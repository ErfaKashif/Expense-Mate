"""Unit tests - BudgetService with mocked repositories and services (no database)."""
from unittest.mock import MagicMock

import pytest

from app.backend.models import Budget, User
from app.backend.services.budget_calculator import BudgetCalculator
from app.backend.services.budget_service import BudgetService
from app.backend.services.currency_service import CurrencyService
from app.backend.utils.errors import ValidationError


@pytest.fixture
def deps():
    d = MagicMock()
    d.users.get_user.return_value = User(id=7, username="u", password_hash="h")
    d.users.base_currency.return_value = "USD"
    d.categories.get_or_create.return_value = 3
    d.analytics.category_summary.return_value = {
        "expense": {"Food": 96.0}, "income": {"Salary": 1000.0}, "total_income": 1000.0,
        "total_expense": 96.0, "by_currency": {}, "foreign_count": 0}
    d.analytics.monthly_trend.return_value = [("2026-11", 1000.0, 96.0)]
    d.budgets.list_for_month.return_value = [
        Budget(id=1, user_id=7, category_id=3, category_name="Food", month="2026-11",
               amount=100.0, currency="USD"),
        Budget(id=2, user_id=7, category_id=4, category_name="Rent", month="2026-11",
               amount=90000.0, currency="PKR"),
    ]
    return d


@pytest.fixture
def service(deps):
    return BudgetService(deps.db, deps.budgets, deps.categories, deps.analytics, deps.users,
                         CurrencyService(), BudgetCalculator())


def test_set_budget_normalises_category_and_currency(service, deps):
    service.set_budget(7, "  groceries ", "2026-11", "250", "eur")
    deps.categories.get_or_create.assert_called_once_with("Groceries", "expense")
    deps.budgets.upsert.assert_called_once_with(7, 3, "2026-11", 250.0, "EUR")


def test_set_budget_defaults_to_user_currency(service, deps):
    deps.users.get_user.return_value.base_currency = "PKR"
    service.set_budget(7, "Food", "2026-11", 100)
    assert deps.budgets.upsert.call_args.args[-1] == "PKR"


@pytest.mark.parametrize("category, month, amount", [
    ("Food", "sep-2026", 100), ("Food", "2026-13", 100), ("Food", "2026-11", -1),
    ("", "2026-11", 100), (None, "2026-11", 100), ("Food", "2026-11", "abc"),
])
def test_set_budget_rejects_invalid_input(service, deps, category, month, amount):
    with pytest.raises(ValidationError):
        service.set_budget(7, category, month, amount)
    deps.budgets.upsert.assert_not_called()


def test_budget_status_converts_and_calculates(service):
    st = service.budget_status(7, "2026-11")
    food, rent = st["status"]
    assert (food["limit"], food["spent"], food["remaining"], food["level"]) == (100.0, 96.0, 4.0, "critical")
    assert rent["limit"] == pytest.approx(324.0) and rent["converted"] is True
    assert rent["spent"] == 0.0 and rent["level"] == "ok"
    assert [a["category"] for a in st["alerts"]] == ["Food"]


def test_alert_for_category(service):
    alert = service.alert_for_category(7, "2026-11", "Food")
    assert alert["level"] == "critical" and "96%" in alert["message"]
    assert service.alert_for_category(7, "2026-11", "Rent") is None
    assert service.alert_for_category(7, "2026-11", "Travel") is None   # no budget


def test_monthly_summary_combines_totals_budgets_and_trend(service):
    s = service.monthly_summary(7, "2026-11")
    assert (s["total_income"], s["total_expense"], s["balance"]) == (1000.0, 96.0, 904.0)
    assert s["by_category"] == {"Food": 96.0}
    assert s["trend"] == [("2026-11", 1000.0, 96.0)]
    assert len(s["budget"]["status"]) == 2 and s["base_symbol"] == "$"


def test_delete_budget_delegates_to_repository(service, deps):
    deps.budgets.delete_by_category.return_value = True
    assert service.delete_budget(7, "2026-11", "Food") is True
    deps.budgets.delete_by_category.assert_called_once_with(7, "2026-11", "Food")
