import os

from app.backend.server import create_app

app = create_app()

def _debug_enabled():
    """Debug mode is on by default for local development; set DEBUG=0 to disable it."""
    return os.environ.get("DEBUG", "1") not in ("0", "false", "False")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=_debug_enabled())
