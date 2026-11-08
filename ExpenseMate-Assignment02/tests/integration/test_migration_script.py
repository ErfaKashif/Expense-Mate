"""
INTEGRATION - the SQLite -> PostgreSQL migration script, end to end, against
the TEST database (never the application database). Uses a COPY of the real
Assignment 01 SQLite file so the original is never opened for writing.
"""
import hashlib
import os
import shutil
import sqlite3
from contextlib import closing

import pytest

from migration import migrate_sqlite_to_postgres as migration

ORIGINAL_DB = os.path.join(os.path.dirname(__file__), "..", "..", "app", "data", "expensemate.db")


@pytest.fixture
def sqlite_copy(tmp_path):
    path = tmp_path / "expensemate_copy.db"
    shutil.copy(ORIGINAL_DB, path)
    return str(path)


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(sqlite_path, *extra):
    return migration.main(["--sqlite", sqlite_path, "--target-env", "TEST_DATABASE_URL", *extra])


def test_migration_copies_and_verifies_all_records(sqlite_copy, clean_db):
    before = sha(sqlite_copy)
    assert run(sqlite_copy) == 0
    assert sha(sqlite_copy) == before                      # source untouched

    with closing(sqlite3.connect(sqlite_copy)) as src:
        for table in ("users", "categories", "transactions", "budgets", "settings"):
            expected = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            with clean_db.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
                assert cur.fetchone()["n"] == expected


def test_migrated_data_is_readable_by_the_application(sqlite_copy, clean_db):
    from app.backend.server import build_services
    assert run(sqlite_copy) == 0
    services = build_services(clean_db)
    with closing(sqlite3.connect(sqlite_copy)) as src:
        user_id, base = src.execute("SELECT id, base_currency FROM users ORDER BY id").fetchone()
        n_rows = src.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?",
                             (user_id,)).fetchone()[0]
        max_id = src.execute("SELECT MAX(id) FROM transactions").fetchone()[0]
    assert services["users"].base_currency(user_id) == base.upper()
    assert len(services["expenses"].list_expenses(user_id)) == n_rows
    # new rows get fresh ids after the migrated ones
    new_id, _ = services["expenses"].add_expense(user_id, "2026-11-07", "after migration", 1, "expense")
    assert new_id == max_id + 1


def test_rerun_is_refused_then_replace_works(sqlite_copy, clean_db):
    assert run(sqlite_copy) == 0
    assert run(sqlite_copy) == 2                           # target not empty -> refused
    assert run(sqlite_copy, "--replace") == 0


def test_failure_rolls_back_everything(sqlite_copy, clean_db):
    conn = sqlite3.connect(sqlite_copy)
    conn.execute("PRAGMA ignore_check_constraints = ON")
    conn.execute("INSERT INTO transactions (user_id, date, description, amount, type) "
                 "VALUES (1, '2026-11-05', 'corrupt', -10, 'expense')")
    conn.commit()
    conn.close()
    assert run(sqlite_copy) == 1
    with clean_db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM users")
        assert cur.fetchone()["n"] == 0                     # nothing half-copied


def test_invalid_date_in_source_aborts_before_writing(sqlite_copy, clean_db):
    conn = sqlite3.connect(sqlite_copy)
    conn.execute("UPDATE transactions SET date = '03/11/2026' WHERE id = (SELECT MIN(id) FROM transactions)")
    conn.commit()
    conn.close()
    assert run(sqlite_copy) == 1


def test_precision_warning_for_sub_cent_amounts(sqlite_copy, clean_db, capsys):
    conn = sqlite3.connect(sqlite_copy)
    conn.execute("UPDATE transactions SET amount = 10.005 WHERE id = (SELECT MIN(id) FROM transactions)")
    conn.commit()
    conn.close()
    assert run(sqlite_copy) == 0
    assert "precision warning" in capsys.readouterr().out
