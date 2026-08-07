"""MyACE Backend — FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import auth, collections, profiles, adapters, doc_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup."""
    if settings.app_env == "development":
        await init_db()
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
