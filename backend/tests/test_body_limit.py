"""Unit tests for app.core.body_limit.MaxBodySizeMiddleware, independent
of the demo route it happens to be wired to in production — these exercise
the middleware directly against a minimal ASGI app so its behavior (cap
enforcement, replay-to-downstream-app, scoping to matched routes only) is
verified without depending on app/api/demo.py's specific request shape.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.core.body_limit import MaxBodySizeMiddleware


async def _echo_body_length(request: Request) -> PlainTextResponse:
    body = await request.body()
    return PlainTextResponse(str(len(body)))


def _build_app(limits: dict[tuple[str, str], int]) -> Starlette:
    app = Starlette(routes=[Route("/limited", _echo_body_length, methods=["POST"])])
    app.add_middleware(MaxBodySizeMiddleware, limits=limits)
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
async def test_unmatched_route_is_never_size_checked() -> None:
    """A (method, path) pair not in `limits` must pass straight through,
    with no cap applied at all — confirms the middleware is scoped, not
    global."""
    app = Starlette(routes=[Route("/unlimited", _echo_body_length, methods=["POST"])])
    app.add_middleware(MaxBodySizeMiddleware, limits={("POST", "/limited"): 10})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/unlimited", content=b"x" * 10_000)
    assert res.status_code == 200
    assert res.text == "10000"
