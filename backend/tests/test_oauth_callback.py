"""Tests for the OIDC/OAuth2 login -> callback round trip, notably PKCE handling.

Regression coverage for a bug where the callback never forwarded the
code_verifier stashed in the session by login(), causing every real
GitHub/Google/OIDC login to fail at the provider's token endpoint with
"A code_verifier was not included, but the authorization request included
a code_challenge." Authlib only auto-manages code_verifier storage/replay
when code_challenge_method is set on the client at registration time; this
app passes it per-request instead, so the app must round-trip it itself.
"""

import base64
import hashlib

import pytest
from httpx import AsyncClient
from starlette.responses import RedirectResponse


class FakeOAuthClient:
    """Stands in for authlib's StarletteOAuth2App without any network calls."""

    def __init__(self) -> None:
        self.authorize_redirect_kwargs: dict | None = None
        self.authorize_access_token_kwargs: dict | None = None

    async def authorize_redirect(self, request, redirect_uri, **kwargs):  # noqa: ANN001
        self.authorize_redirect_kwargs = kwargs
        return RedirectResponse(url="https://provider.example.com/authorize", status_code=302)

    async def authorize_access_token(self, request, **kwargs):  # noqa: ANN001
        self.authorize_access_token_kwargs = kwargs
        return {
            "access_token": "fake-access-token",
            "userinfo": {
                "sub": "12345",
                "email": "octocat@example.com",
                "name": "The Octocat",
            },
        }


@pytest.mark.asyncio
async def test_callback_forwards_the_code_verifier_login_stored(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
):
    fake_client = FakeOAuthClient()
    monkeypatch.setattr("app.api.auth.get_oauth_client", lambda provider, config: fake_client)

    # Uses the generic "oidc" provider (not "github") deliberately — this
    # test is about PKCE mechanics common to all providers, not GitHub's
    # specific /user field-shape normalization (see FakeGitHubClient below).
    login_resp = await async_client.get("/api/v1/auth/login/oidc", follow_redirects=False)
    assert login_resp.status_code == 302
    assert fake_client.authorize_redirect_kwargs is not None
    sent_code_challenge = fake_client.authorize_redirect_kwargs["code_challenge"]

    callback_resp = await async_client.get(
        "/api/v1/auth/callback/oidc?code=fake-code&state=fake-state",
        follow_redirects=False,
    )
    assert callback_resp.status_code == 302
    assert callback_resp.headers["location"] == "/"

    assert fake_client.authorize_access_token_kwargs is not None
    code_verifier = fake_client.authorize_access_token_kwargs.get("code_verifier")
    assert code_verifier, "code_verifier must be forwarded to authorize_access_token"

    # The verifier the callback sent must be the one that actually produced
    # the challenge the login redirect sent to the provider (S256).
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    recomputed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert recomputed_challenge == sent_code_challenge


class FakeGitHubClient:
    """Mimics GitHub's real shape: authorize_access_token() returns a token
    dict with no "userinfo" key (GitHub isn't OIDC, no id_token), so the
    callback must fall through to userinfo(), and that in turn returns
    GitHub's actual /user fields (id/login/avatar_url, no sub/picture)."""

    def __init__(self, github_user: dict, emails: list[dict] | None = None) -> None:
        self._github_user = github_user
        self._emails = emails or []
        self.get_calls: list[str] = []

    async def authorize_redirect(self, request, redirect_uri, **kwargs):  # noqa: ANN001
        return RedirectResponse(url="https://github.com/login/oauth/authorize", status_code=302)

    async def authorize_access_token(self, request, **kwargs):  # noqa: ANN001
        return {"access_token": "fake-github-token"}

    async def userinfo(self, **kwargs):  # noqa: ANN001
        return self._github_user

    async def get(self, url, **kwargs):  # noqa: ANN001
        self.get_calls.append(url)

        class _Resp:
            def __init__(self, data):
                self._data = data

            def raise_for_status(self):
                pass

            def json(self):
                return self._data

        assert url == "https://api.github.com/user/emails"
        return _Resp(self._emails)


@pytest.mark.asyncio
async def test_github_callback_normalizes_userinfo_shape(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
):
    """GitHub's /user has id/login/avatar_url, not the OIDC sub/picture
    claims — the callback must map them, not crash or store null/None."""
    fake_client = FakeGitHubClient(
        github_user={
            "id": 987654,
            "login": "octocat",
            "name": None,
            "email": "octocat@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/987654",
        },
    )
    monkeypatch.setattr("app.api.auth.get_oauth_client", lambda provider, config: fake_client)

    await async_client.get("/api/v1/auth/login/github", follow_redirects=False)
    resp = await async_client.get(
        "/api/v1/auth/callback/github?code=fake-code&state=fake-state",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"

    me = await async_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "octocat@example.com"
    assert body["display_name"] == "octocat"  # falls back to login, name was None


@pytest.mark.asyncio
async def test_github_callback_falls_back_to_emails_endpoint_when_email_private(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
):
    """A user with no public email on GitHub still has one at /user/emails —
    the callback must fetch it instead of creating an account with no email."""
    fake_client = FakeGitHubClient(
        github_user={
            "id": 111222,
            "login": "privateemailuser",
            "name": "Private Email User",
            "email": None,
            "avatar_url": "https://avatars.githubusercontent.com/u/111222",
        },
        emails=[
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "primary@example.com", "primary": True, "verified": True},
        ],
    )
    monkeypatch.setattr("app.api.auth.get_oauth_client", lambda provider, config: fake_client)

    await async_client.get("/api/v1/auth/login/github", follow_redirects=False)
    resp = await async_client.get(
        "/api/v1/auth/callback/github?code=fake-code&state=fake-state",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert fake_client.get_calls == ["https://api.github.com/user/emails"]

    me = await async_client.get("/api/v1/auth/me")
    assert me.json()["email"] == "primary@example.com"


@pytest.mark.asyncio
async def test_github_callback_rejects_when_no_verified_email(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
):
    fake_client = FakeGitHubClient(
        github_user={
            "id": 333444,
            "login": "noverifiedemail",
            "name": None,
            "email": None,
            "avatar_url": None,
        },
        emails=[{"email": "unverified@example.com", "primary": True, "verified": False}],
    )
    monkeypatch.setattr("app.api.auth.get_oauth_client", lambda provider, config: fake_client)

    await async_client.get("/api/v1/auth/login/github", follow_redirects=False)
    resp = await async_client.get(
        "/api/v1/auth/callback/github?code=fake-code&state=fake-state",
        follow_redirects=False,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_callback_does_not_replay_the_same_code_verifier_twice(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
):
    """The stashed code_verifier is single-use — a second callback call
    (e.g. a user double-hitting the redirect) must not silently reuse it."""
    fake_client = FakeOAuthClient()
    monkeypatch.setattr("app.api.auth.get_oauth_client", lambda provider, config: fake_client)

    await async_client.get("/api/v1/auth/login/oidc", follow_redirects=False)
    await async_client.get(
        "/api/v1/auth/callback/oidc?code=fake-code&state=fake-state",
        follow_redirects=False,
    )
    first_verifier = fake_client.authorize_access_token_kwargs.get("code_verifier")
    assert first_verifier

    await async_client.get(
        "/api/v1/auth/callback/oidc?code=fake-code&state=fake-state",
        follow_redirects=False,
    )
    second_verifier = fake_client.authorize_access_token_kwargs.get("code_verifier")
    assert second_verifier is None
