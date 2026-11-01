"""MyACE Backend — FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.api import (
    adapters,
    admin,
    auth,
    collections,
    comments,
    demo,
    doc_cache,
    freshness,
    moderation,
    profiles,
    ratings,
    sync,
)
from app.api.demo import DEMO_REQUEST_BODY_MAX_BYTES
from app.api.demo import limiter as demo_limiter
from app.core.body_limit import MaxBodySizeMiddleware
from app.core.config import settings
from app.core.database import get_session_factory, init_db
from app.services.seed_collections import seed_starter_collections

logger = logging.getLogger("myace")

DEFAULT_SECRET_KEY = "change-me-to-a-random-64-char-string"


def looks_like_real_deployment() -> bool:
    """Whether the config has clearly been customised for a non-local
    deployment — a real secret key, a TRUSTED_HOSTS list, or a non-localhost
    CORS origin. Used only to warn when that coexists with
    `APP_ENV=development`, which silently turns off every production
    hardening check below (the default-secret, TRUSTED_HOSTS, DEBUG and
    CORS-wildcard startup errors included).
    """
    if settings.app_secret_key != DEFAULT_SECRET_KEY or settings.trusted_host_list:
        return True
    local = ("localhost", "127.0.0.1", "[::1]", ".localhost")
    return any(not any(marker in o for marker in local) for o in settings.cors_origin_list)


def validate_cors_origins() -> None:
    """Reject a wildcard CORS origin outside development (L-16).

    `CORSMiddleware` below is registered with `allow_credentials=True`, so
    `CORS_ORIGINS=*` either makes the browser reject every credentialed
    cross-origin request (a mysteriously broken deployment) or reflects any
    request `Origin` back in `Access-Control-Allow-Origin` with credentials
    attached — letting any website read a logged-in user's authenticated API
    responses. Fail at startup instead of shipping either outcome, the same
    shape as the `TRUSTED_HOSTS` check below.

    Development is exempt: a wildcard origin there is a deliberate local
    convenience, and nothing is reachable beyond localhost.

    Extracted from module scope (rather than left inline) so tests can call
    it directly — see tests/test_prod_defaults.py.
    """
    if settings.app_env == "development":
        return
    if "*" in settings.cors_origin_list:
        raise RuntimeError(
            "CORS_ORIGINS contains '*', which is unsafe with allow_credentials=True: "
            "it either breaks the browser's CORS check or reflects any Origin back "
            "with credentials, letting any website read authenticated API responses. "
            "List your real frontend origin(s) explicitly, e.g. "
            "CORS_ORIGINS=https://myace.example.com"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup."""
    if settings.app_env == "development":
        await init_db()
    try:
        async with get_session_factory()() as session:
            await seed_starter_collections(session)
    except Exception:
        # Seeding must never take the app down. In particular, on a fresh
        # production deployment the backend container can start before an
        # operator has run `alembic upgrade head`, so the collections/users
        # tables may not exist yet on this very first boot — the next
        # restart after migrations run will pick the seed back up.
        logger.exception("Starter-pack seeding failed — continuing startup without it.")
    if settings.app_env == "development" and looks_like_real_deployment():
        logger.warning(
            "APP_ENV=development but this looks like a real deployment (custom secret key, "
            "TRUSTED_HOSTS or non-localhost CORS_ORIGINS). Production hardening checks "
            "(default-secret, TRUSTED_HOSTS, DEBUG and CORS-wildcard errors) are OFF and "
            "the database schema is auto-created on every boot — set APP_ENV=production "
            "in .env."
        )
    if settings.app_secret_key == DEFAULT_SECRET_KEY and settings.app_env != "development":
        raise RuntimeError(
            "APP_SECRET_KEY is still the default placeholder value. Session cookies can be "
            "forged by anyone who knows this value. Set a real random secret in .env before "
            "running in production."
        )
    if settings.debug and settings.app_env != "development":
        raise RuntimeError(
            "DEBUG is true outside app_env=development. This serves /docs and /redoc "
            "publicly. Set DEBUG=false in .env for any deployment reachable beyond "
            "localhost."
        )
    if settings.admin_bootstrap_enabled and settings.app_env != "development":
        logger.warning(
            "ADMIN_BOOTSTRAP_ENABLED is true: the next person to register becomes an admin. "
            "Set it to false in .env once you've created your own admin account, especially "
            "on a public deployment."
        )
    if not settings.settings_encryption_key:
        logger.warning(
            "SETTINGS_ENCRYPTION_KEY is not set. Admin-editable secrets (SMTP password, "
            "OAuth client secrets) cannot be saved via System Settings until it's configured — "
            "see .env.example."
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    # Gated on app_env, not `debug` (L-14): the interactive docs expose the
    # full API schema, so they belong to local development only. `debug`
    # defaults to true, which used to mean a production deployment that
    # never flipped it served /docs publicly.
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

# Rate limiter state + exception handler for app.api.demo's @limiter.limit(...)
# decorator — this is app-wide *plumbing* slowapi requires to raise 429s at
# all, not app-wide rate limiting. No route other than POST /demo/compile
# carries the decorator, so no other route is actually rate-limited by this.
app.state.limiter = demo_limiter


def _handle_rate_limit_exceeded(request: Request, exc: Exception) -> Response:
    """Custom handler, not slowapi's own `_rate_limit_exceeded_handler` —
    that one returns `{"error": "Rate limit exceeded: ..."}`, but every
    other error response in this app (FastAPI's `HTTPException`) shapes
    its body as `{"detail": ...}`, which is exactly what
    `frontend/src/lib/api.ts`'s `request()` reads. Returning the
    `{"error": ...}` shape here would silently degrade to a generic
    "HTTP 429" in the UI instead of the real rate-limit message. Rebuilds
    the same rate-limit headers slowapi's own handler injects, via the
    same private `_inject_headers` helper it uses internally.

    Starlette's `add_exception_handler()` expects `Callable[[Request,
    Exception], Response]`, but this is only ever registered for
    `RateLimitExceeded` — the `isinstance` check narrows the type for
    mypy rather than guarding real runtime behavior.
    """
    assert isinstance(exc, RateLimitExceeded)
    response = JSONResponse(
        {"detail": f"Rate limit exceeded: {exc.detail}"}, status_code=429
    )
    # slowapi ships no py.typed marker, so mypy sees this call as returning
    # `Any` despite its real (correctly-typed) runtime signature
    # `(Response, ...) -> Response` — annotate the result explicitly
    # rather than letting `Any` silently propagate as this function's
    # declared `Response` return.
    injected: Response = request.app.state.limiter._inject_headers(
        response, request.state.view_rate_limit
    )
    return injected


app.add_exception_handler(RateLimitExceeded, _handle_rate_limit_exceeded)

# Transport-level request-body caps (see app.core.body_limit for why this
# has to live at the ASGI layer rather than in a Pydantic validator).
#
# DEFAULT_REQUEST_BODY_MAX_BYTES applies to EVERY route without its own
# entry below, so an unauthenticated route such as /auth/register can no
# longer be handed an unbounded body to buffer into memory (M-3). 1 MB
# matches nginx's long-standing implicit default — now declared explicitly
# in frontend/nginx.conf so the deployed limit is intentional rather than
# inherited — and is comfortably above any legitimate JSON request in this
# API.
DEFAULT_REQUEST_BODY_MAX_BYTES = 1024 * 1024
# Bulk import legitimately carries many artifact bodies in a single request,
# so it gets its own, larger entry. frontend/nginx.conf's client_max_body_size
# must be >= this, or nginx would reject the request before the backend sees it.
BULK_IMPORT_REQUEST_BODY_MAX_BYTES = 10 * 1024 * 1024

app.add_middleware(
    MaxBodySizeMiddleware,
    limits={
        # Tighter than the default: this is the one fully-public route.
        ("POST", "/api/v1/demo/compile"): DEMO_REQUEST_BODY_MAX_BYTES,
        ("POST", "/api/v1/collections/import"): BULK_IMPORT_REQUEST_BODY_MAX_BYTES,
    },
    default_max_bytes=DEFAULT_REQUEST_BODY_MAX_BYTES,
)

# Trusted hosts — always enforce. In development, allow all hosts (safe
# default for local testing). In production, the operator MUST set
# TRUSTED_HOSTS to their real domain(s); the app will fail at startup
# with a clear error if it's left empty.
if settings.app_env == "development":
    allowed_hosts = settings.trusted_host_list or ["*"]
else:
    if not settings.trusted_host_list:
        raise RuntimeError(
            "TRUSTED_HOSTS is not set. This is required in production to prevent "
            "Host-header injection attacks. Set it to your real domain(s) in .env, "
            "e.g. TRUSTED_HOSTS=myace.macjuu.com"
        )
    allowed_hosts = settings.trusted_host_list
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# CORS middleware — reject a wildcard origin before registering it (L-16;
# `*` with allow_credentials=True is unsafe — see validate_cors_origins).
validate_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware — backs both the OIDC login handshake (state/nonce) and
# the web UI's authenticated session cookie. `https_only` is derived from
# FRONTEND_BASE_URL's scheme (Settings.session_cookie_secure), never from
# `debug` — see L-14 in that property's docstring.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key,
    session_cookie="myace_session",
    same_site="lax",
    https_only=settings.session_cookie_secure,
    max_age=14 * 24 * 3600,
)

# Register routers
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(freshness.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(demo.router, prefix="/api/v1/demo", tags=["Demo"])
app.include_router(collections.router, prefix="/api/v1/collections", tags=["Collections"])
app.include_router(ratings.router, prefix="/api/v1/collections", tags=["Ratings"])
app.include_router(comments.router, prefix="/api/v1/collections", tags=["Comments"])
app.include_router(moderation.router, prefix="/api/v1/moderation", tags=["Moderation"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["Profiles"])
app.include_router(adapters.router, prefix="/api/v1/adapters", tags=["Adapters"])
app.include_router(doc_cache.router, prefix="/api/v1/doc-cache", tags=["Documentation Cache"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["Sync"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
