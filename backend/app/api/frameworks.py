"""Public framework list — the target ids a pack can be compiled for.

`GET /api/v1/frameworks` is one of the documented anonymous reads (ADR-0014 /
ADR-0018, AGENTS.md rule 13). It exists because the MCP server needs a *typed*
target list: `GET /api/v1/adapters` is authenticated and returns aliases and
adapter metadata that a public surface has no business exposing, while the
pack-install route's guidance document is prose for humans and agents, not
something a typed client should parse.

Only primary `adapter_name()` values are returned (rule 23 — a
`supported_targets()` alias is never a valid compile target), and adapters an
administrator has disabled are omitted: a target advertised here must not 400
when it is used.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import list_adapters
from app.core.config import settings
from app.core.database import get_session
from app.core.ratelimit import storefront_limiter
from app.services.effective_settings import get_disabled_adapter_names

router = APIRouter()


@router.get("", response_model=list[str])
@storefront_limiter.limit(settings.storefront_rate_limit)
async def list_frameworks(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """List the compile targets currently offered to anonymous clients."""
    disabled = await get_disabled_adapter_names(session)
    return [
        adapter.adapter_name()
        for adapter in list_adapters()
        if adapter.adapter_name() not in disabled
    ]
