"""Tests for the public demo compile endpoint (app/api/demo.py).

POST /api/v1/demo/compile is the first fully-public data route besides the
documented auth-entry list (AGENTS.md rule 13) — no Depends(get_current_user),
no DB session dependency, nothing persisted. These tests cover the compile
happy path, the 20KB input cap, the 10/minute/IP rate limit, and confirm no
DB rows are created as a side effect.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.demo import MAX_MARKDOWN_BYTES, limiter
from app.models.artifact import Artifact
from app.models.collection import Collection

SAMPLE_MARKDOWN = "## Formatting\n\nUse tabs, not spaces.\n\n## Testing\n\nWrite a test per bug fix.\n"


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """The demo Limiter is a module-level singleton shared across the whole
    test process — reset its in-memory counters before each test so one
    test's requests don't bleed into another's rate-limit assertions."""
    limiter.reset()


async def test_demo_compile_returns_previews_for_fixed_target_set(
    async_client: AsyncClient,
) -> None:
    res = await async_client.post("/api/v1/demo/compile", json={"markdown": SAMPLE_MARKDOWN})
    assert res.status_code == 200
    data = res.json()
    assert data["artifact_count"] == 2
    assert set(data["targets"].keys()) == {"claude-code", "cursor", "opencode"}
    assert "CLAUDE.md" in data["targets"]["claude-code"]
    assert "AGENTS.md" in data["targets"]["opencode"]


async def test_demo_compile_requires_no_authentication(async_client: AsyncClient) -> None:
    """No Authorization header, no session cookie — still 200."""
    res = await async_client.post(
        "/api/v1/demo/compile",
        json={"markdown": "## Rule\n\nBody.\n"},
        headers={},
    )
    assert res.status_code == 200


async def test_demo_compile_empty_markdown_yields_zero_artifacts(
    async_client: AsyncClient,
) -> None:
    res = await async_client.post("/api/v1/demo/compile", json={"markdown": "no headers here"})
    assert res.status_code == 200
    data = res.json()
    assert data["artifact_count"] == 0
    # Adapters with no rules produce no CLAUDE.md/AGENTS.md files.
    assert data["targets"]["claude-code"] == {}


async def test_demo_compile_oversized_markdown_returns_422(async_client: AsyncClient) -> None:
    oversized = "x" * (MAX_MARKDOWN_BYTES + 1)
    res = await async_client.post("/api/v1/demo/compile", json={"markdown": oversized})
    assert res.status_code == 422


async def test_demo_compile_at_exactly_the_cap_is_allowed(async_client: AsyncClient) -> None:
    at_cap = "## Rule\n\n" + ("x" * (MAX_MARKDOWN_BYTES - len("## Rule\n\n") - 1)) + "\n"
    assert len(at_cap.encode("utf-8")) <= MAX_MARKDOWN_BYTES
    res = await async_client.post("/api/v1/demo/compile", json={"markdown": at_cap})
    assert res.status_code == 200


async def test_demo_compile_rate_limit_triggers_on_eleventh_request(
    async_client: AsyncClient,
) -> None:
    for _ in range(10):
        res = await async_client.post("/api/v1/demo/compile", json={"markdown": "## Rule\n\nx\n"})
        assert res.status_code == 200

    res = await async_client.post("/api/v1/demo/compile", json={"markdown": "## Rule\n\nx\n"})
    assert res.status_code == 429


async def test_demo_compile_creates_no_database_rows(
    async_client: AsyncClient, db_session: AsyncSession,
) -> None:
    res = await async_client.post("/api/v1/demo/compile", json={"markdown": SAMPLE_MARKDOWN})
    assert res.status_code == 200

    collections = (await db_session.execute(select(Collection))).scalars().all()
    artifacts = (await db_session.execute(select(Artifact))).scalars().all()
    assert collections == []
    assert artifacts == []
