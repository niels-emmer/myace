"""MyACE Backend — FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import adapters, admin, auth, collections, doc_cache, profiles
from app.core.config import settings
from app.core.database import get_session_factory, init_db
from app.services.seed_collections import seed_starter_collections

logger = logging.getLogger("myace")

DEFAULT_SECRET_KEY = "change-me-to-a-random-64-char-string"


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
    if settings.app_secret_key == DEFAULT_SECRET_KEY and settings.app_env != "development":
        raise RuntimeError(
            "APP_SECRET_KEY is still the default placeholder value. Session cookies can be "
            "forged by anyone who knows this value. Set a real random secret in .env before "
            "running in production."
        )
    if settings.debug and settings.app_env != "development":
        logger.warning(
            "DEBUG is true outside app_env=development. This exposes /docs and /redoc "
            "publicly and disables secure-only session cookies — set DEBUG=false for any "
            "deployment reachable beyond localhost."
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
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware — backs both the OIDC login handshake (state/nonce) and
# the web UI's authenticated session cookie.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key,
    session_cookie="myace_session",
    same_site="lax",
    https_only=not settings.debug,
    max_age=14 * 24 * 3600,
)

# Register routers
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(collections.router, prefix="/api/v1/collections", tags=["Collections"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["Profiles"])
app.include_router(adapters.router, prefix="/api/v1/adapters", tags=["Adapters"])
app.include_router(doc_cache.router, prefix="/api/v1/doc-cache", tags=["Documentation Cache"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
