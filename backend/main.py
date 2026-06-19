from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from db.base import engine, Base
from db import models  # noqa – registers all models
from api.routes import sessions, design, export, websocket
from utils.storage import init_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    await init_storage()
    yield
    # Shutdown (nothing to clean up currently)


settings = get_settings()

app = FastAPI(
    title="AI-Native CAD-CAM Workstation",
    description="Multi-agent AI system for parametric CAD design and manufacturing",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(design.router, prefix="/api/design", tags=["design"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
