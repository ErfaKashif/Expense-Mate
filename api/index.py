"""Serverless entry point (e.g. Vercel). Reads DATABASE_URL from the environment."""

import os

from app.backend.server import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
