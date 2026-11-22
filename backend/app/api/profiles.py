"""Profile management and compilation routes."""

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.adapters import list_adapters
from app.core.authz import authorize_access, owner_or_public_clause
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.collection import Collection
from app.models.profile import (
    CompileTarget,
    Profile,
    ProfileCompileRequest,
    ProfileCompileResponse,
    ProfileCompileStatusResponse,
    ProfileCreate,
    ProfileRead,
)
from app.models.profile_install import (
    ProfileInstall,
    ProfileInstallCreate,
    ProfileInstallRead,
)
from app.models.user import User
from app.services.compiler import (
    AdapterDisabledError,
    UnknownAdapterError,
    capture_pack_snapshots,
    compile_profile,
    compute_compile_status,
)
from app.services.github_export import slugify

router = APIRouter()


async def _get_profile_or_404(session: AsyncSession, profile_id: uuid.UUID) -> Profile:
    result = await session.execute(
        select(Profile).where(Profile.id == profile_id, Profile.deleted_at == None)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


async def _assert_readable_collection(
    session: AsyncSession, collection_id: uuid.UUID, current_user: User
) -> None:
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection or not collection.is_active:
        raise HTTPException(status_code=404, detail="Base collection not found")
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        is_public=collection.visibility == "public", resource_name="Collection",
    )


def _known_adapter_names() -> set[str]:
    return {adapter.adapter_name() for adapter in list_adapters()}


def _resolve_target_frameworks(profile_data: ProfileCreate) -> list[str]:
    """Filter `target_frameworks` to known adapter names, dropping unknown
    values silently (never 422 — an admin disabling an adapter must not
    brick an existing setup, per docs/adr/0015-pack-reference-freeze.md).

    Falls back to the deprecated `target_framework` field when no valid new
    value was supplied, so an old client that only writes the legacy field
    still records the framework.
    """
    known = _known_adapter_names()
    selected = list(dict.fromkeys(
        name for name in profile_data.target_frameworks if name in known
    ))
    if not selected and profile_data.target_framework in known:
        selected = [profile_data.target_framework]
    return selected


def _parse_target_frameworks(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(value) for value in parsed]


def _install_to_read(install: ProfileInstall) -> ProfileInstallRead:
    return ProfileInstallRead(
        id=install.id,
        profile_id=install.profile_id,
        target=install.target,
        location=install.location,
        method=install.method,
        created_at=install.created_at,
        updated_at=install.updated_at,
    )


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new profile combining collections."""
    await _assert_readable_collection(session, profile_data.base_collection_id, current_user)
    for cid in profile_data.additional_collection_ids:
        await _assert_readable_collection(session, cid, current_user)

    referenced = [profile_data.base_collection_id, *profile_data.additional_collection_ids]
    snapshots = await capture_pack_snapshots(session, referenced, current_user.id)

    db_profile = Profile(
        owner_id=current_user.id,
        name=profile_data.name,
        description=profile_data.description,
        base_collection_id=profile_data.base_collection_id,
        additional_collection_ids=json.dumps(
            [str(cid) for cid in profile_data.additional_collection_ids]
        ),
        disabled_artifact_ids=json.dumps(
            [str(aid) for aid in profile_data.disabled_artifact_ids]
        ),
        target_framework=profile_data.target_framework,
        target_frameworks=json.dumps(_resolve_target_frameworks(profile_data)),
        pack_snapshots=json.dumps(snapshots),
        is_public=profile_data.is_public,
    )
    session.add(db_profile)
    await session.commit()
    await session.refresh(db_profile)
    return _profile_to_read(db_profile)


@router.get("", response_model=list[ProfileRead])
async def list_profiles(
    owner_id: uuid.UUID | None = None,
    is_public: bool | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List profiles visible to the caller: their own + public, or everything for admins."""
    query = select(Profile).where(Profile.deleted_at == None)

    clause = owner_or_public_clause(Profile.owner_id, Profile.is_public == True, current_user)
    if clause is not None:
        query = query.where(clause)
    # Same rule as list_collections: any caller may narrow to their own id (to
    # fetch strictly-owned profiles, excluding public ones they don't own);
    # only admins may narrow to someone else's.
    if owner_id and (current_user.is_admin or owner_id == current_user.id):
        query = query.where(Profile.owner_id == owner_id)
    if is_public is not None:
        query = query.where(Profile.is_public == is_public)

    result = await session.execute(query)
    profiles = result.scalars().all()
    return [_profile_to_read(p) for p in profiles]


@router.get("/{profile_id}", response_model=ProfileRead)
async def get_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a single profile by ID."""
    profile = await _get_profile_or_404(session, profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        is_public=profile.is_public, resource_name="Profile",
    )
    return _profile_to_read(profile)


@router.get("/{profile_id}/installs", response_model=list[ProfileInstallRead])
async def list_profile_installs(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List the caller's claimed installs of this profile.

    Install claims are personal local-machine state, like `SyncStatus` —
    only the calling user's own rows are returned, not any other user's,
    even for admins. A claim is not verification; `SyncStatus` remains the
    only verified source (docs/adr/0015-pack-reference-freeze.md).
    """
    profile = await _get_profile_or_404(session, profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        is_public=profile.is_public, resource_name="Profile",
    )

    result = await session.execute(
        select(ProfileInstall)
        .where(
            ProfileInstall.profile_id == profile_id,
            ProfileInstall.user_id == current_user.id,
        )
        .order_by(ProfileInstall.created_at)
    )
    return [_install_to_read(row) for row in result.scalars().all()]


@router.post("/{profile_id}/installs", response_model=ProfileInstallRead)
async def claim_profile_install(
    profile_id: uuid.UUID,
    install_data: ProfileInstallCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Record (upsert) the caller's claim that they installed this profile.

    Unique per `(user, profile, target, location)`; a repeat claim updates
    `method`/`updated_at` in place rather than inserting a duplicate. This
    is a claim, never verification — see docs/adr/0015-pack-reference-freeze.md.
    """
    profile = await _get_profile_or_404(session, profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        is_public=profile.is_public, resource_name="Profile",
    )

    result = await session.execute(
        select(ProfileInstall).where(
            ProfileInstall.user_id == current_user.id,
            ProfileInstall.profile_id == profile_id,
            ProfileInstall.target == install_data.target,
            ProfileInstall.location == install_data.location,
        )
    )
    install = result.scalar_one_or_none()
    if install is None:
        install = ProfileInstall(
            user_id=current_user.id,
            profile_id=profile_id,
            target=install_data.target,
            location=install_data.location,
            method=install_data.method,
        )
        session.add(install)
    else:
        install.method = install_data.method
        install.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(install)
    return _install_to_read(install)


@router.post("/compile", response_model=ProfileCompileResponse)
async def compile_profile_endpoint(
    request: ProfileCompileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Compile a profile into target-specific file payloads.
    Resolves base + additive collections, merges artifacts without duplicates,
    and returns target-formatted files.
    """
    profile = await _get_profile_or_404(session, request.profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        is_public=profile.is_public, resource_name="Profile",
    )

    try:
        compiled = await compile_profile(
            session=session,
            profile=profile,
            target=request.target,
            include_disabled=request.include_disabled,
            requesting_user=current_user,
        )
    except (AdapterDisabledError, UnknownAdapterError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return compiled


@router.get("/{profile_id}/compile-status", response_model=ProfileCompileStatusResponse)
async def compile_status_endpoint(
    profile_id: uuid.UUID,
    target: CompileTarget,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileCompileStatusResponse:
    """
    Return just the current `compiled_hash` for a profile+target, without
    the full `files` payload — a cheap poll target for `myace check`/`watch`
    drift detection (see `docs/adr/0009-manifest-based-drift-detection.md`).

    Same authorization as `/compile` (owner or public profile). Note the
    cost trade-off documented on `compute_compile_status()`: this still
    performs the same artifact-gathering and `translate()` work as a full
    compile — it only saves the client the transfer/serialization cost of
    every file's content, not the server-side compute cost.
    """
    profile = await _get_profile_or_404(session, profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        is_public=profile.is_public, resource_name="Profile",
    )

    try:
        compiled_hash = await compute_compile_status(
            session=session, profile=profile, target=target,
            requesting_user=current_user,
        )
    except (AdapterDisabledError, UnknownAdapterError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ProfileCompileStatusResponse(
        compiled_hash=compiled_hash, updated_at=profile.updated_at,
    )


@router.post("/compile/zip")
async def compile_profile_zip_endpoint(
    request: ProfileCompileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Compile a profile and return the resulting files as a downloadable zip,
    for browser-only use without the CLI.
    """
    profile = await _get_profile_or_404(session, request.profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        is_public=profile.is_public, resource_name="Profile",
    )

    try:
        compiled = await compile_profile(
            session=session,
            profile=profile,
            target=request.target,
            include_disabled=request.include_disabled,
            requesting_user=current_user,
        )
    except (AdapterDisabledError, UnknownAdapterError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in compiled.files.items():
            zf.writestr(filename, content)

        # The JSON /compile route can return warnings alongside files in the
        # same response body; a zip's HTTP response has no room for a second
        # payload, so warnings ride along as an extra file inside the archive
        # instead, only when there are any to report.
        if compiled.warnings:
            warnings_text = "\n".join(f"[{w.code}] {w.message}" for w in compiled.warnings)
            zf.writestr("_myace_warnings.txt", warnings_text + "\n")

    # Sanitize into the Content-Disposition header — profile.name is
    # user-controlled (including on public profiles owned by someone else),
    # so an unescaped value here would be a header-injection vector.
    zip_filename = f"{slugify(profile.name)}-{slugify(request.target)}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@router.put("/{profile_id}", response_model=ProfileRead)
async def update_profile(
    profile_id: uuid.UUID,
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update an existing profile."""
    profile = await _get_profile_or_404(session, profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        write=True, resource_name="Profile",
    )

    await _assert_readable_collection(session, profile_data.base_collection_id, current_user)
    for cid in profile_data.additional_collection_ids:
        await _assert_readable_collection(session, cid, current_user)

    referenced = [profile_data.base_collection_id, *profile_data.additional_collection_ids]
    snapshots = await capture_pack_snapshots(session, referenced, current_user.id)

    profile.name = profile_data.name
    profile.description = profile_data.description
    profile.base_collection_id = profile_data.base_collection_id
    profile.additional_collection_ids = json.dumps(
        [str(cid) for cid in profile_data.additional_collection_ids]
    )
    profile.disabled_artifact_ids = json.dumps(
        [str(aid) for aid in profile_data.disabled_artifact_ids]
    )
    profile.target_framework = profile_data.target_framework
    profile.target_frameworks = json.dumps(_resolve_target_frameworks(profile_data))
    profile.pack_snapshots = json.dumps(snapshots)
    profile.is_public = profile_data.is_public
    profile.version += 1

    await session.commit()
    await session.refresh(profile)
    return _profile_to_read(profile)


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a profile."""
    profile = await _get_profile_or_404(session, profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        write=True, resource_name="Profile",
    )

    profile.deleted_at = datetime.now(UTC)
    await session.commit()
    return {"message": "Profile deleted"}


def _profile_to_read(profile: Profile) -> ProfileRead:
    """Convert a Profile ORM instance to ProfileRead schema."""
    return ProfileRead(
        id=profile.id,
        owner_id=profile.owner_id,
        name=profile.name,
        description=profile.description,
        base_collection_id=profile.base_collection_id,
        additional_collection_ids=[
            uuid.UUID(cid) for cid in json.loads(profile.additional_collection_ids)
        ],
        disabled_artifact_ids=[
            uuid.UUID(aid) for aid in json.loads(profile.disabled_artifact_ids)
        ],
        target_framework=profile.target_framework,
        target_frameworks=_parse_target_frameworks(profile.target_frameworks),
        is_public=profile.is_public,
        version=profile.version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
