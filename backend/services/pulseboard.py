"""PulseBoard SDK — Zero-dependency telemetry client.

Drop this file into any Python project and call pulse() on startup.
No pip install needed — uses only stdlib.

Usage:
    from pulseboard import pulse
    pulse("your_api_key_here", event="app_started", properties={"version": "1.0"})

Or for ArtSmoker-style integration:
    from pulseboard import PulseBoard
    pb = PulseBoard(api_key="pb_...", endpoint="https://your-cloudfront-url/ingest")
    pb.track("app_started", version="1.2", os="Darwin")
"""

import hashlib
import json
import platform
import threading
import urllib.request
import uuid

# Default endpoint — override with your CloudFront distribution URL
DEFAULT_ENDPOINT = "https://your-pulseboard.cloudfront.net/ingest"


def pulse(
    api_key: str,
    event: str = "app_started",
    properties: dict | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    distinct_id: str | None = None,
):
    """Send a single telemetry pulse. Fire-and-forget, never blocks or crashes.

    Args:
        api_key: Your PulseBoard project API key (starts with pb_).
        event: Event name (e.g. "app_started", "generation_complete").
        properties: Optional dict of properties (version, os, arch, etc.).
        endpoint: PulseBoard ingest URL.
        distinct_id: Unique deployment ID. Auto-generated from machine fingerprint if omitted.
    """
    if not api_key:
        return

    props = properties or {}
    # Auto-populate common properties if not provided
    if "os" not in props:
        props["os"] = platform.system()
    if "os_version" not in props:
        props["os_version"] = platform.release()
    if "arch" not in props:
        props["arch"] = platform.machine()
    if "python" not in props:
        props["python"] = platform.python_version()
    if "hostname_hash" not in props:
        props["hostname_hash"] = hashlib.sha256(platform.node().encode()).hexdigest()[:8]
    if "cpu_count" not in props:
        try:
            import os as _os
            props["cpu_count"] = _os.cpu_count() or 0
        except Exception:
            pass

    if not distinct_id:
        distinct_id = _machine_id()

    payload = json.dumps({
        "api_key": api_key,
        "event": event,
        "distinct_id": distinct_id,
        "properties": props,
    }).encode("utf-8")

    def _send():
        try:
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # Never crash the host app for telemetry

    threading.Thread(target=_send, daemon=True).start()


def _machine_id() -> str:
    """Generate a stable anonymous machine fingerprint.

    Uses hostname + platform + machine to create a deterministic hash.
    No PII is stored — just a hex digest for unique deployment counting.
    """
    raw = f"{platform.node()}:{platform.system()}:{platform.machine()}:{platform.processor()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class PulseBoard:
    """Reusable telemetry client for structured event tracking.

    Usage:
        pb = PulseBoard(api_key="pb_...", endpoint="https://...")
        pb.track("app_started", version="1.2")
        pb.track("generation_complete", model="nova_canvas", duration=7.2)
    """

    def __init__(self, api_key: str, endpoint: str = DEFAULT_ENDPOINT, distinct_id: str | None = None):
        self.api_key = api_key
        self.endpoint = endpoint
        self.distinct_id = distinct_id or _machine_id()

    def track(self, event: str, **properties):
        """Track a named event with optional properties."""
        pulse(
            api_key=self.api_key,
            event=event,
            properties=properties,
            endpoint=self.endpoint,
            distinct_id=self.distinct_id,
        )

    def startup(self, version: str = "", **extra):
        """Convenience: track app startup with version and system info."""
        props = {"version": version, **extra}
        self.track("app_started", **props)

    def generation(self, model: str = "", cost_usd: float = 0, **extra):
        """Convenience: track a generation event with model and cost."""
        props = {"model": model, "cost_usd": cost_usd, **extra}
        self.track("generation", **props)

    def error(self, error_type: str = "", message: str = "", **extra):
        """Track an error/failure event."""
        props = {"error_type": error_type, "message": message[:500], **extra}
        self.track("error", **props)

    def feature(self, name: str, **extra):
        """Track feature usage (which features are popular)."""
        props = {"feature": name, **extra}
        self.track("feature_used", **props)

    def performance(self, operation: str, duration_ms: float, **extra):
        """Track operation performance timing."""
        props = {"operation": operation, "duration_ms": duration_ms, **extra}
        self.track("performance", **props)
