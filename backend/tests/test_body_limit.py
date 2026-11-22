"""Unit tests for app.core.body_limit.MaxBodySizeMiddleware, independent
of the demo route it happens to be wired to in production — these exercise
the middleware directly against a minimal ASGI app so its behavior (cap
enforcement, replay-to-downstream-app, per-route overrides, the
default cap, and the chunked-transfer byte counter) is verified without
depending on app/api/demo.py's specific request shape.

The last test in this file goes the other way and exercises the *real*
FastAPI app, because M-3 was that no route outside /demo/compile had any
cap at all — that wiring is what the default cap exists to fix, and it
only lives in app/main.py.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.core.body_limit import MaxBodySizeMiddleware
from app.main import DEFAULT_REQUEST_BODY_MAX_BYTES
from app.main import app as fastapi_app


async def _echo_body_length(request: Request) -> PlainTextResponse:
    body = await request.body()
    return PlainTextResponse(str(len(body)))


def _build_app(
    limits: dict[tuple[str, str], int], default_max_bytes: int | None = None
) -> Starlette:
    app = Starlette(routes=[Route("/limited", _echo_body_length, methods=["POST"])])
    app.add_middleware(
        MaxBodySizeMiddleware, limits=limits, default_max_bytes=default_max_bytes
    )
    return app


@pytest.mark.asyncio
async def test_body_under_cap_passes_through_unchanged() -> None:
    app = _build_app({("POST", "/limited"): 100})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/limited", content=b"x" * 50)
    assert res.status_code == 200
    assert res.text == "50"


@pytest.mark.asyncio
async def test_body_over_cap_rejected_with_413() -> None:
    app = _build_app({("POST", "/limited"): 100})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/limited", content=b"x" * 500)
    assert res.status_code == 413
    assert "detail" in res.json()


@pytest.mark.asyncio
async def test_body_exactly_at_cap_passes() -> None:
    app = _build_app({("POST", "/limited"): 100})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/limited", content=b"x" * 100)
    assert res.status_code == 200
    assert res.text == "100"


@pytest.mark.asyncio
async def test_unmatched_route_is_never_size_checked_when_no_default_is_set() -> None:
    """With `default_max_bytes` left at its `None` default, a (method, path)
    pair not in `limits` passes straight through with no cap applied at all —
    confirms the middleware stays usable in an explicitly-scoped mode (the
    unit-test shape) and that the default cap is opt-in, not hard-wired."""
    app = Starlette(routes=[Route("/unlimited", _echo_body_length, methods=["POST"])])
    app.add_middleware(MaxBodySizeMiddleware, limits={("POST", "/limited"): 10})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/unlimited", content=b"x" * 10_000)
    assert res.status_code == 200
    assert res.text == "10000"


@pytest.mark.asyncio
async def test_default_cap_applies_to_a_route_with_no_explicit_entry() -> None:
    """M-3: a route with no per-(method, path) entry is capped by
    `default_max_bytes`, so an unauthenticated route can't be handed an
    unbounded body to buffer."""
    app = _build_app({}, default_max_bytes=100)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/limited", content=b"x" * 500)
    assert res.status_code == 413
    assert "detail" in res.json()


@pytest.mark.asyncio
async def test_default_cap_allows_a_body_within_the_limit() -> None:
    app = _build_app({}, default_max_bytes=100)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/limited", content=b"x" * 100)
    assert res.status_code == 200
    assert res.text == "100"


@pytest.mark.asyncio
async def test_explicit_route_entry_overrides_the_default_cap() -> None:
    """A route with its own, larger entry must use that entry — not the
    (smaller) default — or bulk import would be capped at the default."""
    app = _build_app({("POST", "/limited"): 1000}, default_max_bytes=10)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/limited", content=b"x" * 500)
    assert res.status_code == 200
    assert res.text == "500"


@pytest.mark.asyncio
async def test_chunked_body_without_content_length_is_still_capped() -> None:
    """Chunked transfer encoding has no Content-Length to check, so the cap
    must come from the incremental received-byte counter. An async-iterator
    body is sent as multiple `http.request` messages with `more_body=True`."""
    app = _build_app({}, default_max_bytes=100)

    async def _chunks() -> AsyncGenerator[bytes, None]:
        yield b"x" * 60
        yield b"y" * 60

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/limited", content=_chunks())
    assert res.status_code == 413


@pytest.mark.asyncio
async def test_chunked_body_within_the_cap_passes_through() -> None:
    app = _build_app({}, default_max_bytes=100)

    async def _chunks() -> AsyncGenerator[bytes, None]:
        yield b"x" * 30
        yield b"y" * 30

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/limited", content=_chunks())
    assert res.status_code == 200
    assert res.text == "60"


@pytest.mark.asyncio
async def test_oversized_body_to_a_previously_uncapped_route_is_rejected() -> None:
    """M-3, end to end against the real app: `POST /api/v1/auth/register` is
    unauthenticated and, before the default cap, had no size limit at all.
    A body over the default must get a 413 from the transport middleware,
    before FastAPI buffers it to build the request model."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/register",
            content=b"x" * (DEFAULT_REQUEST_BODY_MAX_BYTES + 1),
        )
    assert res.status_code == 413
