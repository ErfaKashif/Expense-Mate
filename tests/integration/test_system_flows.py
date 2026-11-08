"""
INTEGRATION / SYSTEM tests - HTTP request -> controller -> service ->
repository -> real PostgreSQL (the separate TEST_DATABASE_URL database).

Cases 1-5 are the five required by the Assignment 02 brief.
"""
import os

import pytest

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "..", "app", "sample_data",
                          "sample_expenses.csv")


def db_rows(database, sql, params=()):
    with database.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# 1 -------------------------------------------------------------------------
def test_1_add_expense_is_stored_in_postgresql(client, login, clean_db):
    h = login("erfa")
    r = client.post("/api/transactions", headers=h, json={
        "date": "2026-09-01", "description": "Weekly groceries", "amount": "120.50",
        "type": "expense", "category": "groceries", "currency": "usd"})
    assert r.status_code == 201
    new_id = r.get_json()["id"]

    rows = db_rows(clean_db, "SELECT t.*, c.name AS category, u.username FROM transactions t "
                             "JOIN categories c ON c.id = t.category_id "
                             "JOIN users u ON u.id = t.user_id WHERE t.id = %s", (new_id,))
    assert len(rows) == 1
    row = rows[0]
    assert str(row["amount"]) == "120.50"                 # exact NUMERIC(14,2)
    assert row["date"].isoformat() == "2026-09-01"        # real DATE column
    assert (row["type"], row["currency"], row["category"], row["username"]) == \
        ("expense", "USD", "Groceries", "erfa")


# 2 -------------------------------------------------------------------------
def test_2_retrieve_expenses_returns_the_stored_records(client, login):
    h = login("erfa")
    for day, desc, amt, typ, cur in [("01", "salary", 2500, "income", "USD"),
                                     ("03", "rent", 900, "expense", "USD"),
                                     ("11", "chai", 2500, "expense", "PKR")]:
        client.post("/api/transactions", headers=h, json={
            "date": f"2026-09-{day}", "description": desc, "amount": amt, "type": typ,
            "currency": cur})
    client.post("/api/transactions", headers=h, json={
        "date": "2026-08-30", "description": "other month", "amount": 1, "type": "expense"})

    rows = client.get("/api/transactions?month=2026-09", headers=h).get_json()
    assert [r["description"] for r in rows] == ["chai", "rent", "salary"]   # newest first
    chai = rows[0]
    assert chai["amount"] == 2500 and chai["currency"] == "PKR"
    assert chai["amount_base"] == pytest.approx(9.0) and chai["is_foreign"] is True
    assert set(chai) >= {"id", "user_id", "date", "description", "amount", "type", "category_id",
                         "currency", "created_at", "category_name", "base_currency",
                         "base_symbol", "currency_symbol", "amount_base", "is_foreign"}
    assert len(client.get("/api/transactions", headers=h).get_json()) == 4


# 3 -------------------------------------------------------------------------
def test_3_create_monthly_budget_and_get_summary(client, login, clean_db):
    h = login("erfa")
    assert client.post("/api/budgets", headers=h, json={
        "category": "Food", "month": "2026-09", "amount": 200, "currency": "USD"}).status_code == 201
    assert len(db_rows(clean_db, "SELECT * FROM budgets WHERE month = '2026-09'")) == 1

    summary = client.get("/api/summary?month=2026-09", headers=h).get_json()
    food = summary["budget"]["status"][0]
    assert (food["category"], food["limit"], food["spent"], food["remaining"], food["level"]) == \
        ("Food", 200.0, 0.0, 200.0, "ok")
    assert summary["budget"]["month"] == "2026-09" and summary["budget"]["alerts"] == []
    # the new read-only endpoint returns the same status
    assert client.get("/api/budgets?month=2026-09", headers=h).get_json()["status"][0] == food


# 4 -------------------------------------------------------------------------
def test_4_remaining_budget_after_adding_and_deleting_expenses(client, login):
    h = login("erfa")
    client.post("/api/budgets", headers=h, json={"category": "Food", "month": "2026-09", "amount": 100})

    def remaining():
        return client.get("/api/budgets?month=2026-09", headers=h).get_json()["status"][0]

    ids = []
    for amount, expected_remaining, expected_alert in [(50, 50.0, None), (30, 20.0, "warning"),
                                                       (16, 4.0, "critical")]:
        r = client.post("/api/transactions", headers=h, json={
            "date": "2026-09-05", "description": "food", "amount": amount, "type": "expense",
            "category": "Food"}).get_json()
        ids.append(r["id"])
        assert remaining()["remaining"] == expected_remaining
        assert (r["alert"] or {}).get("level") == expected_alert

    # an expense in another currency is converted (2500 PKR = 9 USD)
    client.post("/api/transactions", headers=h, json={
        "date": "2026-09-06", "description": "chai", "amount": 2500, "type": "expense",
        "category": "Food", "currency": "PKR"})
    assert remaining()["remaining"] == -5.0

    # deleting an expense gives the money back - no stored balance to fix up
    client.delete(f"/api/transactions/{ids[0]}", headers=h)
    assert remaining()["remaining"] == 45.0
    # income never reduces a budget
    client.post("/api/transactions", headers=h, json={
        "date": "2026-09-07", "description": "refund", "amount": 500, "type": "income",
        "category": "Food"})
    assert remaining()["remaining"] == 45.0


def test_4b_budget_created_after_spending_is_consistent(client, login):
    """Assignment 01 defect: the pop-up alert ignored spending made before the budget existed."""
    h = login("erfa")
    client.post("/api/transactions", headers=h, json={
        "date": "2026-09-01", "description": "big shop", "amount": 90, "type": "expense",
        "category": "Food"})
    client.post("/api/budgets", headers=h, json={"category": "Food", "month": "2026-09", "amount": 100})
    alert = client.post("/api/transactions", headers=h, json={
        "date": "2026-09-02", "description": "snack", "amount": 1, "type": "expense",
        "category": "Food"}).get_json()["alert"]
    status = client.get("/api/budgets?month=2026-09", headers=h).get_json()["status"][0]
    assert status["level"] == alert["level"] == "warning"
    assert status["remaining"] == 9.0


# 5 -------------------------------------------------------------------------
def test_5_category_wise_summary(client, login):
    h = login("erfa")
    for desc, amt, typ, cat, cur in [("pizza", 50, "expense", "food", "USD"),
                                     ("pasta", 30, "expense", "Food", "USD"),
                                     ("bus", 2500, "expense", "Transport", "PKR"),
                                     ("wages", 1000, "income", "Salary", "USD"),
                                     ("gig", 100, "income", "Freelance", "EUR")]:
        client.post("/api/transactions", headers=h, json={
            "date": "2026-09-10", "description": desc, "amount": amt, "type": typ,
            "category": cat, "currency": cur})
    s = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert s["by_category"] == {"Food": 80.0, "Transport": 9.0}
    assert s["total_expense"] == 89.0
    assert s["total_income"] == pytest.approx(1108.0)
    assert s["balance"] == pytest.approx(1019.0)
    assert s["by_currency"]["PKR"] == {"symbol": "Rs", "income": 0.0, "expense": 2500.0, "count": 1}
    assert s["foreign_count"] == 2


# --------------------------------------------------------------------------
# Further system tests: CSV import, invalid input, isolation, DB errors
# --------------------------------------------------------------------------
def test_import_sample_csv_file(client, login):
    h = login("erfa")
    with open(SAMPLE_CSV, encoding="utf-8") as fh:
        r = client.post("/api/import", headers=h, json={"csv": fh.read()})
    assert r.get_json() == {"imported": 15, "skipped": 0}
    s = client.get("/api/summary?month=2026-09", headers=h).get_json()
    assert s["foreign_count"] == 5
    assert set(s["by_category"]) == {"Groceries", "Rent", "Transport", "Fitness", "Entertainment",
                                     "Utilities", "Dining", "Shopping", "Education"}
    exported = client.get("/api/export?month=2026-09", headers=h).get_data(as_text=True)
    assert len(exported.strip().splitlines()) == 16


def test_csv_import_is_all_or_nothing_on_database_failure(client, login, clean_db):
    h = login("erfa")
    services = client.application.extensions["expensemate"]
    repo = services["expenses"].expenses
    real_add, calls = repo.add, []

    def failing_add(tx):
        calls.append(tx)
        if len(calls) == 3:
            raise __import__("psycopg").errors.QueryCanceled("simulated failure")
        return real_add(tx)
    repo.add = failing_add
    try:
        csv_text = "date,description,amount,type\n" + "".join(
            f"2026-09-0{i},row{i},{i},expense\n" for i in range(1, 6))
        r = client.post("/api/import", headers=h, json={"csv": csv_text})
    finally:
        repo.add = real_add
    assert r.status_code == 500 and "database error" in r.get_json()["error"].lower()
    assert db_rows(clean_db, "SELECT COUNT(*) AS n FROM transactions")[0]["n"] == 0


@pytest.mark.parametrize("body, message", [
    ({"date": "2026-09-01", "description": "x", "amount": -1, "type": "expense"}, "negative"),
    ({"date": "2026/09/01", "description": "x", "amount": 1, "type": "expense"}, "YYYY-MM-DD"),
    ({"date": "2026-09-01", "description": "x", "amount": "ten", "type": "expense"}, "number"),
    ({"date": "2026-09-01", "description": "x", "amount": 1, "type": "gift"}, "Invalid type"),
    ({"date": "2026-09-01", "description": "x", "amount": 1, "type": "expense", "currency": "ABC"}, "Unsupported"),
    ({"date": "2026-09-01", "description": " ", "amount": 1, "type": "expense"}, "Description"),
    ({"description": "x", "amount": 1, "type": "expense"}, "date"),
])
def test_invalid_expense_input_returns_400_and_stores_nothing(client, login, clean_db, body, message):
    h = login("erfa")
    r = client.post("/api/transactions", headers=h, json=body)
    assert r.status_code == 400 and message in r.get_json()["error"]
    assert db_rows(clean_db, "SELECT COUNT(*) AS n FROM transactions")[0]["n"] == 0


@pytest.mark.parametrize("body", [
    {"category": "Food", "month": "2026-13", "amount": 10},
    {"category": "Food", "month": "2026-09", "amount": -10},
    {"month": "2026-09", "amount": 10},
    {"category": "Food", "month": "2026-09", "amount": 10, "currency": "XYZ"},
])
def test_invalid_budget_input_returns_400(client, login, body):
    assert client.post("/api/budgets", headers=login("erfa"), json=body).status_code == 400


def test_users_cannot_delete_each_others_transactions(client, login):
    alice, bob = login("alice"), login("bob")
    tid = client.post("/api/transactions", headers=alice, json={
        "date": "2026-09-01", "description": "private", "amount": 5, "type": "expense"}).get_json()["id"]
    assert client.delete(f"/api/transactions/{tid}", headers=bob).status_code == 404
    assert len(client.get("/api/transactions", headers=alice).get_json()) == 1
    assert client.delete("/api/transactions/999999", headers=alice).status_code == 404


def test_database_down_returns_503(database_url):
    from app.backend.server import create_app
    bad_url = database_url.rsplit("@", 1)[0].rsplit(":", 1)[0] + ":wrong-password@" + \
        database_url.rsplit("@", 1)[1]
    app = create_app(bad_url, testing=True, run_migrations=False)
    r = app.test_client().get("/api/categories")
    assert r.status_code == 503
    assert r.get_json() == {"error": "The database is currently unavailable."}
