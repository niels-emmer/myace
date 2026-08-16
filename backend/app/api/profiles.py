"""Profile management and compilation routes."""

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.authz import authorize_access, owner_or_public_clause
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.collection import Collection
from app.models.profile import (
    Profile,
    ProfileCompileRequest,
    ProfileCompileResponse,
    ProfileCreate,
    ProfileRead,
)
from app.models.user import User
from app.services.compiler import AdapterDisabledError, UnknownAdapterError, compile_profile
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
    if not collection:
        raise HTTPException(status_code=404, detail="Base collection not found")
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        is_public=collection.visibility == "public", resource_name="Collection",
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
    if owner_id and current_user.is_admin:
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
        )
    except (AdapterDisabledError, UnknownAdapterError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return compiled


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
        is_public=profile.is_public,
        version=profile.version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
