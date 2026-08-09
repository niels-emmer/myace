"""MyACE Backend — FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import adapters, auth, collections, doc_cache, profiles
from app.core.config import settings
from app.core.database import init_db

logger = logging.getLogger("myace")

DEFAULT_SECRET_KEY = "change-me-to-a-random-64-char-string"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup."""
    if settings.app_env == "development":
        await init_db()
    if settings.app_secret_key == DEFAULT_SECRET_KEY and settings.app_env != "development":
        logger.warning(
            "APP_SECRET_KEY is still the default placeholder value. Session cookies can be "
            "forged by anyone who knows this value — set a real random secret before exposing "
            "this deployment beyond localhost."
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

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
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(collections.router, prefix="/api/v1/collections", tags=["Collections"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["Profiles"])
app.include_router(adapters.router, prefix="/api/v1/adapters", tags=["Adapters"])
app.include_router(doc_cache.router, prefix="/api/v1/doc-cache", tags=["Documentation Cache"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name, "version": "0.1.0"}
