"""Profile management and compilation routes."""

import uuid
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.models.profile import Profile, ProfileCreate, ProfileRead, ProfileCompileRequest
from app.models.collection import Collection
from app.models.artifact import Artifact, CanonicalArtifact
from app.services.compiler import compile_profile

router = APIRouter()


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Create a new profile combining collections."""
    # Verify base collection exists
    result = await session.execute(
        select(Collection).where(Collection.id == profile_data.base_collection_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Base collection not found")

    db_profile = Profile(
        owner_id=owner_id,
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
    owner_id: Optional[uuid.UUID] = None,
    is_public: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
):
    """List profiles with optional filters."""
    query = select(Profile)
    if owner_id:
        query = query.where(Profile.owner_id == owner_id)
    if is_public is not None:
        query = query.where(Profile.is_public == is_public)

    result = await session.execute(query)
    profiles = result.scalars().all()
    return [_profile_to_read(p) for p in profiles]


@router.get("/{profile_id}", response_model=ProfileRead)
async def get_profile(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single profile by ID."""
    result = await session.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_to_read(profile)


@router.post("/compile")
async def compile_profile_endpoint(
    request: ProfileCompileRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Compile a profile into target-specific file payloads.
    Resolves base + additive collections, merges artifacts without duplicates,
    and returns target-formatted files.
    """
    result = await session.execute(
        select(Profile).where(Profile.id == request.profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    compiled = await compile_profile(
        session=session,
        profile=profile,
        target=request.target,
        include_disabled=request.include_disabled,
    )
    return compiled


@router.put("/{profile_id}", response_model=ProfileRead)
async def update_profile(
    profile_id: uuid.UUID,
    profile_data: ProfileCreate,
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Update an existing profile."""
    result = await session.execute(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.owner_id == owner_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

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
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a profile."""
    result = await session.execute(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.owner_id == owner_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await session.delete(profile)
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
