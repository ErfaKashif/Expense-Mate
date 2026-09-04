"""
ExpenseMate -- Database Layer (Layer 3: Persistence)

Responsibility:
    * Owns the SQLite database file and the connection lifecycle.
    * Defines the schema (users, categories, transactions, budgets, settings).
    * Exposes small, focused repository methods so the logic layer never
      touches raw SQL.

Design note (layered architecture):
    UI (frontend)  ->  server (REST API)  ->  logic  ->  db  ->  SQLite file
"""

import os
import sqlite3
from contextlib import contextmanager

# Allow tests / deployments to redirect the database file via environment.
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "data", "expensemate.db")


class Database:
    """Thin repository over a SQLite database for ExpenseMate."""

    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("EXPENSEMATE_DB", DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.init_schema()

    # ------------------------------------------------------------------ #
    # Connection management
    # ------------------------------------------------------------------ #
    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #
    def init_schema(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    username   TEXT NOT NULL UNIQUE,
                    password   TEXT NOT NULL,
                    base_currency TEXT NOT NULL DEFAULT 'USD',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL CHECK (kind IN ('income', 'expense'))
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    date        TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount      REAL NOT NULL CHECK (amount >= 0),
                    type        TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                    category_id INTEGER REFERENCES categories(id),
                    currency    TEXT NOT NULL DEFAULT 'USD',
                    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS budgets (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    category_id INTEGER NOT NULL REFERENCES categories(id),
                    month       TEXT NOT NULL,          -- 'YYYY-MM'
                    amount      REAL NOT NULL CHECK (amount >= 0),
                    currency    TEXT NOT NULL DEFAULT 'USD',
                    UNIQUE (user_id, category_id, month)
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );
                """
            )

    # ------------------------------------------------------------------ #
    # Users
    # ------------------------------------------------------------------ #
    def create_user(self, username, password, base_currency="USD"):
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password, base_currency) VALUES (?, ?, ?)",
                (username, password, base_currency),
            )
            return cur.lastrowid

    def get_user(self, user_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_user_by_name(self, username):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return dict(row) if row else None

    def update_user(self, user_id, base_currency=None):
        with self.connect() as conn:
            if base_currency is not None:
                conn.execute("UPDATE users SET base_currency = ? WHERE id = ?",
                             (base_currency, user_id))

    # ------------------------------------------------------------------ #
    # Categories
    # ------------------------------------------------------------------ #
    def ensure_category(self, name, kind):
        """Insert a category if it does not already exist; return its id."""
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
            if row:
                return row["id"]
            cur = conn.execute("INSERT INTO categories (name, kind) VALUES (?, ?)", (name, kind))
            return cur.lastrowid

    def list_categories(self, kind=None):
        with self.connect() as conn:
            if kind:
                rows = conn.execute("SELECT * FROM categories WHERE kind = ? ORDER BY name",
                                    (kind,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Transactions
    # ------------------------------------------------------------------ #
    def add_transaction(self, user_id, date, description, amount, type,
                        category_id=None, currency="USD"):
        with self.connect() as conn:
            cur = conn.execute(
                """INSERT INTO transactions
                   (user_id, date, description, amount, type, category_id, currency)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, date, description, amount, type, category_id, currency),
            )
            return cur.lastrowid

    def list_transactions(self, user_id, month=None, type=None):
        with self.connect() as conn:
            sql = """SELECT t.*, c.name AS category_name
                     FROM transactions t
                     LEFT JOIN categories c ON c.id = t.category_id
                     WHERE t.user_id = ?"""
            params = [user_id]
            if month:
                sql += " AND strftime('%Y-%m', t.date) = ?"
                params.append(month)
            if type:
                sql += " AND t.type = ?"
                params.append(type)
            sql += " ORDER BY t.date DESC, t.id DESC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_transaction(self, tx_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
            return dict(row) if row else None

    def delete_transaction(self, tx_id):
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
            return cur.rowcount > 0

    def counts(self):
        with self.connect() as conn:
            n = conn.execute("SELECT COUNT(*) AS c FROM transactions").fetchone()["c"]
            return n

    # ------------------------------------------------------------------ #
    # Budgets
    # ------------------------------------------------------------------ #
    def set_budget(self, user_id, category_id, month, amount, currency="USD"):
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO budgets (user_id, category_id, month, amount, currency)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, category_id, month)
                   DO UPDATE SET amount = excluded.amount, currency = excluded.currency""",
                (user_id, category_id, month, amount, currency),
            )

    def get_budgets(self, user_id, month=None):
        with self.connect() as conn:
            sql = """SELECT b.*, c.name AS category_name
                     FROM budgets b JOIN categories c ON c.id = b.category_id
                     WHERE b.user_id = ?"""
            params = [user_id]
            if month:
                sql += " AND b.month = ?"
                params.append(month)
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
