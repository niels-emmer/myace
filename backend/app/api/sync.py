"""Sync status reporting — opt-in dashboard fed by `myace check --report`/`watch --report`.

See docs/adr/0009-manifest-based-drift-detection.md. Nothing here is
computed server-side; every row is a client-submitted snapshot of a drift
check the CLI already ran locally.
"""

import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.authz import authorize_access
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.profile import Profile
from app.models.sync_status import SyncReportRequest, SyncStatus, SyncStatusRead
from app.models.user import User

router = APIRouter()


async def _get_profile_or_404(session: AsyncSession, profile_id: uuid.UUID) -> Profile:
    result = await session.execute(
        select(Profile).where(Profile.id == profile_id, Profile.deleted_at == None)  # noqa: E711
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


def _to_read(status: SyncStatus, profile_name: str) -> SyncStatusRead:
    return SyncStatusRead(
        id=status.id,
        profile_id=status.profile_id,
        profile_name=profile_name,
        target=status.target,
        machine_label=status.machine_label,
        in_sync=status.in_sync,
        locally_modified_files=json.loads(status.locally_modified_files),
        last_checked_at=status.last_checked_at,
    )


@router.post("/report", response_model=SyncStatusRead)
async def report_sync_status(
    request: SyncReportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SyncStatusRead:
    """Upsert the caller's own sync-status row for (profile, target, machine).

    Ownership always comes from `current_user.id` (AGENTS.md rule 13) — never
    a client-supplied user id. The unique constraint on
    `(user_id, profile_id, target, machine_label)` means a second report for
    the same triple updates the existing row rather than creating a
    duplicate.
    """
    profile = await _get_profile_or_404(session, request.profile_id)
    authorize_access(
        owner_id=profile.owner_id, current_user=current_user,
        is_public=profile.is_public, resource_name="Profile",
    )

    result = await session.execute(
        select(SyncStatus).where(
            SyncStatus.user_id == current_user.id,
            SyncStatus.profile_id == request.profile_id,
            SyncStatus.target == request.target,
            SyncStatus.machine_label == request.machine_label,
        )
    )
    status_row = result.scalar_one_or_none()

    if status_row is None:
        status_row = SyncStatus(
            user_id=current_user.id,
            profile_id=request.profile_id,
            target=request.target,
            machine_label=request.machine_label,
            in_sync=request.in_sync,
            locally_modified_files=json.dumps(request.locally_modified_files),
        )
        session.add(status_row)
    else:
        status_row.in_sync = request.in_sync
        status_row.locally_modified_files = json.dumps(request.locally_modified_files)
        status_row.last_checked_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(status_row)

    return _to_read(status_row, profile.name)


@router.get("/status", response_model=list[SyncStatusRead])
async def list_sync_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SyncStatusRead]:
    """List only the caller's own sync-status rows — this is local machine
    state, not a community/shared feature, so there is no cross-user
    visibility here even for admins."""
    result = await session.execute(
        select(SyncStatus, Profile.name)
        .join(Profile, Profile.id == SyncStatus.profile_id)
        .where(SyncStatus.user_id == current_user.id)
        .order_by(SyncStatus.last_checked_at.desc())
    )
    return [_to_read(status, profile_name) for status, profile_name in result.all()]
