"""
Schema migrations for PostgreSQL.

Each file in `database/migrations/` named `NNN_description.sql` is one
schema version. `apply_migrations()` runs the files that have not been
applied yet, in order, and records them in the `schema_migrations` table.
Running it twice is safe (it is idempotent).
"""

import os

from ..utils.logger import get_logger

log = get_logger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

# Tables in foreign-key order (parents before children). Used by the
# migration script and by the test-suite to clear data.
TABLES = ["users", "categories", "transactions", "budgets", "settings"]


def migration_files():
    """Sorted list of (version, path) for every *.sql migration file."""
    files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    return [(name.split("_", 1)[0], os.path.join(MIGRATIONS_DIR, name)) for name in files]


def apply_migrations(database):
    """Bring the database schema up to date. Returns the versions applied."""
    applied_now = []
    with database.transaction():
        with database.cursor() as cur:
            cur.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                       version    TEXT PRIMARY KEY,
                       applied_at TIMESTAMP NOT NULL DEFAULT now()
                   )"""
            )
            # Serialise concurrent app start-ups (e.g. several workers).
            cur.execute("SELECT pg_advisory_xact_lock(4242001)")
            cur.execute("SELECT version FROM schema_migrations")
            already_applied = {row["version"] for row in cur.fetchall()}

            for version, path in migration_files():
                if version in already_applied:
                    continue
                with open(path, encoding="utf-8") as sql_file:
                    cur.execute(sql_file.read())
                cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
                applied_now.append(version)
                log.info("Applied schema migration %s", os.path.basename(path))
    return applied_now
