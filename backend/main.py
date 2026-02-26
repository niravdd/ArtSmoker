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
from backend.services.bedrock_client import validate_aws_credentials

logger = logging.getLogger(__name__)

# ── Frontend directory ─────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Lifespan ───────────────────────────────────────────────────────────────

_aws_status: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — runs on startup and shutdown."""
    global _aws_status

    # Startup: ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.styles_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Data directories ensured: %s", settings.data_dir)

    # Validate AWS credentials and Bedrock access
    logger.info("Validating AWS credentials and Bedrock model access...")
    _aws_status = validate_aws_credentials()

    if not _aws_status["credentials"]:
        logger.error(
            "\n"
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║  AWS CREDENTIALS NOT FOUND                                 ║\n"
            "║                                                            ║\n"
            "║  ArtSmoker requires valid AWS credentials with Bedrock     ║\n"
            "║  access. Configure credentials via one of:                 ║\n"
            "║    • Environment vars: AWS_ACCESS_KEY_ID + SECRET          ║\n"
            "║    • AWS CLI profile:  aws configure                       ║\n"
            "║    • Named profile:    ARTSMOKER_AWS_PROFILE=myprofile     ║\n"
            "║    • Instance role (EC2/Lambda/ECS)                        ║\n"
            "║                                                            ║\n"
            "║  See SPEC.md for required IAM permissions.                 ║\n"
            "╚══════════════════════════════════════════════════════════════╝"
        )
    elif _aws_status["errors"]:
        logger.warning(
            "AWS credentials valid (%s) but some Bedrock checks failed:\n  %s",
            _aws_status["identity"],
            "\n  ".join(_aws_status["errors"]),
        )
    else:
        logger.info("All AWS checks passed. Identity: %s", _aws_status["identity"])

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
    """Health check endpoint — includes AWS credential and Bedrock status."""
    return {
        "status": "ok" if _aws_status.get("credentials") else "degraded",
        "aws": {
            "credentials": _aws_status.get("credentials", False),
            "identity": _aws_status.get("identity"),
            "bedrock_models": _aws_status.get("models_region", False),
            "bedrock_images": _aws_status.get("images_region", False),
            "errors": _aws_status.get("errors", []),
        },
    }


# ── Static files (frontend) ───────────────────────────────────────────────
# Mounted LAST so that /api/* routes take priority over the catch-all static
# file handler.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    logger.info("Frontend mounted from: %s", FRONTEND_DIR)
else:
    logger.warning("Frontend directory not found at %s — static files not mounted.", FRONTEND_DIR)
