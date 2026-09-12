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
