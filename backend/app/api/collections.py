"""Collection management routes."""

import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.models.collection import Collection, CollectionCreate, CollectionRead
from app.models.artifact import Artifact, ArtifactRead

router = APIRouter()


@router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection_data: CollectionCreate,
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Register a new collection from a Git repository."""
    db_collection = Collection(
        owner_id=owner_id,
        **collection_data.model_dump(),
    )
    session.add(db_collection)
    await session.commit()
    await session.refresh(db_collection)
    return db_collection


@router.get("", response_model=list[CollectionRead])
async def list_collections(
    owner_id: Optional[uuid.UUID] = None,
    collection_type: Optional[str] = Query(None, alias="type"),
    visibility: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """List collections with optional filters."""
    query = select(Collection)

    if owner_id:
        query = query.where(Collection.owner_id == owner_id)
    if collection_type:
        query = query.where(Collection.collection_type == collection_type)
    if visibility:
        query = query.where(Collection.visibility == visibility)

    query = query.where(Collection.is_active == True)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{collection_id}", response_model=CollectionRead)
async def get_collection(
    collection_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single collection by ID."""
    result = await session.execute(
        select(Collection).where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.get("/{collection_id}/artifacts", response_model=list[ArtifactRead])
async def list_collection_artifacts(
    collection_id: uuid.UUID,
    artifact_type: Optional[str] = Query(None, alias="type"),
    session: AsyncSession = Depends(get_session),
):
    """List artifacts in a collection."""
    query = select(Artifact).where(
        Artifact.collection_id == collection_id,
        Artifact.is_enabled == True,
    )
    if artifact_type:
        query = query.where(Artifact.artifact_type == artifact_type)

    result = await session.execute(query)
    return result.scalars().all()


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: uuid.UUID,
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete a collection."""
    result = await session.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.owner_id == owner_id,
        )
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    collection.is_active = False
    await session.commit()
    return {"message": "Collection deleted"}


class ScanRequest(BaseModel):
    """Request to scan a local directory for artifacts."""
    path: str
    framework: str = "opencode"


class ScanResult(BaseModel):
    """A discovered artifact from a local scan."""
    artifact_type: str
    name: str
    version: str = "1.0.0"
    priority: int = 50
    target_compatibility: list[str] = []
    tags: list[str] = []
    description: str = ""
    body: str = ""
    file_path: str = ""
    selected: bool = True


@router.post("/scan")
async def scan_local_directory(request: ScanRequest):
    """Scan a local directory and return discovered artifacts."""
    try:
        from app.services.scanner import scan_directory
        artifacts = scan_directory(request.path)
        return {
            "path": request.path,
            "framework": request.framework,
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {e}")


class BulkImportItem(BaseModel):
    """A single artifact to import."""
    artifact_type: str
    name: str
    version: str = "1.0.0"
    priority: int = 50
    target_compatibility: list[str] = []
    tags: list[str] = []
    description: str = ""
    body: str = ""
    file_path: str = ""


class BulkImportRequest(BaseModel):
    """Request to bulk-import artifacts into a new collection."""
    collection_name: str
    collection_description: str = ""
    git_url: str = ""
    collection_type: str = "base"
    visibility: str = "private"
    owner_email: str = ""
    artifacts: list[BulkImportItem]


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def bulk_import(
    request: BulkImportRequest,
    owner_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000000"),
    session: AsyncSession = Depends(get_session),
):
    """Bulk-import artifacts into a new collection."""
    # Auto-create user if nil UUID is passed
    if str(owner_id) == "00000000-0000-0000-0000-000000000000":
        email = request.owner_email or f"import-{uuid.uuid4().hex[:8]}@myace.local"
        from app.models.user import User
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                display_name=request.collection_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        owner_id = user.id

    # Create the collection
    collection = Collection(
        owner_id=owner_id,
        name=request.collection_name,
        description=request.collection_description,
        git_url=request.git_url or f"imported://{request.collection_name}",
        collection_type=request.collection_type,
        visibility=request.visibility,
    )
    session.add(collection)
    await session.commit()
    await session.refresh(collection)

    # Create artifacts
    created = 0
    for item in request.artifacts:
        artifact = Artifact(
            collection_id=collection.id,
            artifact_type=item.artifact_type,
            name=item.name,
            version=item.version,
            priority=item.priority,
            target_compatibility=json.dumps(item.target_compatibility),
            tags=json.dumps(item.tags),
            description=item.description,
            body=item.body,
            file_path=item.file_path,
        )
        session.add(artifact)
        created += 1

    await session.commit()

    # Update artifact count
    collection.artifact_count = created
    await session.commit()

    return {
        "collection_id": str(collection.id),
        "collection_name": collection.name,
        "artifacts_imported": created,
    }
