"""
Unit tests — Database module (Member A: Backend).
Tests the persistence layer in isolation via repository methods.
"""
import pytest

from app.backend.db import Database


def test_schema_created(tmp_path):
    db = Database(str(tmp_path / "a.db"))
    db.add_transaction  # methods exist
    assert db.path.endswith("a.db")


def test_create_and_get_user(db):
    uid = db.create_user("alice", "pw")
    u = db.get_user(uid)
    assert u["username"] == "alice"
    assert u["base_currency"] == "USD"


def test_username_unique(db):
    import sqlite3
    db.create_user("bob", "1")
    # a second user with the same username must be rejected by the UNIQUE index
    with pytest.raises(sqlite3.IntegrityError):
        db.create_user("bob", "1")


def test_get_user_by_name(db):
    uid = db.create_user("carol", "pw")
    assert db.get_user_by_name("carol")["id"] == uid
    assert db.get_user_by_name("nobody") is None


def test_ensure_category_idempotent(db):
    a = db.ensure_category("Food", "expense")
    b = db.ensure_category("Food", "expense")
    assert a == b


def test_categories_by_kind(db):
    db.ensure_category("Salary", "income")
    db.ensure_category("Food", "expense")
    inc = db.list_categories("income")
    exp = db.list_categories("expense")
    assert len(inc) == 1 and inc[0]["name"] == "Salary"
    assert len(exp) == 1 and exp[0]["name"] == "Food"


def test_add_and_get_transaction(db, user):
    tid = db.add_transaction(user, "2026-09-01", "groceries", 100, "expense")
    t = db.get_transaction(tid)
    assert t["amount"] == 100
    assert t["type"] == "expense"


def test_list_transactions_filter_month(db, user):
    db.add_transaction(user, "2026-09-01", "a", 10, "expense")
    db.add_transaction(user, "2026-08-15", "b", 20, "expense")
    sept = db.list_transactions(user, month="2026-09")
    assert len(sept) == 1 and sept[0]["description"] == "a"

def test_delete_transaction(db, user):
    # Ensure a valid category entry exists first to satisfy the database foreign key requirement
    cat_id = db.ensure_category("Food", "expense")

    # Pass the real generated cat_id into the query function
    tid = db.add_transaction(user, "2026-09-01", "a", 10, "expense", cat_id, "USD")

    # Execute and verify the deletion
    db.delete_transaction(tid)
    assert db.get_transaction(tid) is None


def test_set_and_get_budget_upsert(db, user):
    cat = db.ensure_category("Food", "expense")
    # Explicitly pass the required positional currency argument string
    db.set_budget(user, cat, "2026-09", 500, "USD")
    db.set_budget(user, cat, "2026-09", 700, "USD")  # Upsert override block
    budgets = db.get_budgets(user, month="2026-09")
    assert len(budgets) == 1 and budgets[0]["amount"] == 700


def test_foreign_key_cascade_removes_transactions(db, user):
    db.add_transaction(user, "2026-09-01", "a", 10, "expense")
    conn = db.connect()
    with conn as c:
        c.execute("DELETE FROM users WHERE id = ?", (user,))
    assert db.counts() == 0


def test_budget_initializes_with_equal_remaining_amount(db, user):
    """Validates fix for sqlite3.IntegrityError by ensuring remaining_amount matches amount."""
    cat = db.ensure_category("Food", "expense")
    # Call your upgraded set_budget containing the ON CONFLICT / remaining_amount parameters
    db.set_budget(user, cat, "2026-11", 500.0, "USD")

    budgets = db.get_budgets(user, month="2026-11")
    assert len(budgets) == 1
    assert budgets[0]["amount"] == 500.0
    assert budgets[0]["remaining_amount"] == 500.0  # Verifies default assignment constraint


def test_delete_budget_by_category_compound_unique_match(db, user):
    """Validates the new custom key-matching deletion execution flow."""
    cat = db.ensure_category("Entertainment", "expense")
    db.set_budget(user, cat, "2026-11", 200.0, "USD")

    # Run the targeted removal using the query layer
    success = db.delete_budget_by_category(user, "2026-11", "Entertainment")
    assert success is True

    # Verify the item has been completely removed from the mapping view
    remaining_budgets = db.get_budgets(user, month="2026-11")
    assert len(remaining_budgets) == 0
