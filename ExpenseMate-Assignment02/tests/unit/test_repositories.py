"""
Unit tests - repositories with a FAKE database cursor (no PostgreSQL).

They check that each repository sends parameterised SQL (never string
formatting of user values) and maps PostgreSQL types (Decimal, date,
datetime) to the plain values the services expect. Real-database behaviour
is covered by tests/integration/test_repositories_postgres.py.
"""
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.backend.models import Transaction
from app.backend.repositories import BudgetRepository, CategoryRepository, ExpenseRepository
from app.backend.repositories.expense_repository import month_date_range


class FakeDatabase:
    def __init__(self, fetchone=None, fetchall=None, rowcount=1):
        self.cur = MagicMock()
        self.cur.fetchone.side_effect = list(fetchone or [])
        self.cur.fetchall.return_value = fetchall or []
        self.cur.rowcount = rowcount

    @contextmanager
    def cursor(self):
        yield self.cur

    def sql(self, call=-1):
        return " ".join(self.cur.execute.call_args_list[call].args[0].split())

    def params(self, call=-1):
        return self.cur.execute.call_args_list[call].args[1]


TX_ROW = {"id": 3, "user_id": 7, "date": date(2026, 9, 1), "description": "lunch",
          "amount": Decimal("60.50"), "type": "expense", "category_id": 1, "currency": "usd",
          "created_at": datetime(2026, 9, 1, 12, 30, 5, 123456), "category_name": "Food"}


# ---------------- ExpenseRepository ----------------
def test_add_uses_placeholders_and_returning():
    db = FakeDatabase(fetchone=[{"id": 42}])
    tx = Transaction(user_id=7, date="2026-09-01", description="x'); DROP TABLE users;--",
                     amount=5.0, type="expense", category_id=1, currency="USD")
    assert ExpenseRepository(db).add(tx) == 42
    assert "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id" in db.sql()
    assert "DROP TABLE" not in db.sql()                  # value passed as a parameter
    assert db.params()[2] == tx.description


def test_list_maps_postgres_types_to_api_values():
    db = FakeDatabase(fetchall=[TX_ROW])
    tx = ExpenseRepository(db).list_for_user(7)[0]
    assert (tx.date, tx.amount, tx.currency) == ("2026-09-01", 60.5, "USD")
    assert isinstance(tx.amount, float)
    assert tx.created_at == "2026-09-01 12:30:05" and tx.category_name == "Food"


def test_list_month_filter_uses_date_range():
    db = FakeDatabase()
    ExpenseRepository(db).list_for_user(7, month="2026-12", type="expense")
    assert "t.date >= %s AND t.date < %s AND t.type = %s" in db.sql()
    assert db.params() == [7, date(2026, 12, 1), date(2027, 1, 1), "expense"]
    assert db.sql().endswith("ORDER BY t.date DESC, t.id DESC")


def test_month_date_range():
    assert month_date_range("2026-02") == (date(2026, 2, 1), date(2026, 3, 1))
    assert month_date_range("2026-12") == (date(2026, 12, 1), date(2027, 1, 1))


def test_delete_is_scoped_to_owner_and_reports_result():
    db = FakeDatabase(rowcount=0)
    assert ExpenseRepository(db).delete(3, 7) is False
    assert "WHERE id = %s AND user_id = %s" in db.sql() and db.params() == (3, 7)


def test_get_for_user_returns_none_when_missing():
    assert ExpenseRepository(FakeDatabase(fetchone=[None])).get_for_user(1, 2) is None


# ---------------- BudgetRepository ----------------
def test_budget_upsert_does_not_write_legacy_remaining_amount():
    db = FakeDatabase(fetchone=[{"id": 9}])
    assert BudgetRepository(db).upsert(7, 1, "2026-11", 100.0, "USD") == 9
    sql = db.sql()
    assert "ON CONFLICT (user_id, category_id, month) DO UPDATE" in sql
    assert "remaining_amount" not in sql
    assert db.params() == (7, 1, "2026-11", 100.0, "USD")


def test_budget_list_maps_rows():
    db = FakeDatabase(fetchall=[{"id": 1, "user_id": 7, "category_id": 2, "category_name": "Food",
                                 "month": "2026-11", "amount": Decimal("100.00"),
                                 "remaining_amount": None, "currency": "pkr"}])
    b = BudgetRepository(db).list_for_month(7, "2026-11")[0]
    assert (b.amount, b.currency, b.category_name, b.remaining_amount) == (100.0, "PKR", "Food", None)
    assert db.params() == (7, "2026-11")


def test_budget_delete_by_category():
    db = FakeDatabase(rowcount=1)
    assert BudgetRepository(db).delete_by_category(7, "2026-11", "Food") is True
    assert db.params() == (7, "2026-11", "Food")


# ---------------- CategoryRepository ----------------
def test_get_or_create_inserts_new_category():
    db = FakeDatabase(fetchone=[{"id": 5}])
    assert CategoryRepository(db).get_or_create("Food", "expense") == 5
    assert "ON CONFLICT (name) DO NOTHING RETURNING id" in db.sql()


def test_get_or_create_returns_existing_category():
    db = FakeDatabase(fetchone=[None, {"id": 2}])     # insert skipped -> select
    assert CategoryRepository(db).get_or_create("Food", "expense") == 2
    assert db.sql() == "SELECT id FROM categories WHERE name = %s"


@pytest.mark.parametrize("repo_class", [ExpenseRepository, BudgetRepository, CategoryRepository])
def test_repositories_contain_no_business_constants(repo_class):
    import inspect
    source = inspect.getsource(inspect.getmodule(repo_class))
    for word in ("RATIO", "convert(", "critical", "warning"):
        assert word not in source
