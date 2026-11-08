"""SQL for the `budgets` table."""

from ..models import Budget

_SELECT_WITH_CATEGORY = """
    SELECT b.*, c.name AS category_name
    FROM budgets b
    JOIN categories c ON c.id = b.category_id
"""


class BudgetRepository:
    def __init__(self, database):
        self.db = database

    def upsert(self, user_id, category_id, month, amount, currency):
        """Create the budget, or replace amount/currency if it already exists.

        The legacy `remaining_amount` column is no longer written: remaining
        budget is calculated by BudgetCalculator. Values migrated from
        Assignment 01 are left untouched.
        """
        with self.db.cursor() as cur:
            cur.execute(
                """INSERT INTO budgets (user_id, category_id, month, amount, currency)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (user_id, category_id, month) DO UPDATE SET
                       amount = EXCLUDED.amount,
                       currency = EXCLUDED.currency
                   RETURNING id""",
                (user_id, category_id, month, amount, currency),
            )
            return cur.fetchone()["id"]

    def list_for_month(self, user_id, month):
        with self.db.cursor() as cur:
            cur.execute(_SELECT_WITH_CATEGORY + " WHERE b.user_id = %s AND b.month = %s"
                        " ORDER BY c.name", (user_id, month))
            return [Budget.from_row(r) for r in cur.fetchall()]

    def delete_by_category(self, user_id, month, category_name):
        """Delete a user's budget for (month, category name). True if deleted."""
        with self.db.cursor() as cur:
            cur.execute(
                """DELETE FROM budgets
                   WHERE user_id = %s AND month = %s
                     AND category_id = (SELECT id FROM categories WHERE name = %s)""",
                (user_id, month, category_name),
            )
            return cur.rowcount > 0
