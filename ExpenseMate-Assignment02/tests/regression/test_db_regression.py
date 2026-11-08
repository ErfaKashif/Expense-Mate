"""
REGRESSION — Assignment 01 `Database` tests (tests/test_db.py) re-targeted
at the Assignment 02 repositories on PostgreSQL.

The old single `Database` class (all tables, all SQL) was split into one
repository per table; the `db` fixture maps the old method names onto them.
"""
from types import SimpleNamespace

import psycopg
import pytest

from app.backend.models import Transaction
from app.backend.repositories import (
    BudgetRepository, CategoryRepository, ExpenseRepository, UserRepository,
)


@pytest.fixture
def db(clean_db):
    users, cats = UserRepository(clean_db), CategoryRepository(clean_db)
    txs, budgets = ExpenseRepository(clean_db), BudgetRepository(clean_db)

    def add_transaction(user_id, date, description, amount, type, category_id=None,
                        currency="USD"):
        return txs.add(Transaction(user_id=user_id, date=date, description=description,
                                   amount=amount, type=type, category_id=category_id,
                                   currency=currency))

    def get_user(user_id):
        u = users.get_by_id(user_id)
        return u and {"id": u.id, "username": u.username, "base_currency": u.base_currency}

    return SimpleNamespace(
        database=clean_db,
        create_user=lambda name, pw, base="USD": users.create(name, pw, base),
        get_user=get_user,
        get_user_by_name=lambda name: (lambda u: u and {"id": u.id})(users.get_by_username(name)),
        ensure_category=cats.get_or_create,
        list_categories=lambda kind=None: [c.to_dict() for c in cats.list_all(kind)],
        add_transaction=add_transaction,
        get_transaction=lambda tid: _get_tx(clean_db, tid),
        list_transactions=lambda uid, month=None: [t.to_dict() for t in txs.list_for_user(uid, month)],
        delete_transaction=lambda tid, uid: txs.delete(tid, uid),
        set_budget=budgets.upsert,
        get_budgets=lambda uid, month: [vars(b) for b in budgets.list_for_month(uid, month)],
        delete_budget_by_category=budgets.delete_by_category,
        counts=txs.count,
    )


def _get_tx(database, tid):
    with database.cursor() as cur:
        cur.execute("SELECT * FROM transactions WHERE id = %s", (tid,))
        row = cur.fetchone()
        return Transaction.from_row(row).to_dict() if row else None


@pytest.fixture
def user(db):
    return db.create_user("tester", "x", "USD")


def test_schema_created(clean_db):
    # A02: schema comes from versioned SQL migrations instead of a .db file path.
    with clean_db.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations")
        assert "001" in {r["version"] for r in cur.fetchall()}


def test_create_and_get_user(db):
    uid = db.create_user("alice", "pw")
    u = db.get_user(uid)
    assert u["username"] == "alice"
    assert u["base_currency"] == "USD"


def test_username_unique(db):
    db.create_user("bob", "1")
    # a second user with the same username must be rejected by the UNIQUE index
    with pytest.raises(psycopg.errors.UniqueViolation):
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
    db.delete_transaction(tid, user)          # A02: delete now requires the owner id
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
    with db.database.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user,))
    assert db.counts() == 0


def test_budget_initializes_with_equal_remaining_amount(db, user):
    """Validates fix for sqlite3.IntegrityError by ensuring remaining_amount matches amount."""
    cat = db.ensure_category("Food", "expense")
    # Call your upgraded set_budget containing the ON CONFLICT / remaining_amount parameters
    db.set_budget(user, cat, "2026-11", 500.0, "USD")

    budgets = db.get_budgets(user, month="2026-11")
    assert len(budgets) == 1
    assert budgets[0]["amount"] == 500.0
    # A02 (rewrite of the budget module): the running `remaining_amount` column
    # is no longer written - it drifted out of sync with real spending. The
    # remaining budget is calculated instead; see
    # tests/unit/test_budget_calculator.py and the remaining-amount tests in
    # test_logic_regression.py, which still expect 500 -> 420 -> 500.
    assert budgets[0]["remaining_amount"] is None


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
