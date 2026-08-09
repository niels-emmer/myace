"""Shared ownership/visibility authorization checks.

There is no team/org/sharing model — every resource is either owned by exactly
one user, or (for collections/profiles) marked public for read-only access by
anyone else. Admins bypass ownership entirely.
"""

import uuid

from fastapi import HTTPException, status

from app.models.user import User


def authorize_access(
    *,
    owner_id: uuid.UUID,
    current_user: User,
    is_public: bool = False,
    write: bool = False,
    resource_name: str = "Resource",
) -> None:
    """Raise 404 if current_user cannot access this resource.

    404 (not 403) matches the existing owner-filter convention elsewhere in
    this codebase of not revealing whether a resource exists to a caller who
    isn't allowed to see it.
    """
    if current_user.is_admin or owner_id == current_user.id:
        return
    if not write and is_public:
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource_name} not found")


def owner_or_public_clause(owner_col, is_public_expr, current_user: User):
    """WHERE clause for list endpoints: 'mine + public'. Returns None (no
    filter — see everything) for admins."""
    if current_user.is_admin:
        return None
    from sqlalchemy import or_
    return or_(owner_col == current_user.id, is_public_expr)
