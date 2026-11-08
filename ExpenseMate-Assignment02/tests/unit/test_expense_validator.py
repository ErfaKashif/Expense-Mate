"""Unit tests - ExpenseValidator and validator functions (rewritten expense module). No database."""
import pytest

from app.backend.services.currency_service import CurrencyService
from app.backend.utils.errors import ValidationError
from app.backend.utils.validators import (
    ExpenseValidator, normalise_category, require_text, validate_amount, validate_date,
    validate_month, validate_type,
)


@pytest.fixture
def validator():
    return ExpenseValidator(CurrencyService().normalise)


def valid_input(**overrides):
    data = dict(user_id=1, date="2026-09-01", description="  lunch ", amount="12.345",
                type="expense", category="food", currency="pkr")
    data.update(overrides)
    return data


def test_returns_clean_unsaved_transaction(validator):
    tx = validator.validate(**valid_input())
    assert (tx.user_id, tx.date, tx.description, tx.amount) == (1, "2026-09-01", "lunch", 12.35)
    assert (tx.type, tx.currency, tx.category_name) == ("expense", "PKR", "Food")
    assert tx.id is None and tx.category_id is None


def test_default_currency_used_when_missing(validator):
    assert validator.validate(**valid_input(currency=None), default_currency="EUR").currency == "EUR"


@pytest.mark.parametrize("field, value, message", [
    ("date", "09-01-2026", "YYYY-MM-DD"),
    ("date", None, "YYYY-MM-DD"),
    ("type", "transfer", "Invalid type"),
    ("amount", "abc", "must be a number"),
    ("amount", -5, "cannot be negative"),
    ("amount", "nan", "must be a number"),
    ("currency", "XYZ", "Unsupported currency"),
    ("description", "   ", "Description is required"),
    ("description", None, "Description is required"),
])
def test_invalid_input_rejected(validator, field, value, message):
    with pytest.raises(ValidationError, match=message):
        validator.validate(**valid_input(**{field: value}))


def test_validator_does_not_touch_a_database():
    # The validator receives only a currency function: nothing else to call.
    calls = []
    v = ExpenseValidator(lambda code: calls.append(code) or "USD")
    v.validate(**valid_input())
    assert calls == ["pkr"]


@pytest.mark.parametrize("name, type, expected", [
    ("groceries", "expense", "Groceries"), ("  rent  ", "expense", "Rent"),
    ("", "expense", "Misc"), (None, "income", "Income"), ("salary", "income", "Salary"),
])
def test_normalise_category(name, type, expected):
    assert normalise_category(name, type) == expected


def test_small_validators():
    assert validate_amount("10") == 10.0 and validate_amount(0) == 0.0
    assert validate_date("2026-02-28") == "2026-02-28"
    assert validate_type("income") == "income"
    assert validate_month("2026-12") == "2026-12"
    assert require_text(" a ", "X") == "a"
    for bad in ("2026-13", "2026-00", "sep-2026", None, "2026-9"):
        with pytest.raises(ValidationError):
            validate_month(bad)
    with pytest.raises(ValidationError):
        validate_date("2026-02-30")
