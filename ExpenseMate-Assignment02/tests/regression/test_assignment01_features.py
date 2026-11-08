"""
REGRESSION - every Assignment 01 user feature, exercised exactly the way the
unchanged frontend (app/frontend/static/app.js) calls the API.
"""
import os

import pytest

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "..", "app", "sample_data",
                          "sample_expenses.csv")


def add(client, h, **body):
    base = {"date": "2026-09-01", "description": "item", "amount": 10, "type": "expense",
            "category": "Food", "currency": "USD"}
    base.update(body)
    return client.post("/api/transactions", headers=h, json=base)


def test_frontend_page_and_assets_are_served(client):
    page = client.get("/")
    assert page.status_code == 200 and b"ExpenseMate" in page.data
    for asset in ("app.js", "style.css", "chart.umd.min.js"):
        assert client.get(f"/static/{asset}").status_code == 200


def test_register_login_and_session_check(client):
    r = client.post("/api/register", json={"username": "u", "password": "p", "base_currency": "PKR"})
    token = r.get_json()["access_token"]
    s = client.get("/api/settings", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert s == {"base_currency": "PKR", "base_symbol": "Rs", "currencies": s["currencies"]}


def test_add_and_view_expenses(client, login):
    h = login()
    assert add(client, h, description="lunch", amount=60).status_code == 201
    assert add(client, h, description="bus", amount=200, category="Transport", currency="PKR").status_code == 201
    rows = client.get("/api/transactions?month=2026-09", headers=h).get_json()
    assert {r["description"] for r in rows} == {"lunch", "bus"}


def test_add_income(client, login):
    h = login()
    add(client, h, description="salary", amount=2500, type="income", category="Salary")
    s = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert s["total_income"] == 2500 and s["total_expense"] == 0 and s["balance"] == 2500


def test_manage_monthly_budgets(client, login):
    h = login()
    budget = {"category": "Food", "month": "2026-09", "amount": 100, "currency": "USD"}
    assert client.post("/api/budgets", headers=h, json=budget).status_code == 201
    budget["amount"] = 150                                           # update (upsert)
    client.post("/api/budgets", headers=h, json=budget)
    add(client, h, amount=60)
    st = client.get("/api/summary?month=2026-09", headers=h).get_json()["budget"]["status"]
    assert [(b["category"], b["limit"], b["spent"], b["remaining"]) for b in st] == [("Food", 150, 60, 90)]
    r = client.delete("/api/budgets/by-category", headers=h, json={"category": "Food", "month": "2026-09"})
    assert r.status_code == 200
    assert client.get("/api/summary?month=2026-09", headers=h).get_json()["budget"]["status"] == []
    assert client.delete("/api/budgets/by-category", headers=h,
                         json={"category": "Food", "month": "2026-09"}).status_code == 404


def test_budget_alerts_shown_on_dashboard(client, login):
    h = login()
    client.post("/api/budgets", headers=h, json={"category": "Food", "month": "2026-09", "amount": 100})
    r = add(client, h, amount=96).get_json()
    assert r["alert"]["level"] == "critical"
    alerts = client.get("/api/summary?month=2026-09", headers=h).get_json()["budget"]["alerts"]
    assert alerts[0]["message"] == r["alert"]["message"]


def test_category_wise_summary(client, login):
    h = login()
    add(client, h, amount=50, category="Food")
    add(client, h, amount=30, category="food")
    add(client, h, amount=20, category="Rent")
    assert client.get("/api/summary?month=2026-09", headers=h).get_json()["by_category"] == \
        {"Food": 80.0, "Rent": 20.0}


def test_chart_data_contract(client, login):
    """Pie chart uses by_category {name: number}; line chart uses trend [[month, income, expense]]."""
    h = login()
    for month in ("07", "08", "09"):
        add(client, h, date=f"2026-{month}-01", amount=int(month))
        add(client, h, date=f"2026-{month}-02", amount=100, type="income", category="Salary")
    s = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert all(isinstance(v, (int, float)) for v in s["by_category"].values())
    assert s["trend"] == [["2026-07", 100.0, 7.0], ["2026-08", 100.0, 8.0], ["2026-09", 100.0, 9.0]]


def test_import_sample_csv(client, login):
    h = login()
    with open(SAMPLE_CSV, encoding="utf-8") as fh:
        assert client.post("/api/import", headers=h, json={"csv": fh.read()}).get_json() == \
            {"imported": 15, "skipped": 0}
    assert len(client.get("/api/transactions?month=2026-09", headers=h).get_json()) == 15


def test_export_csv_download(client, login):
    h = login()
    add(client, h, description="k", amount=12)
    r = client.get("/api/export?month=2026-09", headers=h)
    assert r.mimetype == "text/csv" and "attachment" in r.headers["Content-Disposition"]
    assert r.get_data(as_text=True).splitlines()[1] == "2026-09-01,k,12.0,expense,Food,USD,12.0"


def test_currency_converter_and_base_currency_switch(client, login):
    h = login()
    assert client.post("/api/convert", json={"amount": 100, "from": "USD", "to": "PKR"}
                       ).get_json()["result"] == pytest.approx(27777.7778)
    add(client, h, amount=10, currency="USD")
    client.post("/api/settings/base_currency", headers=h, json={"base_currency": "EUR"})
    s = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert s["base_currency"] == "EUR" and s["total_expense"] == pytest.approx(9.26, abs=0.01)


def test_delete_transaction_from_table(client, login):
    h = login()
    tid = add(client, h).get_json()["id"]
    assert client.delete(f"/api/transactions/{tid}", headers=h).get_json() == {"ok": True}
    assert client.get("/api/transactions", headers=h).get_json() == []
