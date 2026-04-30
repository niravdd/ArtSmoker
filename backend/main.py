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

# Suppress noisy third-party loggers
logging.getLogger("botocore.credentials").setLevel(logging.WARNING)
logging.getLogger("botocore.httpsession").setLevel(logging.WARNING)
logging.getLogger("botocore.parsers").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.config import settings
from backend.routers import admin, browse, chat, custom_deploy, gallery, generate, refine, styles, transcribe, typestudio, video
from backend.services.bedrock_client import validate_aws_credentials

logger = logging.getLogger(__name__)

# ── Frontend directory ─────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Config Freshness Check ────────────────────────────────────────────────

def _check_and_refresh_configs():
    """Check if model registry needs first-time Sync from AWS.

    Looks for 'aws_account_discovered' in the user prefs file (.user.json,
    gitignored). Set only by a successful Sync from AWS. If missing, this is
    a fresh deployment → auto-Sync runs after credential validation.
    Stored in .user.json so fresh git clones always trigger auto-Sync.

    Prompt templates are always regenerated from code _DEFAULTS on startup
    (handled by prompt_templates._load()).
    """
    import json

    try:
        from backend.services.model_registry import _USER_PREFS_PATH
        needs_sync = False
        # Check .user.json for the discovery stamp (gitignored, deployment-specific)
        if _USER_PREFS_PATH.exists():
            prefs = json.loads(_USER_PREFS_PATH.read_text())
            ts = prefs.get("_meta", {}).get("aws_account_discovered", {}).get("timestamp")
            if ts:
                logger.info("Model registry: AWS account discovered %s", ts[:19])
            else:
                logger.info("Model registry: model availability in Amazon Bedrock not yet discovered — will auto-Sync")
                needs_sync = True
        else:
            logger.info("Model registry: model availability in Amazon Bedrock not yet discovered — will auto-Sync")
            needs_sync = True

        _check_and_refresh_configs._needs_registry_sync = needs_sync
    except Exception as exc:
        logger.warning("Model registry check failed: %s", exc)
        _check_and_refresh_configs._needs_registry_sync = False

_check_and_refresh_configs._needs_registry_sync = False


# ── Lifespan ───────────────────────────────────────────────────────────────

_aws_status: dict = {}
_server_state: dict = {"ready": False, "sync_in_progress": False, "sync_message": ""}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — runs on startup and shutdown."""
    global _aws_status

    # Auto-update: check GitHub for new version and pull if available.
    # If code was updated, the process restarts here (os.execv) and this
    # function runs again with the new code — the second pass finds
    # "Already up to date" and continues normally.
    update_result = {}
    try:
        from backend.services.auto_update import check_and_update
        update_result = check_and_update()
        # If updated, check_and_update() calls os.execv — we never reach here.
        # If we're here, either no update or update was skipped.
        if update_result.get("skipped_reason"):
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

    # Check if model registry and prompt templates need regeneration
    _check_and_refresh_configs()

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

    # Auto-Sync model registry if stale or missing (requires valid AWS credentials)
    if _check_and_refresh_configs._needs_registry_sync and _aws_status.get("credentials"):
        # Run Sync in a background thread so the server starts immediately.
        # The frontend shows a "Setting Up" modal while sync_in_progress is true.
        import threading

        def _sync_progress(msg):
            _server_state["sync_message"] = msg
            _server_state.setdefault("sync_log", []).append(msg)

        def _run_sync():
            import asyncio
            try:
                _server_state["sync_in_progress"] = True
                _server_state["sync_log"] = []
                _sync_progress("Discovering model availability in Amazon Bedrock in your AWS account...")
                logger.info("Auto-Sync: %s", _server_state["sync_message"])

                from backend.routers.admin import refresh_all_regions, _get_bedrock_regions, _fetch_image_pricing
                from backend.services.model_registry import get_registry, _save as _reg_save
                _reg_save._silent = True

                try:
                    # Step 1: Discover regions
                    _sync_progress("Discovering Amazon Bedrock regions...")
                    all_regions = _get_bedrock_regions()
                    registry = get_registry()
                    registry["bedrock_regions"] = all_regions
                    _reg_save()
                    _sync_progress(f"Found {len(all_regions)} regions. Fetching model pricing...")

                    # Step 2: Pricing
                    pricing_data = _fetch_image_pricing()
                    if pricing_data:
                        registry["image_pricing"] = pricing_data
                        _reg_save()
                    _sync_progress(f"Scanning {len(all_regions)} regions for available models...")

                    # Step 3: Scan each region
                    from backend.services.model_registry import update_image_model
                    for key in list(registry.get("image_models", {}).keys()):
                        update_image_model(key, {"available_regions": []})
                    for key in list(registry.get("chat_models", {}).keys()):
                        registry["chat_models"][key]["available_regions"] = []

                    total_new = 0
                    total_updated = 0
                    failed_regions = []
                    from concurrent.futures import ThreadPoolExecutor as _TPE, TimeoutError as _TE

                    for idx, region in enumerate(all_regions):
                        _sync_progress(f"Scanning region {idx + 1}/{len(all_regions)}: {region}...")
                        # Per-region timeout to avoid hanging on unreachable regions
                        region_new = 0
                        region_updated = 0
                        pool = _TPE(max_workers=1)
                        try:
                            future = pool.submit(
                                lambda r=region: asyncio.run(
                                    __import__('backend.routers.admin', fromlist=['auto_register_image_models']).auto_register_image_models(r)
                                )
                            )
                            result = future.result(timeout=20)
                            region_new = result.get("new_count", 0)
                            region_updated = result.get("updated_count", 0)
                            total_new += region_new
                            total_updated += region_updated
                        except _TE:
                            _sync_progress(f"Skipped {region} (timed out)")
                            failed_regions.append({"region": region, "reason": "timed out"})
                            pool.shutdown(wait=False, cancel_futures=True)
                            continue
                        except Exception as region_exc:
                            _sync_progress(f"Skipped {region} (error)")
                            failed_regions.append({"region": region, "reason": str(region_exc)[:100]})
                            pool.shutdown(wait=False, cancel_futures=True)
                            continue
                        finally:
                            pool.shutdown(wait=False)
                        # Custom models (with timeout)
                        try:
                            from backend.routers.admin import _discover_custom_models
                            cpool = _TPE(max_workers=1)
                            try:
                                cpool.submit(_discover_custom_models, region).result(timeout=15)
                            except _TE:
                                pass
                            finally:
                                cpool.shutdown(wait=False)
                        except Exception:
                            pass
                        # Report per-region result with model count
                        region_total = region_new + region_updated
                        if region_total:
                            _sync_progress(f"Done {region} — {region_total} model{'s' if region_total != 1 else ''} found")
                        else:
                            _sync_progress(f"Done {region} — no models")

                    # Step 4: Prune (skip custom-hosted models — they don't use Bedrock regions)
                    _sync_progress("Finalizing — checking model availability...")
                    for key, cfg in list(registry.get("image_models", {}).items()):
                        if cfg.get("model_source") == "custom_hosted":
                            continue
                        if not cfg.get("available_regions") and cfg.get("enabled", True):
                            update_image_model(key, {"enabled": False})

                    # Stamp
                    from datetime import datetime, timezone
                    from backend.services.model_registry import _save_user_pref
                    registry["last_synced_summary"] = f"{total_new} new, {total_updated} updated across {len(all_regions)} regions"
                    if failed_regions:
                        registry["regions_not_opted_in"] = failed_regions
                        logger.info("Auto-Sync: %d region(s) not opted in or unavailable: %s",
                                    len(failed_regions), ", ".join(r["region"] for r in failed_regions))
                    else:
                        registry.pop("regions_not_opted_in", None)
                    # Clean up old key name
                    registry.pop("sync_failed_regions", None)
                    _save_user_pref("_meta", "aws_account_discovered", "timestamp", datetime.now(timezone.utc).isoformat())
                    _reg_save()

                finally:
                    _reg_save._silent = False

                _server_state["sync_in_progress"] = False
                _server_state["sync_message"] = ""
                logger.info("Auto-Sync: done — %d new, %d updated across %d regions",
                            total_new, total_updated, len(all_regions))
            except Exception as exc:
                _server_state["sync_in_progress"] = False
                _server_state["sync_message"] = ""
                _server_state["sync_error"] = str(exc)
                logger.warning("Auto-Sync failed — run Sync manually from Model Settings: %s", exc)

        def _run_sync_and_mark_ready():
            _run_sync()
            _server_state["ready"] = True
            if not _server_state.get("sync_error"):
                logger.info("ArtSmoker ready.")
            else:
                logger.info("ArtSmoker ready (Sync failed — run Sync from AWS in Model Settings).")

        sync_thread = threading.Thread(target=_run_sync_and_mark_ready, daemon=True)
        sync_thread.start()
        logger.info("Auto-Sync: started in background")
    elif _check_and_refresh_configs._needs_registry_sync:
        logger.warning("Model registry needs refresh — configure AWS credentials, then Sync from Model Settings.")

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

    # Start periodic auto-update scheduler (checks every 24h, restarts if idle)
    from backend.services.auto_update import start_periodic_checker, stop_periodic_checker
    start_periodic_checker()

    # Resume any pending async jobs from S3 (non-blocking background thread)
    import threading
    def _resume_async_jobs():
        try:
            from backend.services.async_jobs import load_persisted_jobs, resume_pending_jobs, _ensure_poller
            loaded = load_persisted_jobs()
            if loaded > 0:
                _ensure_poller()
                resumed = resume_pending_jobs()
                logger.info("Async jobs: %d loaded, %d resumed from S3", loaded, resumed)
        except Exception as exc:
            logger.debug("Async jobs resume: %s", exc)

    threading.Thread(target=_resume_async_jobs, daemon=True, name="async-resume").start()

    # Verify auto-scaling for deployed custom model endpoints.
    # Only registers auto-scaling for endpoints whose model is confirmed ready.
    # For endpoints still loading, the readiness monitor will handle it.
    def _verify_auto_scaling():
        try:
            from backend.services.model_registry import get_registry
            from backend.services.sagemaker_deployer import _register_auto_scaling_after_ready, check_endpoint_status
            reg = get_registry()
            for key, cfg in reg.get("image_models", {}).items():
                if cfg.get("model_source") != "custom_hosted":
                    continue
                dep = cfg.get("deployment", {})
                if dep.get("endpoint_type") != "async":
                    continue
                ep_name = dep.get("endpoint_name", "")
                if not ep_name:
                    continue
                status = check_endpoint_status(ep_name)
                if status.get("status") != "InService":
                    continue
                # Only register auto-scaling if model is confirmed ready
                # (check_endpoint_status triggers readiness check, which will
                #  call _register_auto_scaling_after_ready when ready)
                if not status.get("warming_up"):
                    logger.debug("Endpoint %s is ready — ensuring auto-scaling", ep_name)
                    _register_auto_scaling_after_ready(ep_name)
                else:
                    logger.info("Endpoint %s still warming up — auto-scaling deferred until model ready", ep_name)
        except Exception as exc:
            logger.debug("Auto-scaling verification: %s", exc)
    threading.Thread(target=_verify_auto_scaling, daemon=True, name="autoscale-verify").start()

    # Mark ready only if Sync is not running in background
    # (background Sync thread will set ready=True when it completes)
    if not _server_state["sync_in_progress"]:
        _server_state["ready"] = True
        logger.info("ArtSmoker ready.")
    yield
    # Shutdown
    stop_periodic_checker()
    from backend.services.async_jobs import stop_poller
    stop_poller()
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
        # Track request activity for auto-update idle detection
        # Exclude health/status polls — they don't indicate real user activity
        if not request.url.path.startswith("/api/update-status"):
            from backend.services.auto_update import record_request
            record_request()

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
app.include_router(custom_deploy.router)


# ── Global exception handler — logs full traceback on unhandled errors ────

@app.exception_handler(Exception)
async def _unhandled_exception_handler(request, exc):
    import traceback
    tb = traceback.format_exc()
    logger.error("Unhandled %s at %s %s:\n%s", type(exc).__name__, request.method, request.url.path, tb)
    from starlette.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


# ── Frontend load tracking ─────────────────────────────────────────────────

@app.get("/api/update-status", tags=["health"])
async def get_update_status():
    """Check auto-update status — frontend polls this to detect pending restarts."""
    from backend.services.auto_update import get_update_status, is_dev_mode
    status = get_update_status()
    import os as _os
    status["disabled"] = is_dev_mode() or _os.environ.get("ARTSMOKER_AUTO_UPDATE", "").lower() in ("false", "0", "no")
    return status


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

@app.get("/api/sync-progress", tags=["health"])
async def sync_progress_stream():
    """SSE stream of sync progress — live updates during auto-Sync."""
    import time
    from starlette.responses import StreamingResponse

    def generate():
        import json
        last_log_len = 0
        try:
            while _server_state.get("sync_in_progress"):
                sync_log = _server_state.get("sync_log", [])
                if len(sync_log) > last_log_len:
                    for entry in sync_log[last_log_len:]:
                        try:
                            from backend.services.model_registry import get_registry
                            reg = get_registry()
                            counts = {
                                "image": sum(1 for m in reg.get("image_models", {}).values() if m.get("model_purpose") == "text_to_image"),
                                "chat": len(reg.get("chat_models", {})),
                                "video": len(reg.get("video_models", {})),
                            }
                        except Exception:
                            counts = {}
                        yield f"data: {json.dumps({'message': entry, 'models': counts, 'regions_scanned': last_log_len})}\n\n"
                    last_log_len = len(sync_log)
                time.sleep(1)
            # Final event
            try:
                from backend.services.model_registry import get_registry
                reg = get_registry()
                final_counts = {
                    "image": sum(1 for m in reg.get("image_models", {}).values() if m.get("model_purpose") == "text_to_image"),
                    "chat": len(reg.get("chat_models", {})),
                    "video": len(reg.get("video_models", {})),
                }
            except Exception:
                final_counts = {}
            yield f"data: {json.dumps({'message': 'done', 'ready': True, 'error': _server_state.get('sync_error', ''), 'models': final_counts})}\n\n"
        except GeneratorExit:
            pass  # Client disconnected — normal for SSE
        except Exception:
            pass  # Don't crash on SSE errors

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint — includes AWS credential and Bedrock status."""
    from backend.config import APP_VERSION
    return {
        "version": APP_VERSION,
        "status": "ok" if _server_state["ready"] else "starting",
        "ready": _server_state["ready"],
        "sync_in_progress": _server_state["sync_in_progress"],
        "sync_message": _server_state["sync_message"],
        "sync_error": _server_state.get("sync_error", ""),
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
