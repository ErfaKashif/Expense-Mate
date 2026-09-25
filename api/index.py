"""
Vercel serverless entrypoint for ExpenseMate.

Vercel's Python runtime looks for a WSGI `app` object in this file.
Everything (UI + REST API + static assets) is served by the same Flask app,
so vercel.json rewrites all routes here.

DATABASE NOTE (important on serverless):
    Vercel's filesystem is READ-ONLY except /tmp, and /tmp is EPHEMERAL —
    it is wiped between cold starts / deployments. So the SQLite file works
    for demos and grading, but data will not persist long-term.
    For real persistence use an external DB (see docs/Deployment_Vercel.md).
"""

import os

from app.backend.server import create_app

# Use an explicit env var if given, else /tmp on Vercel, else the local default.
if os.environ.get("EXPENSEMATE_DB"):
    DB_PATH = os.environ["EXPENSEMATE_DB"]
elif os.environ.get("VERCEL"):
    os.makedirs("/tmp/data", exist_ok=True)
    DB_PATH = "/tmp/data/expensemate.db"
else:
    DB_PATH = None          # -> app/data/expensemate.db (local development)

app = create_app(db_path=DB_PATH)

# Vercel can also call this directly; keeping it explicit is harmless.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
