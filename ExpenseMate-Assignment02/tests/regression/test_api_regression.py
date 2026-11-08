"""
REGRESSION — Assignment 01 API tests (tests/test_api.py), re-run unchanged
against the Assignment 02 layered backend on PostgreSQL.

Only the fixture wiring changed (SQLite temp file -> PostgreSQL test
database). Every request and assertion is the original one, except where a
comment marked "A02:" explains a deliberate, documented behaviour fix.
"""
import pytest


@pytest.fixture
def register_and_login(login):
    """Original helper signature: returns (token_placeholder, headers)."""
    def _register_and_login(client, name="demo", pw="pw"):
        return None, login(name, pw)
    return _register_and_login


# ============ BASIC & SECURITY TESTS ============ #

def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"ExpenseMate" in r.data


def test_jwt_token_issued_on_login_and_register(client):
    r_reg = client.post("/api/register", json={"username": "jwt_user", "password": "password123"})
    assert r_reg.status_code == 201
    assert "access_token" in r_reg.get_json()

    r_log = client.post("/api/login", json={"username": "jwt_user", "password": "password123"})
    assert r_log.status_code == 200
    assert "access_token" in r_log.get_json()


def test_protected_routes_reject_missing_token(client):
    protected_endpoints = [
        "/api/transactions",
        "/api/summary?month=2026-09",
        "/api/settings",
        "/api/export?month=2026-09",
    ]
    for endpoint in protected_endpoints:
        res = client.get(endpoint)
        assert res.status_code == 401


def test_protected_routes_reject_invalid_token(client):
    bad_headers = {"Authorization": "Bearer invalid.jwt.token"}
    r = client.get("/api/transactions", headers=bad_headers)
    # Flask-JWT-Extended returns 422 for malformed tokens, 401 for missing tokens
    assert r.status_code in [401, 422]


def test_protected_route_with_valid_jwt(client, register_and_login):
    _, headers = register_and_login(client, name="auth_tester")
    r = client.get("/api/transactions", headers=headers)
    assert r.status_code == 200


def test_jwt_user_isolation(client, register_and_login):
    _, headers_a = register_and_login(client, name="user_a", pw="pw1")
    client.post("/api/transactions", json={
        "date": "2026-09-01", "description": "Secret A", "amount": 100,
        "type": "expense", "category": "Food"
    }, headers=headers_a)

    _, headers_b = register_and_login(client, name="user_b", pw="pw2")
    rows_b = client.get("/api/transactions", headers=headers_b).get_json()
    assert len(rows_b) == 0


def test_register_login_validation(client):
    r = client.post("/api/register", json={"username": "a", "password": "b"})
    assert r.status_code == 201

    r2 = client.post("/api/register", json={"username": "a", "password": "b"})
    assert r2.status_code == 409

    r3 = client.post("/api/login", json={"username": "a", "password": "wrong"})
    assert r3.status_code == 401


# ============ TRANSACTION & WORKFLOW TESTS ============ #

def test_add_and_list_transaction(client, register_and_login):
    _, h = register_and_login(client)
    r = client.post("/api/transactions", json={
        "date": "2026-09-01", "description": "lunch", "amount": 60,
        "type": "expense", "category": "Food"}, headers=h)
    assert r.status_code == 201
    rows = client.get("/api/transactions", headers=h).get_json()
    assert len(rows) == 1 and rows[0]["amount"] == 60


def test_full_workflow_budget_alert(client, register_and_login):
    _, h = register_and_login(client)
    for i in range(3):
        client.post("/api/transactions", json={
            "date": "2026-09-0%d" % (i + 1), "description": "x%d" % i,
            "amount": 40, "type": "expense", "category": "Food"}, headers=h)
    client.post("/api/budgets", json={"category": "Food", "month": "2026-09",
                                      "amount": 100}, headers=h)
    summary = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert summary["total_expense"] == 120
    assert summary["budget"]["alerts"]


def test_export_import_via_api(client, register_and_login):
    _, h = register_and_login(client)
    client.post("/api/transactions", json={"date": "2026-09-01",
        "description": "k", "amount": 12, "type": "expense"}, headers=h)
    exp = client.get("/api/export?month=2026-09", headers=h)
    assert exp.mimetype == "text/csv"
    imp = client.post("/api/import", json={"csv":
        "date,description,amount,type\n2026-09-02,m,8,expense\n"}, headers=h).get_json()
    assert imp["imported"] == 1


# ============ MULTI-CURRENCY TESTS ============ #

def test_currencies_endpoint(client):
    r = client.get("/api/currencies").get_json()
    assert "USD" in r["rates"] and "PKR" in r["rates"]


def test_currencies_payload_is_rich(client):
    d = client.get("/api/currencies").get_json()
    assert d["base_currency"] == "USD" and d["base_symbol"] == "$"
    assert "PKR" in d["currencies"] and "EUR" in d["currencies"]
    assert d["symbols"]["PKR"] == "Rs"
    row = next(x for x in d["table"] if x["code"] == "PKR")
    assert row["name"] == "Pakistani Rupee"
    assert row["one_base_equals"] > 100


def test_register_with_base_currency(client):
    r = client.post("/api/register", json={"username": "pkr_user",
                                           "password": "pw",
                                           "base_currency": "PKR"})
    assert r.status_code == 201
    assert r.get_json()["base_currency"] == "PKR"
    d = client.post("/api/login", json={"username": "pkr_user",
                                        "password": "pw"}).get_json()
    assert d["base_currency"] == "PKR" and d["base_symbol"] == "Rs"


def test_register_rejects_unknown_currency(client):
    r = client.post("/api/register", json={"username": "x", "password": "y",
                                           "base_currency": "XYZ"})
    assert r.status_code == 400
    assert "Unsupported currency" in r.get_json()["error"]


def test_convert_endpoint(client):
    d = client.post("/api/convert", json={"amount": 100, "from": "USD",
                                          "to": "PKR"}).get_json()
    assert d["result"] == pytest.approx(100 / 0.0036, rel=1e-4)
    assert d["from_symbol"] == "$" and d["to_symbol"] == "Rs"


def test_convert_endpoint_validates(client):
    assert client.post("/api/convert", json={"amount": 1, "from": "USD",
                                             "to": "XYZ"}).status_code == 400
    assert client.post("/api/convert", json={"amount": "abc", "from": "USD",
                                             "to": "PKR"}).status_code == 400


def test_change_base_currency_endpoint(client, register_and_login):
    _, h = register_and_login(client, "cur_user")
    r = client.post("/api/settings/base_currency", headers=h,
                    json={"base_currency": "EUR"})
    assert r.status_code == 200
    assert r.get_json()["base_currency"] == "EUR"
    assert client.get("/api/settings", headers=h).get_json()["base_currency"] == "EUR"


def test_change_base_currency_requires_auth(client):
    assert client.post("/api/settings/base_currency",
                       json={"base_currency": "EUR"}).status_code == 401
    assert client.get("/api/settings").status_code == 401


def test_summary_converts_mixed_currencies(client, register_and_login):
    _, h = register_and_login(client, "mix_user")
    for cur, amt in (("PKR", 5000), ("EUR", 100), ("USD", 50)):
        client.post("/api/transactions", headers=h,
                    json={"date": "2026-09-01", "description": f"in {cur}",
                          "amount": amt, "type": "expense",
                          "category": "Food", "currency": cur})
    d = client.get("/api/summary?month=2026-09", headers=h).get_json()
    expected = 5000 * 0.0036 + 100 * 1.08 + 50 * 1.0
    assert d["base_currency"] == "USD"
    assert d["total_expense"] == pytest.approx(expected, rel=1e-4)
    assert d["foreign_count"] == 2
    assert set(d["by_currency"].keys()) == {"PKR", "EUR", "USD"}
    assert d["by_currency"]["PKR"]["expense"] == 5000


def test_switching_base_currency_changes_reported_totals(client, register_and_login):
    _, h = register_and_login(client, "switch_user")
    client.post("/api/transactions", headers=h,
                json={"date": "2026-09-01", "description": "salary",
                      "amount": 1000, "type": "income", "currency": "USD"})
    usd_total = client.get("/api/summary?month=2026-09",
                           headers=h).get_json()["total_income"]
    client.post("/api/settings/base_currency", headers=h,
                json={"base_currency": "PKR"})
    pkr = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert usd_total == pytest.approx(1000, rel=1e-6)
    assert pkr["total_income"] == pytest.approx(1000 / 0.0036, rel=1e-4)
    assert pkr["base_symbol"] == "Rs"


def test_transactions_endpoint_returns_converted_amount(client, register_and_login):
    _, h = register_and_login(client, "view_user")
    client.post("/api/transactions", headers=h,
                json={"date": "2026-09-01", "description": "chai",
                      "amount": 500, "type": "expense", "currency": "PKR"})
    row = client.get("/api/transactions?month=2026-09", headers=h).get_json()[0]
    assert row["amount"] == 500 and row["currency"] == "PKR"
    assert row["amount_base"] == pytest.approx(1.8, abs=0.01)
    assert row["is_foreign"] is True
    assert row["currency_symbol"] == "Rs" and row["base_symbol"] == "$"


def test_export_csv_has_converted_column(client, register_and_login):
    _, h = register_and_login(client, "csv_ccy")
    client.post("/api/transactions", headers=h,
                json={"date": "2026-09-01", "description": "a", "amount": 1000,
                      "type": "expense", "currency": "PKR"})
    text = client.get("/api/export?month=2026-09", headers=h).get_data(as_text=True)
    assert "amount_in_USD" in text.splitlines()[0]


def test_import_csv_with_mixed_currencies(client, register_and_login):
    _, h = register_and_login(client, "imp_ccy")
    csv_text = ("date,description,amount,type,category,currency\n"
                "2026-09-01,lunch,500,expense,Food,PKR\n"
                "2026-09-02,coffee,5,expense,Food,USD\n"
                "2026-09-03,bad,row,notanumber,expense,Food,USD\n")
    d = client.post("/api/import", headers=h, json={"csv": csv_text}).get_json()
    assert d["imported"] == 2
    s = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert s["total_expense"] == pytest.approx(500 * 0.0036 + 5, rel=1e-4)


def test_validation_error_returns_400(client, register_and_login):
    _, h = register_and_login(client)
    # A02: the original test also accepted an uncaught ValidationError (an
    # HTTP 500 in production). The layered backend must answer 400.
    r = client.post("/api/transactions", json={
        "date": "2026-09-01", "description": "x", "amount": -5,
        "type": "expense", "category": "Food", "currency": "USD"
    }, headers=h)
    assert r.status_code == 400
    assert "negative" in r.get_json()["error"]


def test_delete_transaction(client, register_and_login):
    _, h = register_and_login(client)
    res = client.post("/api/transactions", json={
        "date": "2026-09-01", "description": "x", "amount": 5,
        "type": "expense", "category": "Food", "currency": "USD"
    }, headers=h).get_json()

    tid = res["id"]
    r1 = client.delete(f"/api/transactions/{tid}", headers=h)
    assert r1.status_code in [200, 204]


def test_api_add_transaction_returns_alert_in_json_payload(client, register_and_login):
    _, h = register_and_login(client, "alert_user")
    client.post("/api/budgets", json={"category": "Food", "month": "2026-11", "amount": 100.0, "currency": "USD"},
                headers=h)

    r = client.post("/api/transactions", json={
        "date": "2026-11-03", "description": "Expensive Groceries", "amount": 96.0,
        "type": "expense", "category": "Food", "currency": "USD"
    }, headers=h)

    assert r.status_code == 201
    payload = r.get_json()
    assert "alert" in payload
    assert payload["alert"]["level"] == "critical"
    assert "96%" in payload["alert"]["message"]


def test_api_delete_budget_by_category_endpoint(client, register_and_login):
    _, h = register_and_login(client, "delete_user")
    client.post("/api/budgets", json={"category": "Rent", "month": "2026-11", "amount": 1200.0, "currency": "USD"},
                headers=h)

    r = client.delete("/api/budgets/by-category", json={
        "category": "Rent",
        "month": "2026-11"
    }, headers=h)

    assert r.status_code == 200
    assert r.get_json()["status"] == "success"

    summary = client.get("/api/summary?month=2026-11", headers=h).get_json()
    assert len(summary["budget"]["status"]) == 0