"""SQL for the `users` table."""

from ..models import User


class UserRepository:
    def __init__(self, database):
        self.db = database

    def create(self, username, password_hash, base_currency):
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password, base_currency) "
                "VALUES (%s, %s, %s) RETURNING id",
                (username, password_hash, base_currency),
            )
            return cur.fetchone()["id"]

    def get_by_id(self, user_id):
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return User.from_row(row) if row else None

    def get_by_username(self, username):
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            return User.from_row(row) if row else None

    def update_base_currency(self, user_id, base_currency):
        with self.db.cursor() as cur:
            cur.execute("UPDATE users SET base_currency = %s WHERE id = %s",
                        (base_currency, user_id))
            return cur.rowcount > 0
