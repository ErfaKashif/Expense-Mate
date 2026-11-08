"""
REGRESSION — Assignment 01 `Logic` tests (tests/test_logic.py) re-targeted
at the Assignment 02 services on PostgreSQL.

The old god-class `Logic` was split, so each call now goes to the service
that owns that responsibility (see the `logic` fixture below). Inputs and
expected values are the original ones; "A02:" comments mark deliberate,
documented changes.
"""
from types import SimpleNamespace

import pytest

from app.backend.utils.errors import NotFoundError, ValidationError


@pytest.fixture
def logic(services):
    """Map each old Logic method name to the service that now owns it."""
    s = services
    return SimpleNamespace(
        add_transaction=s["expenses"].add_expense,
        delete_transaction=s["expenses"].delete_expense,
        transactions_view=s["expenses"].list_expenses,
        export_csv=s["expenses"].export_csv,
        import_csv=s["expenses"].import_csv,
        category_summary=s["analytics"].category_summary,
        balance=s["analytics"].balance,
        monthly_trend=s["analytics"].monthly_trend,
        set_budget=s["budgets"].set_budget,
        budget_status=s["budgets"].budget_status,
        to_summary_json=s["budgets"].monthly_summary,
        convert=s["currency"].convert,
        rates_table=s["currency"].rates_table,
        base_currency=s["users"].base_currency,
        set_base_currency=s["users"].set_base_currency,
    )


# --------- validation ---------
# Inside tests/test_logic.py

def test_add_income(logic, user):
    # Unpack the tuple value directly to grab the returned integer ID
    tid, alert = logic.add_transaction(user, "2026-09-01", "Salary", 1000, "income", category="Salary", currency="USD")
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


def test_unknown_user_rejected(logic, clean_db):
    # A02: an unknown user is now a NotFoundError (HTTP 404), not a ValidationError.
    with pytest.raises(NotFoundError):
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
    # Unpack both the import count and skipped row count metrics
    imported, skipped = logic.import_csv(user, csv_text)
    assert imported == 2
    assert skipped == 0
    assert logic.category_summary(user, month="2026-09")["total_expense"] == 40


def test_import_csv_skips_bad_rows(logic, user):
    csv_text = ("date,description,amount,type\n"
                "2026-09-01,good,25,expense\n"
                "not-a-date,bad,-5,expense\n")
    n,skipped = logic.import_csv(user, csv_text)
    assert n == 1 and skipped==1


def test_import_csv_wrong_headers(logic, user):
    with pytest.raises(ValidationError):
        logic.import_csv(user, "foo,bar\n1,2\n")


# --------- MULTI-CURRENCY (Phase 5 adaptive maintenance: full conversion) ---------
def test_currency_conversion(logic, clean_db):
    # 100 USD -> PKR via the public convert() helper (pivots through USD)
    pkr = logic.convert(100, "USD", "PKR")
    assert pkr == pytest.approx(100 / 0.0036)
    # A02: the private alias Logic._convert was removed (no remaining callers).


def test_conversion_round_trip(logic, clean_db):
    usd = logic.convert(250, "PKR", "USD")
    back = logic.convert(usd, "USD", "PKR")
    assert back == pytest.approx(250, rel=1e-6)


def test_unsupported_currency_rejected_on_convert_settings(logic, user):
    with pytest.raises(ValidationError):
        logic.set_base_currency(user, "XYZ")


def test_analytics_convert_to_base_currency(logic, user):
    """Mixing currencies must produce a CONVERTED total, not a naive sum."""
    logic.add_transaction(user, "2026-09-01", "a", 100, "income", currency="USD")
    logic.add_transaction(user, "2026-09-01", "b", 50, "income", currency="PKR")
    s = logic.category_summary(user, month="2026-09")
    # 50 PKR = 50 * 0.0036 = 0.18 USD  ->  total 100.18 (NOT 150)
    assert s["base_currency"] == "USD"
    assert s["total_income"] == pytest.approx(100.18, abs=0.01)
    assert s["foreign_count"] == 1


def test_native_breakdown_kept_per_currency(logic, user):
    logic.add_transaction(user, "2026-09-01", "a", 100, "income", currency="USD")
    logic.add_transaction(user, "2026-09-02", "b", 5000, "expense", currency="PKR")
    s = logic.category_summary(user, month="2026-09")
    assert s["by_currency"]["USD"]["income"] == 100
    assert s["by_currency"]["PKR"]["expense"] == 5000
    assert s["by_currency"]["PKR"]["symbol"] == "Rs"


def test_base_currency_switch_reconverts_everything(logic, user):
    logic.add_transaction(user, "2026-09-01", "a", 100, "income", currency="USD")
    logic.add_transaction(user, "2026-09-01", "b", 50, "income", currency="PKR")
    assert logic.base_currency(user) == "USD"
    logic.set_base_currency(user, "PKR")
    assert logic.base_currency(user) == "PKR"
    s = logic.category_summary(user, month="2026-09")
    # 100 USD -> 100/0.0036 = 27777.78 PKR, plus native 50 PKR
    assert s["total_income"] == pytest.approx(100 / 0.0036 + 50, rel=1e-4)
    assert s["base_symbol"] == "Rs"


def test_transactions_view_annotates_converted_amount(logic, user):
    logic.add_transaction(user, "2026-09-01", "a", 5000, "expense", currency="PKR")
    rows = logic.transactions_view(user, month="2026-09")
    assert rows[0]["amount"] == 5000            # native preserved
    assert rows[0]["currency"] == "PKR"
    assert rows[0]["amount_base"] == pytest.approx(18.0, abs=0.01)   # 5000*0.0036
    assert rows[0]["is_foreign"] is True
    assert rows[0]["currency_symbol"] == "Rs"


def test_budget_alert_across_currencies(logic, user):
    """Budget in USD, spending in PKR -> compared after conversion."""
    logic.set_budget(user, "Food", "2026-09", 10, currency="USD")
    logic.add_transaction(user, "2026-09-05", "meal", 5000, "expense",
                          category="Food", currency="PKR")   # = 18 USD
    st = logic.budget_status(user, "2026-09")
    row = st["status"][0]
    assert row["spent"] == pytest.approx(18.0, abs=0.01)
    assert row["limit"] == pytest.approx(10.0, abs=0.01)
    assert row["level"] == "critical"
    assert row["converted"] is False        # base==budget currency (USD)
    assert st["alerts"][0]["category"] == "Food"


def test_budget_set_in_foreign_currency_converted(logic, user):
    logic.set_budget(user, "Rent", "2026-09", 90000, currency="PKR")   # = 324 USD
    logic.add_transaction(user, "2026-09-05", "rent", 300, "expense",
                          category="Rent", currency="USD")
    row = logic.budget_status(user, "2026-09")["status"][0]
    assert row["limit"] == pytest.approx(324.0, abs=0.5)
    assert row["budget_currency"] == "PKR"
    assert row["converted"] is True
    # 300 of 324 = 92.6% -> between WARN_RATIO (80%) and CRITICAL_RATIO (95%)
    assert row["level"] == "warning"
    assert 0.80 <= row["ratio"] < 0.95


def test_rates_table_shape(logic, clean_db):
    t = logic.rates_table("USD")
    assert t["base"] == "USD" and t["base_symbol"] == "$"
    codes = [r["code"] for r in t["rates"]]
    assert "PKR" in codes and "EUR" in codes and "GBP" in codes
    pkr = next(r for r in t["rates"] if r["code"] == "PKR")
    assert pkr["per_base"] == pytest.approx(0.0036, abs=1e-4)
    assert pkr["one_base_equals"] == pytest.approx(1 / 0.0036, rel=1e-3)


def test_export_csv_includes_converted_column(logic, user):
    logic.add_transaction(user, "2026-09-01", "a", 5000, "expense", currency="PKR")
    text = logic.export_csv(user, month="2026-09")
    assert "amount_in_USD" in text.splitlines()[0]
    assert "18.0" in text


def test_summary_json_reports_base_currency(logic, user):
    logic.add_transaction(user, "2026-09-01", "a", 100, "income", currency="USD")
    d = logic.to_summary_json(user, "2026-09")
    assert d["base_currency"] == "USD" and d["base_symbol"] == "$"
    assert "PKR" in d["currencies"]
    assert d["total_income"] == 100


def test_add_transaction_updates_budget_remaining_and_returns_alert(logic, user):
    """Validates that creating an expense immediately reduces remaining_amount and returns an alert."""
    logic.set_budget(user, "Food", "2026-11", 100.0, currency="USD")

    # Log an expense of 80 against the 100 USD threshold limit
    tx_id, alert = logic.add_transaction(user, "2026-11-03", "Dinner", 80.0, "expense", category="Food", currency="USD")

    # Verify the inline budget row was modified in real-time
    status = logic.budget_status(user, "2026-11")
    food_budget = status["status"][0]
    assert food_budget["remaining"] == 20.0
    assert food_budget["spent"] == 80.0

    # 80/100 = 80%. Assuming WARN_RATIO <= 0.80, a localized notification must be generated
    assert alert is not None
    assert alert["level"] == "warning"
    assert "Food" in alert["message"]


def test_add_transaction_normalizes_category_casing_to_title_case(logic, user):
    """Validates that lower-case categories from javascript ('food') are title-cased ('Food')."""
    logic.set_budget(user, "Food", "2026-11", 100.0, currency="USD")

    # Send lowercase category string matching frontend select elements
    tx_id, alert = logic.add_transaction(user, "2026-11-03", "Snack", 10.0, "expense", category="food", currency="USD")

    status = logic.budget_status(user, "2026-11")
    food_budget = status["status"][0]
    assert food_budget["category"] == "Food"
    assert food_budget["spent"] == 10.0  # Verifies case matching works correctly


def test_delete_transaction_restores_budget_remaining_amount(logic, user):
    """Validates that deleting an expense automatically credits back the budget remaining_amount."""
    logic.set_budget(user, "Food", "2026-11", 100.0, currency="USD")
    tx_id, _ = logic.add_transaction(user, "2026-11-03", "Lunch", 40.0, "expense", category="Food", currency="USD")

    # Verify deduction occurred
    assert logic.budget_status(user, "2026-11")["status"][0]["remaining"] == 60.0

    # Trigger your updated conversion-aware deletion process
    success = logic.delete_transaction(user, tx_id)
    assert success is True

    # Verify the remaining headroom balance has rolled back up to 100
    assert logic.budget_status(user, "2026-11")["status"][0]["remaining"] == 100.0
