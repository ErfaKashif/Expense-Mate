"""
Integration & System tests — the full Client->Server->DB stack.
Member A: integration testing (module wiring).
Member B: system testing (end-to-end user journeys via the HTTP API).
"""
import pytest
from app.backend.server import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "api.db"), testing=True)
    return app.test_client()


def register_and_login(client, name="demo", pw="pw"):
    client.post("/api/register", json={"username": name, "password": pw})
    r = client.post("/api/login", json={"username": name, "password": pw})
    return r.get_json()["user_id"]


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"ExpenseMate" in r.data


def test_register_login(client):
    r = client.post("/api/register", json={"username": "a", "password": "b"})
    assert r.status_code == 201
    r2 = client.post("/api/register", json={"username": "a", "password": "b"})
    assert r2.status_code == 409
    r3 = client.post("/api/login", json={"username": "a", "password": "wrong"})
    assert r3.status_code == 401


def test_transactions_require_auth(client):
    assert client.get("/api/transactions").status_code == 401


def test_add_and_list_transaction(client):
    uid = register_and_login(client)
    h = {"X-User-Id": str(uid)}
    r = client.post("/api/transactions", json={
        "date": "2026-09-01", "description": "lunch", "amount": 60,
        "type": "expense", "category": "Food"}, headers=h)
    assert r.status_code == 201
    rows = client.get("/api/transactions", headers=h).get_json()
    assert len(rows) == 1 and rows[0]["amount"] == 60


def test_full_workflow_budget_alert(client):
    """System test: register -> add -> budget -> alert triggers."""
    uid = register_and_login(client)
    h = {"X-User-Id": str(uid)}
    for i in range(3):
        client.post("/api/transactions", json={
            "date": "2026-09-0%d" % (i + 1), "description": "x%d" % i,
            "amount": 40, "type": "expense", "category": "Food"}, headers=h)
    client.post("/api/budgets", json={"category": "Food", "month": "2026-09",
                                      "amount": 100}, headers=h)
    summary = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert summary["total_expense"] == 120
    assert summary["budget"]["alerts"]


def test_export_import_via_api(client):
    uid = register_and_login(client)
    h = {"X-User-Id": str(uid)}
    client.post("/api/transactions", json={"date": "2026-09-01",
        "description": "k", "amount": 12, "type": "expense"}, headers=h)
    exp = client.get("/api/export?month=2026-09", headers=h)
    assert exp.mimetype == "text/csv"
    imp = client.post("/api/import", json={"csv":
        "date,description,amount,type\n2026-09-02,m,8,expense\n"}, headers=h).get_json()
    assert imp["imported"] == 1


def test_validation_error_returns_400(client):
    uid = register_and_login(client)
    h = {"X-User-Id": str(uid)}
    r = client.post("/api/transactions", json={"date": "2026-09-01",
        "description": "x", "amount": -5, "type": "expense"}, headers=h)
    assert r.status_code == 400


def test_delete_transaction(client):
    uid = register_and_login(client)
    h = {"X-User-Id": str(uid)}
    tid = client.post("/api/transactions", json={"date": "2026-09-01",
        "description": "x", "amount": 5, "type": "expense"}, headers=h).get_json()["id"]
    assert client.delete(f"/api/transactions/{tid}", headers=h).status_code == 200
    assert client.delete(f"/api/transactions/{tid}", headers=h).status_code == 404


def test_currencies_endpoint(client):
    r = client.get("/api/currencies").get_json()
    assert "USD" in r["rates"] and "PKR" in r["rates"]


# ============ MULTI-CURRENCY API (integration tests) ============
def test_currencies_payload_is_rich(client):
    d = client.get("/api/currencies").get_json()
    assert d["base_currency"] == "USD" and d["base_symbol"] == "$"
    assert "PKR" in d["currencies"] and "EUR" in d["currencies"]
    assert d["symbols"]["PKR"] == "Rs"
    row = next(x for x in d["table"] if x["code"] == "PKR")
    assert row["name"] == "Pakistani Rupee"
    assert row["one_base_equals"] > 100          # 1 USD is many PKR


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


def test_change_base_currency_endpoint(client):
    uid = register_and_login(client, "cur_user")
    h = {"X-User-Id": str(uid)}
    r = client.post("/api/settings/base_currency", headers=h,
                    json={"base_currency": "EUR"})
    assert r.status_code == 200
    assert r.get_json()["base_currency"] == "EUR"
    assert client.get("/api/settings", headers=h).get_json()["base_currency"] == "EUR"


def test_change_base_currency_requires_auth(client):
    assert client.post("/api/settings/base_currency",
                       json={"base_currency": "EUR"}).status_code == 401
    assert client.get("/api/settings").status_code == 401


def test_summary_converts_mixed_currencies(client):
    """System test: spend in PKR + EUR, report in USD."""
    uid = register_and_login(client, "mix_user")
    h = {"X-User-Id": str(uid)}
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
    assert d["by_currency"]["PKR"]["expense"] == 5000        # native preserved


def test_switching_base_currency_changes_reported_totals(client):
    uid = register_and_login(client, "switch_user")
    h = {"X-User-Id": str(uid)}
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


def test_transactions_endpoint_returns_converted_amount(client):
    uid = register_and_login(client, "view_user")
    h = {"X-User-Id": str(uid)}
    client.post("/api/transactions", headers=h,
                json={"date": "2026-09-01", "description": "chai",
                      "amount": 500, "type": "expense", "currency": "PKR"})
    row = client.get("/api/transactions?month=2026-09", headers=h).get_json()[0]
    assert row["amount"] == 500 and row["currency"] == "PKR"
    assert row["amount_base"] == pytest.approx(1.8, abs=0.01)
    assert row["is_foreign"] is True
    assert row["currency_symbol"] == "Rs" and row["base_symbol"] == "$"


def test_export_csv_has_converted_column(client):
    uid = register_and_login(client, "csv_ccy")
    h = {"X-User-Id": str(uid)}
    client.post("/api/transactions", headers=h,
                json={"date": "2026-09-01", "description": "a", "amount": 1000,
                      "type": "expense", "currency": "PKR"})
    text = client.get("/api/export?month=2026-09", headers=h).get_data(as_text=True)
    assert "amount_in_USD" in text.splitlines()[0]


def test_import_csv_with_mixed_currencies(client):
    uid = register_and_login(client, "imp_ccy")
    h = {"X-User-Id": str(uid)}
    csv_text = ("date,description,amount,type,category,currency\n"
                "2026-09-01,lunch,500,expense,Food,PKR\n"
                "2026-09-02,coffee,5,expense,Food,USD\n"
                "2026-09-03,bad,row,notanumber,expense,Food,USD\n")
    d = client.post("/api/import", headers=h, json={"csv": csv_text}).get_json()
    assert d["imported"] == 2                     # malformed row skipped
    s = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert s["total_expense"] == pytest.approx(500 * 0.0036 + 5, rel=1e-4)
