"""SQL for the `transactions` table (expenses and income)."""

from datetime import date

from ..models import Transaction

_SELECT_WITH_CATEGORY = """
    SELECT t.*, c.name AS category_name
    FROM transactions t
    LEFT JOIN categories c ON c.id = t.category_id
"""


def month_date_range(month):
    """'2026-09' -> (date(2026, 9, 1), date(2026, 10, 1)) for a range query.

    A range (date >= first AND date < next) lets PostgreSQL use the
    (user_id, date) index, unlike formatting every row's date as text.
    """
    year, mon = int(month[:4]), int(month[5:7])
    first = date(year, mon, 1)
    after = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return first, after


class ExpenseRepository:
    def __init__(self, database):
        self.db = database

    def add(self, transaction):
        """Insert a Transaction and return its new id."""
        with self.db.cursor() as cur:
            cur.execute(
                """INSERT INTO transactions
                       (user_id, date, description, amount, type, category_id, currency)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (transaction.user_id, transaction.date, transaction.description,
                 transaction.amount, transaction.type, transaction.category_id,
                 transaction.currency),
            )
            return cur.fetchone()["id"]

    def list_for_user(self, user_id, month=None, type=None, category_id=None):
        """Transactions of one user, newest first, optionally filtered."""
        sql = _SELECT_WITH_CATEGORY + " WHERE t.user_id = %s"
        params = [user_id]
        if month:
            first, after = month_date_range(month)
            sql += " AND t.date >= %s AND t.date < %s"
            params += [first, after]
        if type:
            sql += " AND t.type = %s"
            params.append(type)
        if category_id is not None:
            sql += " AND t.category_id = %s"
            params.append(category_id)
        sql += " ORDER BY t.date DESC, t.id DESC"
        with self.db.cursor() as cur:
            cur.execute(sql, params)
            return [Transaction.from_row(r) for r in cur.fetchall()]

    def get_for_user(self, transaction_id, user_id):
        """One transaction, only if it belongs to `user_id` (else None)."""
        with self.db.cursor() as cur:
            cur.execute(_SELECT_WITH_CATEGORY + " WHERE t.id = %s AND t.user_id = %s",
                        (transaction_id, user_id))
            row = cur.fetchone()
            return Transaction.from_row(row) if row else None

    def delete(self, transaction_id, user_id):
        """Delete a user's transaction. Returns True if a row was deleted."""
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s",
                        (transaction_id, user_id))
            return cur.rowcount > 0

    def count(self):
        with self.db.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM transactions")
            return cur.fetchone()["n"]
