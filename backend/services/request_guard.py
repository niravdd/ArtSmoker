"""Refuse browser requests that another website makes to this server.

ArtSmoker has no login, and a browser can reach it at localhost even when it
runs only on the user's own machine. Without this guard, any page the user
visits could call the API through their browser: read assets and chats, start
paid generations, or deploy and tear down models. Three checks, in one ASGI
middleware ahead of everything else:

1. Host. The Host header must be localhost, an IP address, this machine's host
   name, or a name listed in ``settings.allowed_hosts``. This stops DNS
   rebinding, where an attacker's domain is made to resolve to 127.0.0.1 so the
   browser treats their page as same-origin. Rebinding needs a domain name, so
   IP addresses are safe to allow (e.g. http://<EC2 IP>:8000).
2. Origin. A state-changing request (POST/PUT/PATCH/DELETE) that carries an
   Origin header must come from this server's own origin or from one listed in
   ``settings.cors_origins``. Browsers send Origin on these requests, so a
   cross-site form post or a body-less fetch is refused, even the "simple"
   requests that skip a CORS preflight.
3. Fetch metadata. A request the browser labels ``Sec-Fetch-Site: cross-site``
   is refused unless it is a top-level navigation (following a link to the app)
   or comes from an allowed origin.

Clients that send none of these browser headers (curl, scripts, the sanity
harness, a reverse proxy's health check) pass checks 2 and 3 unchanged.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import socket
from urllib.parse import urlsplit

from backend.config import settings

logger = logging.getLogger(__name__)

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_warned: set = set()  # (reason, value) pairs already logged — one line each


def _split_list(value: str) -> list:
    return [v.strip().lower() for v in (value or "").split(",") if v.strip()]


def _own_host_names() -> set:
    names = {"localhost"}
    try:
        h = socket.gethostname().lower()
        if h:
            names |= {h, h.split(".")[0], f"{h.split('.')[0]}.local"}
    except OSError:
        pass
    return names


_OWN_NAMES = _own_host_names()


def _host_name(host_header: str) -> str:
    """'Example.com:8000' → 'example.com'; '[::1]:8000' → '::1'."""
    h = (host_header or "").strip().lower()
    if h.startswith("["):
        return h[1:].split("]", 1)[0]
    if h.count(":") == 1:
        return h.rsplit(":", 1)[0]
    return h


def host_allowed(host_header: str, allowed: list | None = None) -> bool:
    allowed = _split_list(settings.allowed_hosts) if allowed is None else allowed
    if "*" in allowed:
        return True
    name = _host_name(host_header).rstrip(".")
    if not name:
        return True  # no Host header (HTTP/1.0 tools) — not a browser request
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        pass
    if name in _OWN_NAMES or name.endswith(".localhost"):
        return True
    return any(name == a or (a.startswith(".") and (name.endswith(a) or name == a[1:]))
               for a in allowed)


def origin_allowed(origin: str, host_header: str, cors: list | None = None) -> bool:
    """Same origin as the request (scheme-agnostic host:port match), or listed."""
    cors = _split_list(settings.cors_origins) if cors is None else cors
    o = (origin or "").strip().lower()
    if not o or o == "null":
        return False
    if o.rstrip("/") in [c.rstrip("/") for c in cors]:
        return True
    return urlsplit(o).netloc == (host_header or "").strip().lower()


def _refusal(scope, headers: dict):
    """The reason to refuse this request, or None to let it through."""
    host = headers.get("host", "")
    if not host_allowed(host):
        return ("host", host,
                f"This server doesn't answer to the host name '{_host_name(host)}'. "
                "If you serve ArtSmoker under that name, add it to ARTSMOKER_ALLOWED_HOSTS.")
    origin = headers.get("origin")
    if origin is not None:
        if scope.get("method", "GET").upper() in _UNSAFE_METHODS and not origin_allowed(origin, host):
            return ("origin", origin, "Cross-site request refused: it came from another website.")
        if origin_allowed(origin, host):
            return None  # same origin, or an origin listed in ARTSMOKER_CORS_ORIGINS
    if headers.get("sec-fetch-site") == "cross-site" and headers.get("sec-fetch-mode") != "navigate":
        return ("fetch-site", origin or headers.get("referer", "?"),
                "Cross-site request refused: it came from another website.")
    return None


class RequestGuard:
    """Pure ASGI middleware (runs before routing, static files included)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        refused = _refusal(scope, headers)
        if refused is None:
            return await self.app(scope, receive, send)
        reason, value, message = refused
        if (reason, value) not in _warned:
            _warned.add((reason, value))
            logger.warning("Refused %s %s — %s check (%s)", scope.get("method"), scope.get("path"), reason, value)
        status = 400 if reason == "host" else 403
        body = json.dumps({"detail": message}).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
