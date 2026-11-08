"""Unit tests - BudgetCalculator (rewritten budget-calculation module). No database."""
import pytest

from app.backend.services.budget_calculator import (
    CRITICAL, OK, WARNING, BudgetCalculator, BudgetThresholds,
)


@pytest.fixture
def calc():
    return BudgetCalculator()


# ---- thresholds / levels (same 80 % / 95 % as Assignment 01) ----
@pytest.mark.parametrize("ratio, level", [
    (0.0, OK), (0.7999, OK), (0.80, WARNING), (0.9499, WARNING), (0.95, CRITICAL), (1.5, CRITICAL),
])
def test_level_boundaries(calc, ratio, level):
    assert calc.level_for(ratio) == level


def test_custom_thresholds_are_respected():
    calc = BudgetCalculator(BudgetThresholds(warning=0.5, critical=0.9))
    assert calc.level_for(0.5) == WARNING and calc.level_for(0.9) == CRITICAL


def test_invalid_thresholds_rejected():
    with pytest.raises(ValueError):
        BudgetThresholds(warning=0.9, critical=0.5)


# ---- ratio ----
def test_usage_ratio_rounds_to_four_places(calc):
    assert calc.usage_ratio(1, 3) == 0.3333


def test_zero_budget_with_spending_is_fully_used(calc):
    assert calc.usage_ratio(5, 0) == 1.0
    assert calc.usage_ratio(0, 0) == 0.0


# ---- evaluate ----
def test_evaluate_computes_remaining_from_spending(calc):
    s = calc.evaluate("Food", limit=100, spent=80, currency="USD", symbol="$")
    assert (s.limit, s.spent, s.remaining, s.ratio, s.level) == (100, 80, 20, 0.8, WARNING)
    assert s.converted is False and s.budget_currency == "USD"


def test_evaluate_over_budget_gives_negative_remaining(calc):
    s = calc.evaluate("Food", 100, 120, "USD", "$")
    assert s.remaining == -20 and s.level == CRITICAL


def test_evaluate_marks_converted_budgets(calc):
    s = calc.evaluate("Rent", 324.0, 300, "USD", "$", budget_currency="pkr",
                      budget_amount_native=90000)
    assert s.converted is True and s.budget_currency == "PKR"
    assert s.budget_amount_native == 90000


def test_evaluate_rounds_money_to_cents(calc):
    s = calc.evaluate("Food", 100.004, 33.335, "USD", "$")
    assert s.limit == 100.0 and s.spent == pytest.approx(33.34, abs=0.006)


def test_status_dict_has_assignment01_keys(calc):
    keys = set(calc.evaluate("Food", 1, 1, "USD", "$").to_dict())
    assert keys == {"category", "limit", "spent", "remaining", "ratio", "level", "currency",
                    "symbol", "budget_currency", "budget_amount_native", "converted"}


# ---- alerts (message text identical to Assignment 01) ----
def test_no_alert_when_ok(calc):
    assert calc.alert_for(calc.evaluate("Food", 100, 10, "USD", "$")) is None


def test_warning_message(calc):
    alert = calc.alert_for(calc.evaluate("Food", 100, 85, "USD", "$"))
    assert alert.level == WARNING
    assert alert.message == "Budget for 'Food' is at 85% ($85 of $100)."


def test_critical_message(calc):
    alert = calc.alert_for(calc.evaluate("Food", 100.0, 96.0, "USD", "$"))
    assert alert.level == CRITICAL
    assert alert.message == "You have exceeded 96% of the budget for 'Food' (spent $96.0 of $100.0)."


# ---- whole month ----
def test_evaluate_month_matches_spending_by_category(calc):
    lines = [{"category": "Food", "limit": 100}, {"category": "Rent", "limit": 500}]
    statuses, alerts = calc.evaluate_month(lines, {"Food": 96, "Travel": 40}, "USD", "$")
    assert [s.spent for s in statuses] == [96, 0.0]
    assert [a.category for a in alerts] == ["Food"]


def test_evaluate_month_with_no_budgets(calc):
    assert calc.evaluate_month([], {"Food": 5}, "USD", "$") == ([], [])
