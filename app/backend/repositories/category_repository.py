"""SQL for the `categories` table."""

from ..models import Category


class CategoryRepository:
    def __init__(self, database):
        self.db = database

    def get_or_create(self, name, kind):
        """Return the id of category `name`, inserting it first if needed.

        ON CONFLICT makes this safe when two requests create the same
        category at the same moment (SQLite version could race).
        """
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO categories (name, kind) VALUES (%s, %s) "
                "ON CONFLICT (name) DO NOTHING RETURNING id",
                (name, kind),
            )
            row = cur.fetchone()
            if row:
                return row["id"]
            cur.execute("SELECT id FROM categories WHERE name = %s", (name,))
            return cur.fetchone()["id"]

    def list_all(self, kind=None):
        with self.db.cursor() as cur:
            if kind:
                cur.execute("SELECT * FROM categories WHERE kind = %s ORDER BY name", (kind,))
            else:
                cur.execute("SELECT * FROM categories ORDER BY name")
            return [Category.from_row(r) for r in cur.fetchall()]
