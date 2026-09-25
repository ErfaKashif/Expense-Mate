"""
ExpenseMate — entry point for LOCAL development and PaaS hosts (Render/Railway).

Run locally:      python run.py            -> http://localhost:5000
Run on a host:    the platform injects $PORT (e.g. Render uses 10000) and we honour it.

NOTE ON DEBUG: the Werkzeug debugger allows arbitrary code execution, so it is ON
only for local development and OFF whenever we detect a deployed environment.
Set DEBUG=1 explicitly if you really want it on elsewhere.

For Vercel, do NOT use this file — Vercel uses api/index.py (see docs/Deployment_Vercel.md).
"""
import os

from app.backend.server import create_app

app = create_app()


def _is_deployed():
    """True when running on a hosting platform rather than a developer machine."""
    return any(os.environ.get(k) for k in
               ("VERCEL", "RENDER", "RAILWAY_ENVIRONMENT", "PYTHONANYWHERE_SITE"))


def _debug_enabled():
    if os.environ.get("DEBUG"):
        return os.environ["DEBUG"] not in ("0", "false", "False")
    return not _is_deployed()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=_debug_enabled())
