"""ArtSmoker entry point — stable import target + cross-platform supervisor.

Two roles, selected by how this module is used:

  • Imported (``uvicorn backend.main:app`` / ``gunicorn backend.main:app``, or
    the child's ``from backend.main import _server_state``): it lazily
    re-exports the ASGI ``app`` and shared ``_server_state`` from
    :mod:`backend.app`. Every existing launch command keeps working verbatim.

  • Run directly (``python -m backend.main``): it starts the supervisor that
    runs the app in a child process and can restart that child in place for
    auto-updates — reliably and on every OS, including Windows. (The supervisor
    itself is added in a later step; this module currently provides only the
    lazy re-export shim.)

The re-export is LAZY on purpose: the supervisor process must not import the
whole FastAPI app (routers, AWS clients, logging banners) just to spawn a
child. Only genuine attribute access — by uvicorn/gunicorn resolving
``backend.main:app``, or the child's lazy ``from backend.main import
_server_state`` — loads :mod:`backend.app`.
"""


def __getattr__(name):
    # PEP 562 module-level attribute hook. `app` and `_server_state` are the only
    # names other code reaches through backend.main; both live in backend.app.
    # `_server_state` is a dict mutated in place (never reassigned), so this
    # re-export and backend.app share the one object — state stays consistent.
    if name in ("app", "_server_state"):
        from backend import app as _app_module
        return getattr(_app_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
