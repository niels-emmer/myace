"""The Dockerfile's --forwarded-allow-ips must not let a client forge its IP.

With `*`, uvicorn takes the left-most X-Forwarded-For entry — which the client
controls — so a forged header spoofed `request.client` and bypassed the
per-IP auth rate limits (app/core/ratelimit.py). These tests feed the *actual*
value out of the Dockerfile's CMD into uvicorn's own middleware.
"""

import re
from pathlib import Path

import pytest
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

DOCKERFILE = Path(__file__).resolve().parent.parent / "Dockerfile"

# The chain in production: client -> NPM -> frontend nginx -> backend. nginx
# appends its peer (NPM) to whatever X-Forwarded-For it received, and the
# backend's own peer is the frontend container.
FRONTEND_CONTAINER = "172.18.0.3"
NPM = "172.20.0.10"
REAL = "87.210.125.134"


def _trusted_hosts() -> str:
    match = re.search(r"--forwarded-allow-ips=([^\"]+)\"", DOCKERFILE.read_text())
    assert match, "Dockerfile CMD no longer sets --forwarded-allow-ips"
    return match.group(1)


async def _resolve_client(peer: str, xff: str) -> str | None:
    seen: dict[str, str | None] = {}

    async def app(scope, receive, send):  # noqa: ANN001
        seen["client"] = scope["client"][0] if scope.get("client") else None

    middleware = ProxyHeadersMiddleware(app, trusted_hosts=_trusted_hosts())
    scope = {
        "type": "http",
        "client": (peer, 5555),
        "headers": [(b"x-forwarded-for", xff.encode())],
    }
    await middleware(scope, None, None)
    return seen["client"]


def test_dockerfile_does_not_trust_every_proxy() -> None:
    assert _trusted_hosts().strip() != "*"


@pytest.mark.asyncio
async def test_real_client_ip_is_resolved_through_the_proxy_chain() -> None:
    assert await _resolve_client(FRONTEND_CONTAINER, f"{REAL}, {NPM}") == REAL


@pytest.mark.asyncio
@pytest.mark.parametrize("forged", ["203.0.113.77", "1.2.3.4, 5.6.7.8", "127.0.0.1"])
async def test_client_supplied_forwarded_for_cannot_override_the_real_ip(forged: str) -> None:
    # nginx received "<forged>, <real>" from NPM and appended NPM's address.
    assert await _resolve_client(FRONTEND_CONTAINER, f"{forged}, {REAL}, {NPM}") == REAL


@pytest.mark.asyncio
async def test_forwarded_for_from_an_untrusted_peer_is_ignored() -> None:
    """Someone reaching the backend directly from a public address can't set
    their own client IP at all."""
    assert await _resolve_client("198.51.100.9", "203.0.113.77") == "198.51.100.9"
