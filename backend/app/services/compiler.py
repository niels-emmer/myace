"""Profile compilation engine — resolves collections, merges artifacts, translates to target."""

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.adapters import get_adapter, list_adapters
from app.models.artifact import Artifact, CanonicalArtifact
from app.models.collection import Collection
from app.models.profile import Profile, ProfileCompileResponse, ValidationIssue
from app.models.system_settings import SystemSettings
from app.models.user import User


def compute_compiled_hash(files: dict[str, str]) -> str:
    """Deterministic sha256 over a compiled-output `files` dict.

    Sorts by filename (dict iteration order isn't guaranteed to be stable
    across callers/serializations) and concatenates `filename\\0content\\0`
    for each entry before hashing, so the same logical output always
    produces the same hash regardless of dict construction order. Same
    primitive as `DocCacheEntry.content_hash`
    (`backend/app/services/doc_verifier.py`) — sha256 over encoded text —
    applied to a whole `files` dict instead of a single string.
    """
    hasher = hashlib.sha256()
    for filename in sorted(files):
        hasher.update(filename.encode())
        hasher.update(b"\0")
        hasher.update(files[filename].encode())
        hasher.update(b"\0")
    return hasher.hexdigest()


class AdapterDisabledError(Exception):
    """Raised when compilation targets an adapter an admin has disabled."""


class UnknownAdapterError(Exception):
    """Raised when `target` doesn't match any registered adapter.

    In practice unreachable via the API — `ProfileCompileRequest.target` is a
    `Literal` covering every registered adapter, so FastAPI 422s before this
    function is ever called with a bad value — but kept as a real, typed
    error (rather than an ad hoc `{"error": ...}` dict) so `compile_profile()`
    can have one concrete success return type end to end.
    """


async def compile_profile(
    session: AsyncSession,
    profile: Profile,
    target: str,
    include_disabled: bool = False,
    requesting_user: User | None = None,
) -> ProfileCompileResponse:
    """
    Compile a profile into target-specific file payloads.

    1. Resolve base collection + additional collections. A collection that
       is missing, inactive (soft-deleted), or — when `requesting_user` is
       given — unreadable by the caller is resolved through
       `Profile.pack_snapshots` **only for an allowed viewer**: an internal
       caller (`requesting_user is None`), the profile's owner, or an
       admin. Any other requester skips it and gets a `pack_unavailable`
       warning. That warning is emitted whether or not a snapshot is used;
       with no snapshot, or for a disallowed viewer, the collection is
       skipped, as before, but no longer silently. See
       docs/adr/0015-pack-reference-freeze.md.
    2. Collect all live (not soft-deleted) artifacts, respecting disabled
       list; `include_disabled` only takes effect for collections the
       requester owns (or any, for an admin)
    3. Sort by priority (highest first)
    4. Deduplicate by name (later collections override earlier); emit a
       `name_collision` ValidationIssue warning whenever that override
       actually happens across two different source collections (see
       AGENTS.md rule 29 for the dedup itself and rule 32 for this
       warnings mechanism)
    5. Translate via the target adapter
    """
    # Resolve collection IDs
    base_id = profile.base_collection_id
    additional_ids = [
        uuid.UUID(cid) for cid in json.loads(profile.additional_collection_ids)
    ]
    disabled_ids = set(
        uuid.UUID(aid) for aid in json.loads(profile.disabled_artifact_ids)
    )

    # Fetch all referenced collections. A collection that is missing,
    # inactive, or unreadable by the requester is resolved through the
    # profile's reference snapshot when one exists AND the requester is an
    # allowed viewer (internal caller, profile owner, or admin); every other
    # requester skips it with a `pack_unavailable` warning. See
    # docs/adr/0015-pack-reference-freeze.md.
    ordered_collection_ids = _unique_ids([base_id] + additional_ids)
    snapshots = _parse_pack_snapshots(profile)
    collection_map: dict[uuid.UUID, Collection] = {}
    collection_by_id: dict[uuid.UUID, Collection] = {}
    frozen_snapshots: dict[uuid.UUID, dict[str, object]] = {}
    warnings: list[ValidationIssue] = []

    # Frozen content may only be served to the profile's owner, an admin, or
    # an internal caller with no identity. A third party compiling a public
    # profile gets an honest `pack_unavailable` warning and no frozen
    # artifacts — otherwise unpublishing a pack would turn every public
    # profile referencing it into a redistribution channel. See ADR-0015.
    can_use_frozen = (
        requesting_user is None
        or requesting_user.id == profile.owner_id
        or requesting_user.is_admin
    )

    for cid in ordered_collection_ids:
        result = await session.execute(select(Collection).where(Collection.id == cid))
        collection = result.scalar_one_or_none()
        if collection is not None:
            collection_by_id[cid] = collection
        is_available = (
            collection is not None
            and collection.is_active
            and (requesting_user is None or _can_read_collection(collection, requesting_user))
        )
        if is_available and collection is not None:
            collection_map[cid] = collection
            continue

        snapshot = snapshots.get(str(cid))
        # Only reveal the display name to a requester who may read the pack;
        # a third party compiling a public profile must learn at most the id.
        visible_name = (
            collection.name
            if collection is not None
            and (requesting_user is None or _can_read_collection(collection, requesting_user))
            else None
        )
        label = _label(visible_name, cid)
        if snapshot is not None and can_use_frozen:
            frozen_snapshots[cid] = snapshot
            captured_at = snapshot.get("captured_at") or "an earlier time"
            warnings.append(
                ValidationIssue(
                    code="pack_unavailable",
                    message=(
                        f"Pack {label} is no longer available to you; using a "
                        f"frozen copy captured at {captured_at}."
                    ),
                )
            )
        else:
            warnings.append(
                ValidationIssue(
                    code="pack_unavailable",
                    message=(
                        f"Pack {label} is not available to you; it was skipped."
                    ),
                )
            )

    # Collect artifacts from all available collections, falling back to the
    # frozen artifact set for any collection resolved through a snapshot.
    seen_names: dict[str, CanonicalArtifact] = {}
    all_artifacts: list[CanonicalArtifact] = []

    def _register(canonical: CanonicalArtifact) -> None:
        # Deduplicate by name — later collections override earlier ones
        # (AGENTS.md rule 29). When the override crosses a collection
        # boundary, surface it as a name_collision warning instead of
        # letting it vanish silently. Compare *collection IDs*, not names.
        existing = seen_names.get(canonical.name)
        if existing is not None and existing.source_collection_id != canonical.source_collection_id:
            other_label = _collection_label(existing)
            winning_label = _collection_label(canonical)
            warnings.append(
                ValidationIssue(
                    code="name_collision",
                    message=(
                        f"Artifact '{canonical.name}' ({canonical.artifact_type}) is "
                        f"defined in both {other_label} and {winning_label}; "
                        f"{winning_label} wins."
                    ),
                )
            )
        seen_names[canonical.name] = canonical

    for cid in ordered_collection_ids:
        if cid in frozen_snapshots:
            await _load_frozen_artifacts(
                session=session,
                collection_id=cid,
                snapshot=frozen_snapshots[cid],
                collection=collection_by_id.get(cid),
                disabled_ids=disabled_ids,
                register=_register,
            )
            continue
        if cid not in collection_map:
            continue

        collection = collection_map[cid]
        query = select(Artifact).where(
            Artifact.collection_id == cid, Artifact.deleted_at == None  # noqa: E711
        )

        if not include_disabled or not _can_include_disabled(collection, requesting_user):
            query = query.where(Artifact.is_enabled == True)

        result = await session.execute(query)
        db_artifacts = result.scalars().all()

        for db_artifact in db_artifacts:
            if db_artifact.id in disabled_ids:
                continue
            _register(_db_to_canonical(db_artifact, collection))

    # Sort by priority descending
    all_artifacts = sorted(seen_names.values(), key=lambda a: a.priority, reverse=True)

    # Whole-profile validation pass, deliberately separate from the
    # per-collection dedup loop above (AGENTS.md rule 32/Epic 3.1): a
    # handoff_to target may live in *any* collection in the profile, so it
    # can only be checked once the final deduplicated artifact set is known
    # — unlike name_collision, which is pairwise/streaming and correctly
    # lives inside the loop.
    warnings.extend(_check_dangling_handoffs(all_artifacts))

    # Reject a system-wide-disabled adapter before translating — this is
    # the single choke point both /profiles/compile and /profiles/compile/zip
    # funnel through, so it can't be bypassed via either route.
    settings_result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings_row = settings_result.scalar_one_or_none()
    if settings_row and target in json.loads(settings_row.disabled_adapters):
        raise AdapterDisabledError(f"Adapter '{target}' is currently disabled by an administrator")

    # Translate via adapter
    adapter = get_adapter(target)
    if not adapter:
        available = ", ".join(a.adapter_name() for a in list_adapters())
        raise UnknownAdapterError(f"No adapter found for target '{target}'. Available: {available}")

    files = adapter.translate(all_artifacts)

    return ProfileCompileResponse(
        profile_id=str(profile.id),
        profile_name=profile.name,
        target=target,
        artifact_count=len(all_artifacts),
        files=files,
        warnings=warnings,
        compiled_hash=compute_compiled_hash(files),
    )


def _can_read_collection(collection: Collection, user: User) -> bool:
    return user.is_admin or collection.owner_id == user.id or collection.visibility == "public"


def _can_include_disabled(collection: Collection, user: User | None) -> bool:
    if user is None:
        return True
    return user.is_admin or collection.owner_id == user.id


async def compute_compile_status(
    session: AsyncSession,
    profile: Profile,
    target: str,
    include_disabled: bool = False,
    requesting_user: User | None = None,
) -> str:
    """Compute just the `compiled_hash` for `GET /profiles/{id}/compile-status`.

    Trade-off, documented honestly: this still gathers artifacts and
    resolves the same overrides/dedup/collision logic as a full compile
    (that work determines *which* files would exist and what they'd
    contain, so there's no way around it without a second, divergent
    source of truth) — it hands the same resolved artifact list to the
    adapter's `translate()` exactly like a full compile does, then hashes
    the result. In practice this endpoint saves callers the
    request/response *serialization* size (the caller only gets a hash +
    timestamp back, not every file's full content), not the server-side
    computation cost — `watch`'s timer loop still triggers a real
    `translate()` call per poll. A true no-`translate()`-cost variant
    would require caching compiled output keyed by a hash of the
    profile's resolved inputs, which is future work, not implemented here.
    """
    compiled = await compile_profile(
        session=session, profile=profile, target=target,
        include_disabled=include_disabled, requesting_user=requesting_user,
    )
    return compiled.compiled_hash


async def capture_pack_snapshots(
    session: AsyncSession,
    collection_ids: list[uuid.UUID],
    requesting_user: User,
    existing_raw: str | None = None,
) -> dict[str, dict[str, object]]:
    """Capture a reference snapshot for every referenced collection the
    requesting user does *not* own and can read.

    Only non-owned, currently-readable collections are snapshotted: an owned
    collection can always be read by its owner, and a collection the caller
    can no longer read must not be re-read (that would let a profile update
    pull artifacts the caller lost access to). For a referenced collection
    that is now unreadable, a previously captured snapshot is **preserved**
    unchanged rather than dropped or refreshed — this is what keeps a setup
    editable after its pack goes private (docs/adr/0015-pack-reference-freeze.md).

    The snapshot records the enabled, live artifact ids at capture time —
    the same set `compile_profile()` would resolve for a non-owner — plus a
    deterministic hash and an ISO-8601 timestamp.
    """
    existing = _parse_snapshot_json(existing_raw)
    snapshots: dict[str, dict[str, object]] = {}
    captured_at = datetime.now(UTC).isoformat()
    for cid in _unique_ids(collection_ids):
        result = await session.execute(select(Collection).where(Collection.id == cid))
        collection = result.scalar_one_or_none()

        if (
            collection is None
            or not collection.is_active
            or not _can_read_collection(collection, requesting_user)
        ):
            # Never capture from a pack the caller cannot read; keep the
            # frozen copy captured earlier, if there is one.
            if str(cid) in existing:
                snapshots[str(cid)] = existing[str(cid)]
            continue

        if collection.owner_id == requesting_user.id:
            continue

        art_result = await session.execute(
            select(Artifact.id).where(
                Artifact.collection_id == cid,
                Artifact.deleted_at == None,  # noqa: E711
                Artifact.is_enabled == True,
            )
        )
        artifact_ids = sorted(str(aid) for aid in art_result.scalars().all())
        snapshots[str(cid)] = {
            "artifact_ids": artifact_ids,
            "hash": hashlib.sha256("\n".join(artifact_ids).encode()).hexdigest(),
            "captured_at": captured_at,
        }
    return snapshots


def _check_dangling_handoffs(all_artifacts: list[CanonicalArtifact]) -> list[ValidationIssue]:
    """Flag `handoff_to` entries that don't name any artifact in the final,
    deduplicated compiled set.

    Whole-profile check, run once after dedup (see the call site above for
    why this can't be folded into the per-collection loop): a `handoff_to`
    target on an agent from one collection may legitimately live in a
    completely different collection of the same profile, so the full
    resolved name set has to exist first.
    """
    warnings: list[ValidationIssue] = []
    known_names = {a.name for a in all_artifacts}
    for artifact in all_artifacts:
        if artifact.artifact_type != "agent" or not artifact.handoff_to:
            continue
        for target_name in artifact.handoff_to:
            if target_name not in known_names:
                warnings.append(
                    ValidationIssue(
                        code="dangling_handoff",
                        message=(
                            f"Agent '{artifact.name}' declares handoff_to "
                            f"'{target_name}', which is not present in the "
                            f"compiled artifact set."
                        ),
                    )
                )
    return warnings


def _collection_label(artifact: CanonicalArtifact) -> str:
    """Human-readable, disambiguated label for a warning message.

    `Collection.name` has no uniqueness constraint, so two distinct
    collections can share a display name — append a short id prefix so a
    user with two same-named collections can still tell them apart.
    """
    return _label(artifact.source_collection_name, artifact.source_collection_id)


def _label(name: str | None, collection_id: uuid.UUID | None) -> str:
    short_id = str(collection_id)[:8] if collection_id else "?"
    if name is None:
        # Never leak a name the requester isn't allowed to see — the id is
        # enough to disambiguate.
        return f"'{short_id}'"
    return f"'{name}' ({short_id})"


def _parse_pack_snapshots(profile: Profile) -> dict[str, dict[str, object]]:
    """Parse `Profile.pack_snapshots` defensively.

    Stored as JSON text (AGENTS.md rule 11). A corrupt value must never
    break compilation — treat it as "no snapshots" rather than raising.
    """
    return _parse_snapshot_json(getattr(profile, "pack_snapshots", None))


def _parse_snapshot_json(raw: str | None) -> dict[str, dict[str, object]]:
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): value for key, value in parsed.items() if isinstance(value, dict)}


def _unique_ids(ids: list[uuid.UUID]) -> list[uuid.UUID]:
    """Deduplicate while preserving order."""
    seen: set[uuid.UUID] = set()
    ordered: list[uuid.UUID] = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            ordered.append(cid)
    return ordered


async def _load_frozen_artifacts(
    session: AsyncSession,
    collection_id: uuid.UUID,
    snapshot: dict[str, object],
    collection: Collection | None,
    disabled_ids: set[uuid.UUID],
    register: Callable[[CanonicalArtifact], None],
) -> None:
    """Load the artifacts named by a reference snapshot.

    Deliberate authorization bypass, scoped to ids the profile owner
    already had access to when the snapshot was captured: the artifact
    rows are fetched by `(id, collection_id)` only, with no live
    collection-read check. Artifacts are soft-deleted at most (rule 15),
    so the row still exists; a later soft-delete does not remove it from
    the frozen set. `disabled_ids` (the profile's own toggles) still
    applies. See docs/adr/0015-pack-reference-freeze.md.
    """
    raw_ids = snapshot.get("artifact_ids")
    if not isinstance(raw_ids, list):
        return

    ids: list[uuid.UUID] = []
    for raw in raw_ids:
        try:
            ids.append(uuid.UUID(str(raw)))
        except (TypeError, ValueError):
            continue
    if not ids:
        return

    result = await session.execute(
        select(Artifact).where(Artifact.id.in_(ids), Artifact.collection_id == collection_id)
    )
    by_id = {artifact.id: artifact for artifact in result.scalars().all()}
    collection_name = collection.name if collection is not None else None

    # Iterate the snapshot's order so a frozen compile is deterministic,
    # independent of how the database returns the rows.
    for aid in ids:
        db_artifact = by_id.get(aid)
        if db_artifact is None or db_artifact.id in disabled_ids:
            continue
        register(_db_to_canonical_with_source(db_artifact, collection_id, collection_name))


def _db_to_canonical(db_artifact: Artifact, collection: Collection) -> CanonicalArtifact:
    """Convert a database Artifact to a CanonicalArtifact."""
    return _db_to_canonical_with_source(db_artifact, collection.id, collection.name)


def _db_to_canonical_with_source(
    db_artifact: Artifact,
    collection_id: uuid.UUID,
    collection_name: str | None,
) -> CanonicalArtifact:
    return CanonicalArtifact(
        artifact_type=db_artifact.artifact_type,
        name=db_artifact.name,
        version=db_artifact.version,
        target_compatibility=json.loads(db_artifact.target_compatibility),
        priority=db_artifact.priority,
        tags=json.loads(db_artifact.tags),
        description=db_artifact.description or "",
        body=db_artifact.body,
        handoff_to=json.loads(db_artifact.handoff_to) if db_artifact.handoff_to else None,
        source_collection_id=collection_id,
        source_collection_name=collection_name,
    )
