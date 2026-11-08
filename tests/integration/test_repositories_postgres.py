"""INTEGRATION - repositories against real PostgreSQL (constraints, types, transactions)."""
import psycopg
import pytest

from app.backend.models import Transaction
from app.backend.repositories import (
    BudgetRepository, CategoryRepository, ExpenseRepository, UserRepository,
)


@pytest.fixture
def repos(clean_db):
    return (UserRepository(clean_db), CategoryRepository(clean_db),
            ExpenseRepository(clean_db), BudgetRepository(clean_db))


def make_tx(user_id, **kw):
    data = dict(user_id=user_id, date="2026-09-15", description="d", amount=10.0,
                type="expense", currency="USD")
    data.update(kw)
    return Transaction(**data)


def test_money_is_stored_exactly(repos):
    users, cats, txs, _ = repos
    uid = users.create("u", "h", "USD")
    txs.add(make_tx(uid, amount=0.1))
    txs.add(make_tx(uid, amount=0.2))
    amounts = [t.amount for t in txs.list_for_user(uid)]
    assert sorted(amounts) == [0.1, 0.2]


def test_month_filter_boundaries(repos):
    users, _, txs, _ = repos
    uid = users.create("u", "h", "USD")
    for d in ("2026-08-31", "2026-09-01", "2026-09-30", "2026-10-01"):
        txs.add(make_tx(uid, date=d, description=d))
    assert sorted(t.date for t in txs.list_for_user(uid, month="2026-09")) == ["2026-09-01", "2026-09-30"]


def test_constraints_enforced_by_postgresql(repos, clean_db):
    users, cats, txs, budgets = repos
    uid = users.create("u", "h", "USD")
    with pytest.raises(psycopg.errors.CheckViolation):
        txs.add(make_tx(uid, amount=-1))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        txs.add(make_tx(9999))
    with pytest.raises(psycopg.errors.CheckViolation):
        budgets.upsert(uid, cats.get_or_create("Food", "expense"), "2026-13", 10, "USD")


def test_budget_upsert_updates_in_place(repos):
    users, cats, _, budgets = repos
    uid, cid = users.create("u", "h", "USD"), cats.get_or_create("Food", "expense")
    first = budgets.upsert(uid, cid, "2026-09", 100, "USD")
    second = budgets.upsert(uid, cid, "2026-09", 250, "EUR")
    rows = budgets.list_for_month(uid, "2026-09")
    assert first == second and len(rows) == 1
    assert (rows[0].amount, rows[0].currency) == (250.0, "EUR")


def test_service_transaction_rolls_back_every_statement(repos, clean_db):
    users, cats, txs, _ = repos
    uid = users.create("u", "h", "USD")
    with pytest.raises(RuntimeError):
        with clean_db.transaction():
            cats.get_or_create("Temp", "expense")
            txs.add(make_tx(uid))
            raise RuntimeError("fail after two writes")
    assert txs.count() == 0
    assert [c.name for c in cats.list_all()] == []


def test_deleting_user_cascades(repos, clean_db):
    users, _, txs, _ = repos
    uid = users.create("u", "h", "USD")
    txs.add(make_tx(uid))
    with clean_db.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (uid,))
    assert txs.count() == 0


def test_ids_continue_after_explicit_inserts(repos, clean_db):
    """Mirrors what the migration does: explicit ids + sequence reset."""
    users = repos[0]
    with clean_db.cursor() as cur:
        cur.execute("INSERT INTO users (id, username, password) VALUES (50, 'old', 'h')")
        cur.execute("SELECT setval(pg_get_serial_sequence('users','id'), 51, false)")
    assert users.create("new", "h", "USD") == 51
