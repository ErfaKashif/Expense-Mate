"""
ExpenseService: record, list and delete income/expense entries; CSV import/export.

REWRITE of the Assignment 01 expense-management module (`Logic.add_transaction`,
`Logic.delete_transaction`, `Logic.import_csv`, `Logic._validate_*`).

Responsibilities are now separated:
    ExpenseValidator  - is the input valid? (pure)
    CsvImporter       - turn CSV text into rows (pure)
    ExpenseService    - coordinate: validate -> save in a transaction -> ask
                        BudgetService for an alert
    ExpenseRepository - SQL
Budget arithmetic no longer lives here at all (see BudgetCalculator).
"""

import csv
import io

from ..utils.errors import NotFoundError, ValidationError


class ExpenseService:
    def __init__(self, database, expense_repository, category_repository, user_service,
                 currency_service, budget_service, validator, csv_importer):
        self.db = database
        self.expenses = expense_repository
        self.categories = category_repository
        self.users = user_service
        self.currency = currency_service
        self.budgets = budget_service
        self.validator = validator
        self.csv_importer = csv_importer

    # ------------------------------------------------------------------ #
    # Feature 1: Add Expense
    # ------------------------------------------------------------------ #
    def add_expense(self, user_id, date, description, amount, type,
                    category=None, currency=None):
        """Validate and store one record. Returns (new_id, alert dict or None)."""
        user = self.users.get_user(user_id)
        transaction = self.validator.validate(
            user_id, date, description, amount, type, category, currency,
            default_currency=user.base_currency)

        with self.db.transaction():
            new_id = self._save(transaction)

        alert = None
        if transaction.type == "expense":
            alert = self.budgets.alert_for_category(user_id, transaction.month,
                                                    transaction.category_name)
        return new_id, alert

    def _save(self, transaction, category_ids=None):
        """Attach the category id (creating the category if new) and insert."""
        cache = {} if category_ids is None else category_ids
        key = transaction.category_name
        if key not in cache:
            cache[key] = self.categories.get_or_create(key, transaction.type)
        transaction.category_id = cache[key]
        transaction.id = self.expenses.add(transaction)
        return transaction.id

    # ------------------------------------------------------------------ #
    def delete_expense(self, user_id, transaction_id):
        """Delete one of the user's own records (NotFoundError otherwise).

        No budget bookkeeping is needed: remaining budgets are calculated
        from the transactions, so they are correct as soon as the row is gone.
        """
        if not self.expenses.delete(transaction_id, user_id):
            raise NotFoundError("Transaction not found.")
        return True

    def list_expenses(self, user_id, month=None, type=None):
        """Transaction dicts annotated with the amount in the user's base currency."""
        base = self.users.base_currency(user_id)
        base_symbol = self.currency.symbol(base)
        rows = []
        for tx in self.expenses.list_for_user(user_id, month=month, type=type):
            row = tx.to_dict()
            row.update(
                base_currency=base,
                base_symbol=base_symbol,
                currency_symbol=self.currency.symbol(tx.currency),
                amount_base=round(self.currency.convert(tx.amount, tx.currency, base), 2),
                is_foreign=tx.currency != base,
            )
            rows.append(row)
        return rows

    def list_categories(self):
        return [c.to_dict() for c in self.categories.list_all()]

    # ------------------------------------------------------------------ #
    # CSV
    # ------------------------------------------------------------------ #
    def import_csv(self, user_id, raw_text):
        """Import CSV text. Returns (imported, skipped).

        Invalid rows are skipped (same as Assignment 01). All valid rows are
        saved in ONE transaction: either the whole import is stored or, if
        the database fails, nothing is.
        """
        user = self.users.get_user(user_id)
        parsed = self.csv_importer.parse(raw_text)

        valid, skipped = [], parsed.blank_rows
        for row in parsed.rows:
            try:
                valid.append(self.validator.validate(
                    user_id, row["date"], row["description"], row["amount"], row["type"],
                    row["category"], row["currency"], default_currency=user.base_currency))
            except ValidationError:
                skipped += 1

        category_ids = {}
        with self.db.transaction():
            for transaction in valid:
                self._save(transaction, category_ids)
        return len(valid), skipped

    def export_csv(self, user_id, month=None):
        """CSV of native amounts plus the amount converted to the base currency."""
        base = self.users.base_currency(user_id)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["date", "description", "amount", "type", "category",
                         "currency", f"amount_in_{base}"])
        for tx in self.expenses.list_for_user(user_id, month=month):
            writer.writerow([tx.date, tx.description, tx.amount, tx.type,
                             tx.category_name or "", tx.currency,
                             round(self.currency.convert(tx.amount, tx.currency, base), 2)])
        return buffer.getvalue()
