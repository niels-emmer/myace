"""Profile compilation engine — resolves collections, merges artifacts, translates to target."""

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.adapters import get_adapter, list_adapters
from app.models.artifact import Artifact, CanonicalArtifact
from app.models.collection import Collection
from app.models.profile import Profile, ProfileCompileResponse, ValidationIssue
from app.models.system_settings import SystemSettings


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
) -> ProfileCompileResponse:
    """
    Compile a profile into target-specific file payloads.

    1. Resolve base collection + additional collections
    2. Collect all artifacts, respecting disabled list
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

    # Fetch all collections
    all_collection_ids = [base_id] + additional_ids
    collection_map: dict[uuid.UUID, Collection] = {}

    for cid in all_collection_ids:
        result = await session.execute(select(Collection).where(Collection.id == cid))
        collection = result.scalar_one_or_none()
        if collection:
            collection_map[cid] = collection

    # Collect artifacts from all collections
    seen_names: dict[str, CanonicalArtifact] = {}
    all_artifacts: list[CanonicalArtifact] = []
    warnings: list[ValidationIssue] = []

    for cid in all_collection_ids:
        if cid not in collection_map:
            continue

        collection = collection_map[cid]
        query = select(Artifact).where(Artifact.collection_id == cid)

        if not include_disabled:
            query = query.where(Artifact.is_enabled == True)

        result = await session.execute(query)
        db_artifacts = result.scalars().all()

        for db_artifact in db_artifacts:
            if db_artifact.id in disabled_ids:
                continue

            canonical = _db_to_canonical(db_artifact, collection)
            # Deduplicate by name — later collections override earlier ones
            # (AGENTS.md rule 29). When the override crosses a collection
            # boundary, surface it as a name_collision warning instead of
            # letting it vanish silently. Compare *collection IDs*, not
            # names — Collection.name has no uniqueness constraint, so two
            # distinct collections can share a display name, and comparing
            # names would false-negative on exactly that case.
            existing = seen_names.get(canonical.name)
            if existing is not None:
                if existing.source_collection_id != canonical.source_collection_id:
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

    # Sort by priority descending
    all_artifacts = sorted(seen_names.values(), key=lambda a: a.priority, reverse=True)

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
    )


def _collection_label(artifact: CanonicalArtifact) -> str:
    """Human-readable, disambiguated label for a warning message.

    `Collection.name` has no uniqueness constraint, so two distinct
    collections can share a display name — append a short id prefix so a
    user with two same-named collections can still tell them apart.
    """
    short_id = str(artifact.source_collection_id)[:8] if artifact.source_collection_id else "?"
    return f"'{artifact.source_collection_name}' ({short_id})"


def _db_to_canonical(db_artifact: Artifact, collection: Collection) -> CanonicalArtifact:
    """Convert a database Artifact to a CanonicalArtifact."""
    return CanonicalArtifact(
        artifact_type=db_artifact.artifact_type,
        name=db_artifact.name,
        version=db_artifact.version,
        target_compatibility=json.loads(db_artifact.target_compatibility),
        priority=db_artifact.priority,
        tags=json.loads(db_artifact.tags),
        description=db_artifact.description or "",
        body=db_artifact.body,
        source_collection_id=collection.id,
        source_collection_name=collection.name,
    )
