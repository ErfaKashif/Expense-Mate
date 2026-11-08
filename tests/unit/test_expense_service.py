"""Unit tests - ExpenseService with mocked repositories and services (no database)."""
from unittest.mock import MagicMock

import pytest

from app.backend.models import Transaction, User
from app.backend.services.csv_importer import CsvImporter
from app.backend.services.currency_service import CurrencyService
from app.backend.services.expense_service import ExpenseService
from app.backend.utils.errors import NotFoundError, ValidationError
from app.backend.utils.validators import ExpenseValidator


@pytest.fixture
def deps():
    d = MagicMock()
    d.users.get_user.return_value = User(id=7, username="u", password_hash="h", base_currency="USD")
    d.users.base_currency.return_value = "USD"
    d.categories.get_or_create.side_effect = lambda name, kind: {"Food": 1, "Transport": 2}.get(name, 9)
    d.expenses.add.return_value = 101
    d.budgets.alert_for_category.return_value = None
    return d


@pytest.fixture
def service(deps):
    currency = CurrencyService()
    return ExpenseService(deps.db, deps.expenses, deps.categories, deps.users, currency,
                          deps.budgets, ExpenseValidator(currency.normalise), CsvImporter())


def test_add_expense_saves_validated_transaction(service, deps):
    new_id, alert = service.add_expense(7, "2026-09-01", " lunch ", "60", "expense", "food", "usd")
    assert (new_id, alert) == (101, None)
    saved = deps.expenses.add.call_args.args[0]
    assert (saved.description, saved.amount, saved.currency, saved.category_id) == ("lunch", 60.0, "USD", 1)
    deps.categories.get_or_create.assert_called_once_with("Food", "expense")
    deps.db.transaction.assert_called_once()


def test_add_expense_returns_budget_alert(service, deps):
    deps.budgets.alert_for_category.return_value = {"level": "critical", "message": "m", "category": "Food"}
    _, alert = service.add_expense(7, "2026-11-03", "x", 96, "expense", "Food")
    assert alert["level"] == "critical"
    deps.budgets.alert_for_category.assert_called_once_with(7, "2026-11", "Food")


def test_income_does_not_check_budgets(service, deps):
    service.add_expense(7, "2026-09-01", "salary", 1000, "income")
    deps.budgets.alert_for_category.assert_not_called()
    assert deps.expenses.add.call_args.args[0].category_name == "Income"


def test_default_currency_is_users_base_currency(service, deps):
    deps.users.get_user.return_value.base_currency = "PKR"
    service.add_expense(7, "2026-09-01", "chai", 500, "expense")
    assert deps.expenses.add.call_args.args[0].currency == "PKR"


def test_invalid_expense_never_reaches_repository(service, deps):
    with pytest.raises(ValidationError):
        service.add_expense(7, "2026-09-01", "x", -5, "expense")
    deps.expenses.add.assert_not_called()
    deps.db.transaction.assert_not_called()


def test_unknown_user_propagates_not_found(service, deps):
    deps.users.get_user.side_effect = NotFoundError("User not found.")
    with pytest.raises(NotFoundError):
        service.add_expense(99, "2026-09-01", "x", 5, "expense")


def test_delete_missing_or_foreign_transaction_raises(service, deps):
    deps.expenses.delete.return_value = False
    with pytest.raises(NotFoundError):
        service.delete_expense(7, 555)
    deps.expenses.delete.assert_called_once_with(555, 7)


def test_delete_own_transaction(service, deps):
    deps.expenses.delete.return_value = True
    assert service.delete_expense(7, 5) is True


def test_list_expenses_adds_base_currency_fields(service, deps):
    deps.expenses.list_for_user.return_value = [Transaction(
        id=1, user_id=7, date="2026-09-01", description="chai", amount=500, type="expense",
        currency="PKR", category_name="Food")]
    row = service.list_expenses(7, month="2026-09")[0]
    assert row["amount_base"] == pytest.approx(1.8) and row["is_foreign"] is True
    assert row["currency_symbol"] == "Rs" and row["base_symbol"] == "$"
    deps.expenses.list_for_user.assert_called_once_with(7, month="2026-09", type=None)


def test_import_saves_valid_rows_in_one_transaction(service, deps):
    csv_text = ("date,description,amount,type,category,currency\n"
                "2026-09-01,rice,25,expense,Food,USD\n"
                "2026-09-02,bread,5,expense,food,USD\n"
                "bad-date,x,1,expense,Food,USD\n"
                "2026-09-03,taxi,15,expense,Transport,XYZ\n"
                "2026-09-04,bus,2,expense,Transport,PKR\n")
    assert service.import_csv(7, csv_text) == (3, 2)
    assert deps.expenses.add.call_count == 3
    deps.db.transaction.assert_called_once()                 # all rows, one transaction
    assert deps.categories.get_or_create.call_count == 2     # cached per category


def test_import_wrong_headers(service):
    with pytest.raises(ValidationError):
        service.import_csv(7, "foo,bar\n1,2\n")


def test_export_csv_has_converted_column(service, deps):
    deps.expenses.list_for_user.return_value = [Transaction(
        id=1, user_id=7, date="2026-09-01", description="a", amount=5000, type="expense",
        currency="PKR", category_name="Food")]
    lines = service.export_csv(7, "2026-09").splitlines()
    assert lines[0].endswith("amount_in_USD")
    assert lines[1] == "2026-09-01,a,5000,expense,Food,PKR,18.0"
