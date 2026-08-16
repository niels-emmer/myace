"""Collection management routes."""

import json
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.authz import authorize_access, owner_or_public_clause
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.artifact import Artifact, ArtifactRead, ArtifactUpdate, CanonicalArtifact
from app.models.collection import Collection, CollectionCreate, CollectionRead, CollectionUpdate
from app.models.user import User

router = APIRouter()


def _artifact_to_read(artifact: Artifact) -> ArtifactRead:
    """Convert a DB Artifact (JSON-as-text columns) into its API schema."""
    return ArtifactRead(
        id=artifact.id,
        collection_id=artifact.collection_id,
        artifact_type=artifact.artifact_type,
        name=artifact.name,
        version=artifact.version,
        priority=artifact.priority,
        target_compatibility=json.loads(artifact.target_compatibility),
        tags=json.loads(artifact.tags),
        description=artifact.description,
        body=artifact.body,
        file_path=artifact.file_path,
        is_enabled=artifact.is_enabled,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


def _artifact_to_canonical(artifact: Artifact) -> CanonicalArtifact:
    """Convert a DB Artifact into the in-memory Canonical IR shape."""
    return CanonicalArtifact(
        artifact_type=artifact.artifact_type,
        name=artifact.name,
        version=artifact.version,
        target_compatibility=json.loads(artifact.target_compatibility),
        priority=artifact.priority,
        tags=json.loads(artifact.tags),
        description=artifact.description or "",
        body=artifact.body,
    )


async def _get_collection_or_404(session: AsyncSession, collection_id: uuid.UUID) -> Collection:
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection_data: CollectionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Register a new collection from a Git repository."""
    db_collection = Collection(
        owner_id=current_user.id,
        **collection_data.model_dump(),
    )
    session.add(db_collection)
    await session.commit()
    await session.refresh(db_collection)
    return db_collection


@router.get("", response_model=list[CollectionRead])
async def list_collections(
    owner_id: uuid.UUID | None = None,
    collection_type: str | None = Query(None, alias="type"),
    visibility: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List collections visible to the caller: their own + public, or everything for admins.

    `owner_id` narrows this further — any caller may pass their own id (e.g. to fetch
    strictly-owned collections, excluding public ones they don't own); only admins may
    pass someone else's.
    """
    query = select(Collection)

    clause = owner_or_public_clause(
        Collection.owner_id, Collection.visibility == "public", current_user
    )
    if clause is not None:
        query = query.where(clause)
    if owner_id and (current_user.is_admin or owner_id == current_user.id):
        query = query.where(Collection.owner_id == owner_id)
    if collection_type:
        query = query.where(Collection.collection_type == collection_type)
    if visibility:
        query = query.where(Collection.visibility == visibility)

    query = query.where(Collection.is_active == True)
    result = await session.execute(query)
    return result.scalars().all()


class CommunityCollectionsResponse(BaseModel):
    """Paginated response for community collections."""
    items: list[CollectionRead]
    total: int


@router.get("/community", response_model=CommunityCollectionsResponse)
async def list_community_collections(
    collection_type: str | None = Query(None, alias="type"),
    category: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List published community collections, with optional filters and pagination.

    Results are sorted alphabetically by name. Supports filtering by
    collection_type ('base'/'additional') and/or category.
    """
    base_query = select(Collection).where(
        Collection.published == True,
        Collection.is_active == True,
    )
    if collection_type:
        base_query = base_query.where(Collection.collection_type == collection_type)
    if category:
        base_query = base_query.where(Collection.category == category)

    # Total count for pagination
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch page — base collections first, then additional, both alphabetically.
    # 'additional' < 'base' alphabetically, so use a CASE expression to force
    # the correct order: base → 0, additional → 1.
    type_order = case(
        (Collection.collection_type == "base", 0),
        (Collection.collection_type == "additional", 1),
        else_=2,
    )
    query = (
        base_query
        .order_by(type_order, Collection.name.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)

    return CommunityCollectionsResponse(
        items=list(result.scalars().all()),
        total=total,
    )


@router.get("/community/top", response_model=list[CollectionRead])
async def list_top_community_collections(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List the top N most downloaded published community collections."""
    query = (
        select(Collection)
        .where(Collection.published == True, Collection.is_active == True)
        .order_by(Collection.download_count.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/community/categories", response_model=list[str])
async def list_community_categories(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all distinct categories among published community collections."""
    from sqlalchemy import distinct

    query = select(distinct(Collection.category)).where(
        Collection.published == True,
        Collection.is_active == True,
        Collection.category != None,
    )
    result = await session.execute(query)
    return [row[0] for row in result.all() if row[0]]


@router.get("/{collection_id}", response_model=CollectionRead)
async def get_collection(
    collection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a single collection by ID."""
    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        is_public=collection.visibility == "public", resource_name="Collection",
    )
    return collection


@router.patch("/{collection_id}", response_model=CollectionRead)
async def update_collection(
    collection_id: uuid.UUID,
    update_data: CollectionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update a collection's editable fields (name, description, type)."""
    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        write=True, resource_name="Collection",
    )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(collection, field, value)

    await session.commit()
    await session.refresh(collection)
    return collection


@router.get("/{collection_id}/artifacts", response_model=list[ArtifactRead])
async def list_collection_artifacts(
    collection_id: uuid.UUID,
    artifact_type: str | None = Query(None, alias="type"),
    include_disabled: bool = Query(False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List artifacts in a collection."""
    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        is_public=collection.visibility == "public", resource_name="Collection",
    )

    query = select(Artifact).where(
        Artifact.collection_id == collection_id,
        Artifact.deleted_at == None,
    )
    if not include_disabled:
        query = query.where(Artifact.is_enabled == True)
    if artifact_type:
        query = query.where(Artifact.artifact_type == artifact_type)

    result = await session.execute(query)
    return [_artifact_to_read(a) for a in result.scalars().all()]


@router.get("/{collection_id}/artifacts/{artifact_id}", response_model=ArtifactRead)
async def get_artifact(
    collection_id: uuid.UUID,
    artifact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a single artifact by ID (includes disabled artifacts)."""
    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        is_public=collection.visibility == "public", resource_name="Collection",
    )

    result = await session.execute(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.collection_id == collection_id,
            Artifact.deleted_at == None,
        )
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _artifact_to_read(artifact)


@router.patch("/{collection_id}/artifacts/{artifact_id}", response_model=ArtifactRead)
async def update_artifact(
    collection_id: uuid.UUID,
    artifact_id: uuid.UUID,
    update_data: ArtifactUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update an artifact's fields (partial update)."""
    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        write=True, resource_name="Collection",
    )

    result = await session.execute(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.collection_id == collection_id,
            Artifact.deleted_at == None,
        )
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    update_dict = update_data.model_dump(exclude_unset=True)

    # Handle JSON-serialized list fields
    if "target_compatibility" in update_dict:
        update_dict["target_compatibility"] = json.dumps(update_dict["target_compatibility"])
    if "tags" in update_dict:
        update_dict["tags"] = json.dumps(update_dict["tags"])

    for field, value in update_dict.items():
        setattr(artifact, field, value)

    await session.commit()
    await session.refresh(artifact)
    return _artifact_to_read(artifact)


class BulkArtifactIds(BaseModel):
    """A set of artifact IDs to act on in bulk."""
    artifact_ids: list[uuid.UUID]


@router.post("/{collection_id}/artifacts/bulk-delete")
async def bulk_delete_artifacts(
    collection_id: uuid.UUID,
    request: BulkArtifactIds,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a set of artifacts from a collection."""
    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        write=True, resource_name="Collection",
    )

    result = await session.execute(
        select(Artifact).where(
            Artifact.collection_id == collection_id,
            Artifact.id.in_(request.artifact_ids),
            Artifact.deleted_at == None,
        )
    )
    artifacts = result.scalars().all()
    deleted = len(artifacts)
    now = datetime.now(UTC)
    for artifact in artifacts:
        artifact.deleted_at = now
    await session.commit()

    count_result = await session.execute(
        select(Artifact).where(Artifact.collection_id == collection_id)
    )
    collection.artifact_count = len(count_result.scalars().all())
    await session.commit()

    return {"deleted": deleted}


class BulkExportRequest(BaseModel):
    """Request to copy a set of artifacts into an existing or new collection."""
    artifact_ids: list[uuid.UUID]
    target_collection_id: uuid.UUID | None = None
    new_collection_name: str | None = None
    new_collection_description: str = ""
    new_collection_type: str = "base"


@router.post("/{collection_id}/artifacts/bulk-export")
async def bulk_export_artifacts(
    collection_id: uuid.UUID,
    request: BulkExportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Copy a set of artifacts from this collection into an existing or new collection."""
    source_collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=source_collection.owner_id, current_user=current_user,
        is_public=source_collection.visibility == "public", resource_name="Collection",
    )

    result = await session.execute(
        select(Artifact).where(
            Artifact.collection_id == collection_id,
            Artifact.id.in_(request.artifact_ids),
            Artifact.deleted_at == None,
        )
    )
    source_artifacts = result.scalars().all()
    if not source_artifacts:
        raise HTTPException(status_code=404, detail="No matching artifacts found")

    target_collection: Collection | None = None
    if request.target_collection_id:
        target_collection = await _get_collection_or_404(session, request.target_collection_id)
        authorize_access(
            owner_id=target_collection.owner_id, current_user=current_user,
            write=True, resource_name="Collection",
        )
    else:
        if not request.new_collection_name:
            raise HTTPException(
                status_code=422,
                detail="new_collection_name is required when target_collection_id is not provided",
            )
        target_collection = Collection(
            owner_id=current_user.id,
            name=request.new_collection_name,
            description=request.new_collection_description,
            git_url=f"imported://{request.new_collection_name}",
            collection_type=request.new_collection_type,
        )
        session.add(target_collection)
        await session.commit()
        await session.refresh(target_collection)

    exported = 0
    for src in source_artifacts:
        session.add(Artifact(
            collection_id=target_collection.id,
            artifact_type=src.artifact_type,
            name=src.name,
            version=src.version,
            priority=src.priority,
            target_compatibility=src.target_compatibility,
            tags=src.tags,
            description=src.description,
            body=src.body,
            file_path=src.file_path,
            is_enabled=src.is_enabled,
        ))
        exported += 1
    await session.commit()

    count_result = await session.execute(
        select(Artifact).where(Artifact.collection_id == target_collection.id)
    )
    target_collection.artifact_count = len(count_result.scalars().all())
    await session.commit()

    return {
        "target_collection_id": str(target_collection.id),
        "target_collection_name": target_collection.name,
        "exported": exported,
    }


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete a collection."""
    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        write=True, resource_name="Collection",
    )

    collection.is_active = False
    await session.commit()
    return {"message": "Collection deleted"}


class GitHubExportRequest(BaseModel):
    """Request to export a collection's enabled artifacts to a GitHub branch + PR."""
    repo: str
    base_branch: str = "main"
    new_branch: str = ""
    commit_message: str = ""
    pr_title: str = ""
    pr_body: str = ""
    github_token: str


@router.post("/{collection_id}/export/github")
async def export_collection_to_github(
    collection_id: uuid.UUID,
    request: GitHubExportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export a collection's enabled artifacts as a new branch + pull request on GitHub."""
    from app.services.github_export import (
        GitHubExportError,
        artifacts_to_files,
        parse_repo,
        slugify,
    )
    from app.services.github_export import (
        export_collection_to_github as do_export,
    )

    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        write=True, resource_name="Collection",
    )

    art_result = await session.execute(
        select(Artifact).where(
            Artifact.collection_id == collection_id,
            Artifact.is_enabled == True,
            Artifact.deleted_at == None,
        )
    )
    db_artifacts = art_result.scalars().all()
    if not db_artifacts:
        raise HTTPException(status_code=400, detail="Collection has no enabled artifacts to export")

    canonical = [_artifact_to_canonical(a) for a in db_artifacts]

    try:
        owner, repo_name = parse_repo(request.repo)
    except GitHubExportError as e:
        raise HTTPException(status_code=400, detail=str(e))

    files = artifacts_to_files(canonical)
    skipped_model_configs = sum(1 for a in canonical if a.artifact_type == "model_config")

    new_branch = (
        request.new_branch or f"myace-export-{slugify(collection.name)}-{uuid.uuid4().hex[:8]}"
    )
    commit_message = request.commit_message or f'Export "{collection.name}" from MyACE'
    pr_title = request.pr_title or commit_message

    try:
        result = await do_export(
            owner=owner,
            repo=repo_name,
            base_branch=request.base_branch or "main",
            new_branch=new_branch,
            files=files,
            commit_message=commit_message,
            pr_title=pr_title,
            pr_body=request.pr_body,
            token=request.github_token,
        )
    except GitHubExportError as e:
        raise HTTPException(status_code=502, detail=str(e))

    result["files_exported"] = len(files)
    result["skipped_model_configs"] = skipped_model_configs
    return result


class PublishRequest(BaseModel):
    """Request to publish a collection to the MyACE community store."""
    category: str
    publish_name: str | None = None
    publish_description: str | None = None


@router.post("/{collection_id}/publish", response_model=CollectionRead)
async def publish_collection(
    collection_id: uuid.UUID,
    request: PublishRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Submit a collection for moderation review.

    This no longer publishes immediately — it moves the collection into the
    `submitted` moderation queue for a moderator/admin to approve or deny
    (see app.api.moderation). Only `published`/`visibility` flip is the
    approve action; this endpoint never touches them. Allowed from `draft`
    or `denied` only (409 otherwise — already submitted/approved).
    """
    collection = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=collection.owner_id, current_user=current_user,
        write=True, resource_name="Collection",
    )

    if collection.moderation_status not in ("draft", "denied"):
        raise HTTPException(
            status_code=409,
            detail=f"Collection is already {collection.moderation_status}; cannot resubmit",
        )

    if not request.category.strip():
        raise HTTPException(status_code=422, detail="category is required")

    art_result = await session.execute(
        select(Artifact).where(
            Artifact.collection_id == collection_id,
            Artifact.is_enabled == True,
            Artifact.deleted_at == None,
        )
    )
    db_artifacts = art_result.scalars().all()
    if not db_artifacts:
        raise HTTPException(
            status_code=400, detail="Collection has no enabled artifacts to publish"
        )

    if request.publish_name and request.publish_name.strip():
        collection.name = request.publish_name.strip()
    if request.publish_description is not None:
        collection.description = request.publish_description.strip()
    collection.category = request.category.strip()
    collection.moderation_status = "submitted"
    collection.submitted_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(collection)

    return collection


@router.post("/{collection_id}/import", status_code=status.HTTP_201_CREATED)
async def import_community_collection(
    collection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Import a published community collection into the user's workspace.

    Creates a new collection owned by the caller with all artifacts copied.
    Increments the download_count on the source collection.
    """
    source = await _get_collection_or_404(session, collection_id)
    authorize_access(
        owner_id=source.owner_id, current_user=current_user,
        is_public=source.visibility == "public" or source.published,
        resource_name="Collection",
    )

    if not source.published:
        raise HTTPException(status_code=400, detail="Only published collections can be imported")

    # Fetch source artifacts
    art_result = await session.execute(
        select(Artifact).where(
            Artifact.collection_id == collection_id,
            Artifact.deleted_at == None,
        )
    )
    source_artifacts = art_result.scalars().all()

    # Create a new collection for the user
    target = Collection(
        owner_id=current_user.id,
        name=f"{source.name} (imported)",
        description=source.description,
        git_url=f"imported://community/{source.name}",
        collection_type=source.collection_type,
        visibility="private",
        category=source.category,
    )
    session.add(target)
    await session.commit()
    await session.refresh(target)

    # Copy artifacts
    created = 0
    for src in source_artifacts:
        session.add(Artifact(
            collection_id=target.id,
            artifact_type=src.artifact_type,
            name=src.name,
            version=src.version,
            priority=src.priority,
            target_compatibility=src.target_compatibility,
            tags=src.tags,
            description=src.description,
            body=src.body,
            file_path=src.file_path,
            is_enabled=src.is_enabled,
        ))
        created += 1
    await session.commit()

    # Update counts
    target.artifact_count = created
    source.download_count = (source.download_count or 0) + 1
    await session.commit()

    return {
        "collection_id": str(target.id),
        "collection_name": target.name,
        "artifacts_imported": created,
    }


class ScanRequest(BaseModel):
    """Request to scan a local directory or a Git repository for artifacts."""
    source_type: Literal["local", "git"] = "local"
    path: str = ""
    git_url: str = ""
    git_branch: str = "main"
    subdirectory: str = ""
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
async def scan_local_directory(
    request: ScanRequest,
    current_user: User = Depends(get_current_user),
):
    """Scan a local directory or Git repository and return discovered artifacts."""
    try:
        if request.source_type == "git":
            from app.services.scanner import _redact_credentials, scan_git_repository
            if not request.git_url:
                raise ValueError("git_url is required when source_type is 'git'")
            artifacts = scan_git_repository(
                request.git_url,
                branch=request.git_branch or "main",
                subdirectory=request.subdirectory,
            )
            source_label = _redact_credentials(request.git_url)
        else:
            from app.services.scanner import scan_directory
            if not request.path:
                raise ValueError("path is required when source_type is 'local'")
            artifacts = scan_directory(request.path)
            source_label = request.path

        return {
            "path": source_label,
            "framework": request.framework,
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Directory not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Scan failed")


class BulkImportItem(BaseModel):
    """A single artifact to import."""
    artifact_type: Literal["rule", "skill", "agent", "workflow", "model_config"]
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
    artifacts: list[BulkImportItem]


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def bulk_import(
    request: BulkImportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Bulk-import artifacts into a new collection owned by the caller."""
    collection = Collection(
        owner_id=current_user.id,
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
