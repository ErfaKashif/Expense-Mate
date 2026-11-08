"""
Reusable input validators.

Each function either returns the cleaned value or raises ValidationError.
They are pure functions (no database access), so they are trivial to test.
"""

import re
from datetime import datetime

from ..models import Transaction
from .errors import ValidationError

TRANSACTION_TYPES = ("income", "expense")
_MONTH_PATTERN = re.compile(r"\d{4}-\d{2}")


def validate_type(value):
    if value not in TRANSACTION_TYPES:
        raise ValidationError(f"Invalid type '{value}'.")
    return value


def validate_amount(value):
    """A non-negative number, rounded to 2 decimal places."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValidationError("Amount must be a number.") from None
    if amount != amount or amount in (float("inf"), float("-inf")):  # NaN / infinity
        raise ValidationError("Amount must be a number.")
    if amount < 0:
        raise ValidationError("Amount cannot be negative.")
    return round(amount, 2)


def validate_date(value):
    """A calendar date in YYYY-MM-DD format (returned unchanged)."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValidationError("Date must be in YYYY-MM-DD format.") from None
    return value


def validate_month(value):
    """A month in YYYY-MM format."""
    if not isinstance(value, str) or not _MONTH_PATTERN.fullmatch(value):
        raise ValidationError("Month must be in YYYY-MM format.")
    if not 1 <= int(value[5:7]) <= 12:
        raise ValidationError("Month must be in YYYY-MM format.")
    return value


def require_text(value, field_name):
    """A non-empty string (surrounding whitespace removed)."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} is required.")
    return value.strip()


def normalise_category(name, type):
    """One rule for category names, used by BOTH expenses and budgets.

    Blank -> 'Income' / 'Misc'; otherwise trimmed and Title Cased, so a
    budget for "groceries" matches expenses entered as "Groceries".
    (Assignment 01 title-cased expense categories but not budget
    categories, so such budgets never saw any spending.)
    """
    cleaned = name.strip() if isinstance(name, str) else ""
    if not cleaned:
        return "Income" if type == "income" else "Misc"
    return cleaned.title()


class ExpenseValidator:
    """Turns raw user input into a valid, not-yet-saved Transaction.

    REWRITE of the validation that Assignment 01 mixed into
    `Logic.add_transaction` together with database writes, budget updates
    and alert formatting. It is pure: no database, so it can be tested with
    plain values and reused for single entries and CSV rows alike.
    """

    def __init__(self, normalise_currency):
        # normalise_currency(code) -> 'USD' or raises ValidationError
        self.normalise_currency = normalise_currency

    def validate(self, user_id, date, description, amount, type,
                 category=None, currency=None, default_currency="USD"):
        date = validate_date(date)
        type = validate_type(type)
        amount = validate_amount(amount)
        currency = self.normalise_currency(currency or default_currency)
        description = require_text(description, "Description")
        return Transaction(
            user_id=user_id, date=date, description=description, amount=amount,
            type=type, currency=currency, category_name=normalise_category(category, type),
        )
