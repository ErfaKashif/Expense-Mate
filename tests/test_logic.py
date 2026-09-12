"""
Unit tests — Logic module (Member A: Frontend/backend integration logic).
Covers business rules: validation, budgets & alerts, analytics, CSV, currency.
"""
import pytest

from app.backend.logic import Logic, ValidationError


# --------- validation ---------
def test_add_income(logic, user):
    tid = logic.add_transaction(user, "2026-09-01", "Salary", 1000, "income")
    assert tid > 0


def test_negative_amount_rejected(logic, user):
    with pytest.raises(ValidationError):
        logic.add_transaction(user, "2026-09-01", "x", -5, "expense")


def test_bad_date_rejected(logic, user):
    with pytest.raises(ValidationError):
        logic.add_transaction(user, "09-01-2026", "x", 5, "expense")


def test_bad_type_rejected(logic, user):
    with pytest.raises(ValidationError):
        logic.add_transaction(user, "2026-09-01", "x", 5, "transfer")


def test_unsupported_currency_rejected(logic, user):
    with pytest.raises(ValidationError):
        logic.add_transaction(user, "2026-09-01", "x", 5, "expense", currency="XYZ")


def test_empty_description_rejected(logic, user):
    with pytest.raises(ValidationError):
        logic.add_transaction(user, "2026-09-01", "   ", 5, "expense")


def test_unknown_user_rejected(logic):
    with pytest.raises(ValidationError):
        logic.add_transaction(99999, "2026-09-01", "x", 5, "expense")


# --------- analytics ---------
def test_category_summary(logic, user):
    logic.add_transaction(user, "2026-09-01", "wages", 1000, "income", category="Salary")
    logic.add_transaction(user, "2026-09-02", "pizza", 50, "expense", category="Food")
    logic.add_transaction(user, "2026-09-03", "pizza2", 30, "expense", category="Food")
    s = logic.category_summary(user, month="2026-09")
    assert s["total_income"] == 1000
    assert s["total_expense"] == 80
    assert s["expense"]["Food"] == 80


def test_balance(logic, user):
    logic.add_transaction(user, "2026-09-01", "w", 2000, "income")
    logic.add_transaction(user, "2026-09-02", "p", 500, "expense")
    assert logic.balance(user, month="2026-09") == 1500


def test_monthly_trend_orders_months(logic, user):
    logic.add_transaction(user, "2026-07-01", "a", 100, "expense")
    logic.add_transaction(user, "2026-08-01", "b", 200, "expense")
    logic.add_transaction(user, "2026-09-01", "c", 300, "expense")
    trend = logic.monthly_trend(user, n_months=3)
    assert [t[0] for t in trend] == ["2026-07", "2026-08", "2026-09"]


# --------- budgets & alerts ---------
def test_budget_alert_critical(logic, user):
    logic.add_transaction(user, "2026-09-01", "shop", 95, "expense", category="Food")
    logic.set_budget(user, "Food", "2026-09", 100)
    st = logic.budget_status(user, "2026-09")
    assert st["status"][0]["level"] == "critical"
    assert len(st["alerts"]) == 1


def test_budget_alert_warning(logic, user):
    logic.add_transaction(user, "2026-09-01", "shop", 85, "expense", category="Food")
    logic.set_budget(user, "Food", "2026-09", 100)
    st = logic.budget_status(user, "2026-09")
    assert st["status"][0]["level"] == "warning"


def test_budget_ok_when_under(logic, user):
    logic.add_transaction(user, "2026-09-01", "shop", 40, "expense", category="Food")
    logic.set_budget(user, "Food", "2026-09", 100)
    st = logic.budget_status(user, "2026-09")
    assert st["status"][0]["level"] == "ok"
    assert st["alerts"] == []


def test_set_budget_bad_month(logic, user):
    with pytest.raises(ValidationError):
        logic.set_budget(user, "Food", "sep-2026", 100)


# --------- CSV ---------
def test_export_csv_roundtrip(logic, user):
    logic.add_transaction(user, "2026-09-01", "dinner", 40, "expense", category="Food")
    csv_text = logic.export_csv(user, month="2026-09")
    assert "date,description,amount,type,category,currency" in csv_text
    assert "dinner" in csv_text


def test_import_csv(logic, user):
    csv_text = ("date,description,amount,type,category,currency\n"
                "2026-09-01,rice,25,expense,Food,USD\n"
                "2026-09-02,taxi,15,expense,Transport,USD\n")
    n = logic.import_csv(user, csv_text)
    assert n == 2
    assert logic.category_summary(user, month="2026-09")["total_expense"] == 40


def test_import_csv_skips_bad_rows(logic, user):
    csv_text = ("date,description,amount,type\n"
                "2026-09-01,good,25,expense\n"
                "not-a-date,bad,-5,expense\n")
    n = logic.import_csv(user, csv_text)
    assert n == 1


def test_import_csv_wrong_headers(logic, user):
    with pytest.raises(ValidationError):
        logic.import_csv(user, "foo,bar\n1,2\n")


# --------- multi-currency ---------
def test_currency_conversion(logic):
    # 100 USD -> convert to PKR via logic._convert
    pkr = logic._convert(100, "USD", "PKR")
    assert pkr == pytest.approx(100 / 0.0036)


def test_currency_stored_and_summed(logic, user):
    logic.add_transaction(user, "2026-09-01", "a", 100, "income", currency="USD")
    logic.add_transaction(user, "2026-09-01", "b", 50, "income", currency="PKR")
    s = logic.category_summary(user, month="2026-09")
    # summed in native amounts (analytics keep native currency for simplicity)
    assert s["total_income"] == 150
