from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import design, export, sessions, websocket
from config import get_settings
from db import models  # noqa – registers all models
from db.base import Base, engine
from utils.storage import init_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    Base.metadata.create_all(bind=engine)
    await init_storage()
    yield
    # Shutdown - cleanup if needed


settings = get_settings()

app = FastAPI(
    title="AI-Native CAD-CAM Workstation",
    description="Multi-agent AI system for parametric CAD design and manufacturing",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration - secure in production
cors_origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=(settings.dev_mode),  # Only allow credentials in dev mode
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Routers
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(design.router, prefix="/api/design", tags=["design"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/api/health")
async def health():
    """Health check endpoint for container orchestration."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "dev_mode": settings.dev_mode,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI-Native CAD-CAM Workstation API",
        "docs": "/docs",
        "health": "/api/health",
    }
