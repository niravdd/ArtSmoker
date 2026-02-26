"""ArtSmoker FastAPI application — AI-Powered Game Asset Generation.

Assembles all routers, configures CORS for development, mounts the frontend
as static files, and ensures data directories exist on startup.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routers import gallery, generate, refine, styles, transcribe

logger = logging.getLogger(__name__)

# ── Frontend directory ─────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — runs on startup and shutdown."""
    # Startup: ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.styles_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Data directories ensured: %s", settings.data_dir)
    logger.info("ArtSmoker backend started.")
    yield
    # Shutdown
    logger.info("ArtSmoker backend shutting down.")


# ── Application ────────────────────────────────────────────────────────────

app = FastAPI(
    title="ArtSmoker",
    description="AI-Powered Game Asset Generation",
    lifespan=lifespan,
)

# ── CORS (development mode — allow all origins) ───────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(styles.router)
app.include_router(generate.router)
app.include_router(refine.router)
app.include_router(transcribe.router)
app.include_router(gallery.router)


# ── Health check ───────────────────────────────────────────────────────────

@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "ok"}


# ── Static files (frontend) ───────────────────────────────────────────────
# Mounted LAST so that /api/* routes take priority over the catch-all static
# file handler.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    logger.info("Frontend mounted from: %s", FRONTEND_DIR)
else:
    logger.warning("Frontend directory not found at %s — static files not mounted.", FRONTEND_DIR)
