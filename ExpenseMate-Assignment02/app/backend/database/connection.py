"""
PostgreSQL connection and transaction management (DATABASE layer).

Only this module knows how to open a connection. Repositories ask it for a
cursor; services can group several repository calls into ONE database
transaction with `with database.transaction(): ...`.

How the transaction sharing works
---------------------------------
The connection that belongs to the currently running transaction is stored
in a thread-local variable. Flask serves each request on its own thread, so
two requests never share a connection.

    with db.transaction():           # opens connection, BEGIN
        repo_a.insert(...)           # db.cursor() re-uses that connection
        repo_b.update(...)           # same connection, same transaction
                                     # COMMIT on success, ROLLBACK on error

A repository call made outside any `transaction()` block simply runs in its
own short transaction (opened and committed automatically).
"""

import threading
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from ..utils.logger import get_logger

log = get_logger(__name__)


class DatabaseUnavailableError(Exception):
    """Raised when PostgreSQL cannot be reached (server down, bad credentials...)."""


class Database:
    """Creates PostgreSQL connections and manages transactions."""

    def __init__(self, url, connect_timeout=5):
        self.url = url
        self.connect_timeout = connect_timeout
        self._local = threading.local()

    # ------------------------------------------------------------------ #
    # Connections
    # ------------------------------------------------------------------ #
    def _open_connection(self):
        try:
            # dict_row => every fetched row is a plain dict {column: value}
            return psycopg.connect(self.url, row_factory=dict_row,
                                   connect_timeout=self.connect_timeout)
        except psycopg.OperationalError as exc:
            log.error("Could not connect to PostgreSQL: %s", exc)
            raise DatabaseUnavailableError("The database is currently unavailable.") from exc

    def _active_connection(self):
        return getattr(self._local, "connection", None)

    # ------------------------------------------------------------------ #
    # Transactions
    # ------------------------------------------------------------------ #
    @contextmanager
    def transaction(self):
        """Run the enclosed block in a single transaction.

        Nested calls join the outer transaction, so a service method that
        uses `transaction()` can safely be called from another one.
        """
        active = self._active_connection()
        if active is not None:          # already inside a transaction
            yield active
            return

        connection = self._open_connection()
        self._local.connection = connection
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self._local.connection = None
            connection.close()

    @contextmanager
    def cursor(self):
        """Yield a cursor that takes part in the current transaction."""
        with self.transaction() as connection:
            with connection.cursor() as cur:
                yield cur

    # ------------------------------------------------------------------ #
    # Health check
    # ------------------------------------------------------------------ #
    def ping(self):
        """Return True if PostgreSQL answers a trivial query."""
        with self.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            return cur.fetchone()["ok"] == 1
