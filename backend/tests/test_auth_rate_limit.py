"""The credential-guessing auth routes are rate-limited end to end.

Covers the 429 path that `_handle_rate_limit_exceeded` exists for: the tenth
failed login is allowed, the eleventh is rejected with this app's normal
`{"detail": ...}` shape (not slowapi's default `{"error": ...}`), and the
limiter is reset afterwards so no other test inherits the exhausted bucket.
"""

from httpx import AsyncClient

from app.core.ratelimit import auth_limiter


async def test_auth_login_is_rate_limited(async_client: AsyncClient) -> None:
    auth_limiter.reset()
    auth_limiter.enabled = True
    try:
        responses = [
            await async_client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "wrong-password"},
            )
            for _ in range(11)
        ]

        assert [r.status_code for r in responses[:10]] == [401] * 10
        limited = responses[10]
        assert limited.status_code == 429
        assert "detail" in limited.json()
        assert limited.json()["detail"].startswith("Rate limit exceeded")
    finally:
        auth_limiter.enabled = False
        auth_limiter.reset()


async def test_rate_limit_buckets_are_independent(async_client: AsyncClient) -> None:
    """Exhausting the auth bucket must not throttle the public demo route."""
    auth_limiter.reset()
    auth_limiter.enabled = True
    try:
        for _ in range(11):
            await async_client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "wrong-password"},
            )

        demo = await async_client.post(
            "/api/v1/demo/compile", json={"markdown": "## rule\n\nbody"}
        )
        assert demo.status_code == 200
    finally:
        auth_limiter.enabled = False
        auth_limiter.reset()
