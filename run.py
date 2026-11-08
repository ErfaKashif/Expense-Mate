"""
Start ExpenseMate locally:   python run.py

Requires PostgreSQL and a DATABASE_URL (put it in a .env file; see .env.example).
Set FLASK_DEBUG=1 for auto-reload and the debugger during development.
"""

import os
import sys

# Make sure the project folder is first on the import path.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root in sys.path:
    sys.path.remove(project_root)
sys.path.insert(0, project_root)

from app.backend.database import ConfigurationError, DatabaseUnavailableError  # noqa: E402
from app.backend.server import create_app  # noqa: E402

if __name__ == "__main__":
    try:
        app = create_app()
    except (ConfigurationError, DatabaseUnavailableError) as exc:
        sys.exit(f"ExpenseMate could not start: {exc}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
