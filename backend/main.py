"""ArtSmoker FastAPI application — AI-Powered Game Asset Generation.

Assembles all routers, configures CORS for development, mounts the frontend
as static files, and ensures data directories exist on startup.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

# ── Coloured logging with timestamps ──────────────────────────────────────

class _ColorFormatter(logging.Formatter):
    """ANSI-coloured log formatter with distinct level colours."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    LEVEL_STYLES = {
        logging.DEBUG:    ("\033[38;5;44m",   "DEBUG   "),   # teal
        logging.INFO:     ("\033[38;5;40m",   "INFO    "),   # vivid green
        logging.WARNING:  ("\033[38;5;220m",  "WARNING "),   # bright yellow
        logging.ERROR:    ("\033[38;5;196m",  "ERROR   "),   # vivid red
        logging.CRITICAL: ("\033[38;5;201m",  "CRITICAL"),   # hot pink
    }
    TS_COLOR = "\033[38;5;245m"   # medium grey for timestamp
    NAME_COLOR = "\033[38;5;39m"  # sky blue for module name

    # Clean up misleading logger names for display
    NAME_MAP = {"uvicorn.error": "uvicorn", "uvicorn.access": "uvicorn.access"}

    def format(self, record):
        color, label = self.LEVEL_STYLES.get(record.levelno, ("\033[0m", record.levelname.ljust(8)))
        ts = self.formatTime(record, self.datefmt)
        name = self.NAME_MAP.get(record.name, record.name)
        msg = record.getMessage()
        return (
            f"{self.TS_COLOR}{ts}{self.RESET}  "
            f"{color}{self.BOLD}{label}{self.RESET}  "
            f"{self.NAME_COLOR}{name}{self.RESET}  "
            f"{msg}"
        )

_log_datefmt = "%Y-%m-%d %H:%M:%S"
_color_handler = logging.StreamHandler()
_color_handler.setFormatter(_ColorFormatter(datefmt=_log_datefmt))

# Apply to root logger
logging.root.setLevel(logging.INFO)
logging.root.handlers = [_color_handler]

# Override uvicorn's loggers to use the same coloured format
for _uv_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    _uv_logger = logging.getLogger(_uv_name)
    _uv_logger.handlers = [_color_handler]
    _uv_logger.propagate = False

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.config import settings
from backend.routers import admin, browse, chat, gallery, generate, refine, styles, transcribe, typestudio, video
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

    # Auto-update: check GitHub for new version and pull if available
    update_result = {}
    try:
        from backend.services.auto_update import check_and_update
        update_result = check_and_update()
        if update_result.get("updated"):
            logger.info("Auto-update: %s → %s", update_result["from_version"], update_result["to_version"])
        elif update_result.get("skipped_reason"):
            logger.info("Auto-update: %s", update_result["skipped_reason"])
        elif update_result.get("error"):
            logger.info("Auto-update: check failed (%s)", update_result["error"])
    except Exception as exc:
        logger.info("Auto-update: unavailable (%s)", exc)

    # Startup: ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.styles_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "chat").mkdir(parents=True, exist_ok=True)
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

    # Initialize telemetry
    from backend.services.telemetry import init as telemetry_init, track_server_start, track_server_stop, track_auto_update
    telemetry_init()

    # Track auto-update result first (happened before server_start)
    if update_result.get("checked"):
        track_auto_update(
            updated=update_result.get("updated", False),
            from_version=update_result.get("from_version", ""),
            to_version=update_result.get("to_version", ""),
            skipped_reason=update_result.get("skipped_reason", ""),
        )

    track_server_start()

    logger.info("ArtSmoker backend started.")
    yield
    # Shutdown
    track_server_stop()
    logger.info("ArtSmoker backend shutting down.")


# ── Application ────────────────────────────────────────────────────────────

app = FastAPI(
    title="ArtSmoker",
    description="AI-Powered Game Asset Generation",
    lifespan=lifespan,
)

# ── No-cache for frontend assets (development) ───────────────────────────

class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(NoCacheStaticMiddleware)

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
app.include_router(browse.router)
app.include_router(typestudio.router)
app.include_router(video.router)
app.include_router(chat.router)
app.include_router(admin.router)


# ── Frontend load tracking ─────────────────────────────────────────────────

@app.post("/api/ping", tags=["telemetry"])
async def frontend_ping(request: Request):
    """Lightweight endpoint called once on frontend page load.
    Accepts optional client info from the browser."""
    from backend.services.telemetry import track_frontend_load
    try:
        body = await request.json()
    except Exception:
        body = {}
    track_frontend_load(
        client_os=body.get("os", ""),
        client_browser=body.get("browser", ""),
        screen=body.get("screen", ""),
    )
    return {"ok": True}


# ── Health check ───────────────────────────────────────────────────────────

@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint — includes AWS credential and Bedrock status."""
    from backend.config import APP_VERSION
    return {
        "version": APP_VERSION,
        "status": "ok" if _aws_status.get("credentials") else "degraded",
        "aws": {
            "credentials": _aws_status.get("credentials", False),
            "identity": _aws_status.get("identity"),
            "bedrock_models": _aws_status.get("models_region", False),
            "bedrock_images": _aws_status.get("images_region", False),
            "errors": _aws_status.get("errors", []),
        },
    }


# ── Version check endpoint ────────────────────────────────────────────────

@app.get("/api/admin/check-update", tags=["admin"])
async def check_for_update():
    """Check if a newer version is available on GitHub (without pulling)."""
    from backend.config import APP_VERSION
    try:
        from backend.services.auto_update import _git, _read_version, PROJECT_ROOT
        _git("fetch", "origin", "main", "--quiet")
        local_sha = _git("rev-parse", "HEAD").strip()
        remote_sha = _git("rev-parse", "origin/main").strip()
        behind = int(_git("rev-list", "--count", f"HEAD..origin/main").strip())

        # Read remote version from fetched origin/main
        remote_version = APP_VERSION  # default
        try:
            raw = _git("show", "origin/main:backend/config.py")
            for line in raw.splitlines():
                if line.startswith("APP_VERSION"):
                    remote_version = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        except Exception:
            pass

        return {
            "current_version": APP_VERSION,
            "latest_version": remote_version,
            "update_available": behind > 0,
            "commits_behind": behind,
        }
    except Exception as exc:
        return {
            "current_version": APP_VERSION,
            "latest_version": None,
            "update_available": False,
            "error": str(exc),
        }


# ── Client-side log endpoint ──────────────────────────────────────────────

_client_logger = logging.getLogger("artsmoker.client")


@app.post("/api/log", tags=["system"])
async def client_log(request: Request):
    """Receive log entries from the frontend for server-side recording."""
    body = await request.json()
    level = body.get("level", "info").lower()
    message = body.get("message", "")
    context = body.get("context", "")

    log_line = f"[CLIENT] {message}"
    if context:
        log_line += f" | {context}"

    if level == "error":
        _client_logger.error(log_line)
    elif level == "warning":
        _client_logger.warning(log_line)
    else:
        _client_logger.info(log_line)

    return {"ok": True}


# ── Static files (frontend) ───────────────────────────────────────────────
# Mounted LAST so that /api/* routes take priority over the catch-all static
# file handler.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    logger.info("Frontend mounted from: %s", FRONTEND_DIR)
else:
    logger.warning("Frontend directory not found at %s — static files not mounted.", FRONTEND_DIR)
