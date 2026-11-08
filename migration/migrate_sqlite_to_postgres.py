"""
ExpenseMate: migrate the Assignment 01 SQLite database to PostgreSQL.

Usage (from the project root):

    python migration/migrate_sqlite_to_postgres.py
    python migration/migrate_sqlite_to_postgres.py --sqlite app/data/expensemate.db \
        --target-env DATABASE_URL --report docs/evidence/migration_verification.md
    python migration/migrate_sqlite_to_postgres.py --replace   # re-run on a non-empty target

What it does
  1. Opens the SQLite file READ-ONLY (it is never modified) and records its SHA-256.
  2. Runs SQLite integrity and foreign-key checks.
  3. Reads every row and converts the data types (REAL -> NUMERIC(14,2),
     TEXT dates -> DATE/TIMESTAMP, currency codes -> upper case).
  4. Creates the PostgreSQL schema with the application's own migrations.
  5. Inside ONE PostgreSQL transaction: copies all rows with their original
     primary keys, resets the identity sequences, then VERIFIES the copy
     (row counts, row-by-row comparison, money totals, orphan foreign keys).
  6. COMMITS only if every check passed; otherwise ROLLS BACK so the target
     is left exactly as it was. Exit code 0 = success, 1 = failed, 2 = refused.
"""

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.backend.database import (  # noqa: E402  (path set up above)
    TABLES, ConfigurationError, Database, DatabaseUnavailableError, apply_migrations,
    get_database_url, load_env_file, mask_url,
)

DEFAULT_SQLITE_PATH = os.path.join(PROJECT_ROOT, "app", "data", "expensemate.db")
CENT = Decimal("0.01")

# Column order used for reading, inserting and comparing each table.
COLUMNS = {
    "users": ["id", "username", "password", "base_currency", "created_at"],
    "categories": ["id", "name", "kind"],
    "transactions": ["id", "user_id", "date", "description", "amount", "type",
                     "category_id", "currency", "created_at"],
    "budgets": ["id", "user_id", "category_id", "month", "amount",
                "remaining_amount", "currency"],
    "settings": ["key", "value"],
}
ORDER_BY = {"settings": "key"}          # every other table is ordered by id
IDENTITY_TABLES = ["users", "categories", "transactions", "budgets"]


class MigrationError(Exception):
    """Any problem that must abort the migration."""


# ---------------------------------------------------------------------- #
# Type conversion (SQLite value -> PostgreSQL value)
# ---------------------------------------------------------------------- #
def to_money(value, column, warnings, row_id):
    """REAL -> Decimal with 2 decimal places, warning if precision is lost."""
    if value is None:
        return None
    exact = Decimal(str(value))
    money = exact.quantize(CENT, rounding=ROUND_HALF_UP)
    if money != exact:
        warnings.append(f"{column} of row {row_id}: {value} rounded to {money}")
    return money


def to_date(value, row_id):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise MigrationError(f"transactions row {row_id}: invalid date {value!r}") from exc


def to_timestamp(value, table, row_id):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise MigrationError(f"{table} row {row_id}: invalid timestamp {value!r}") from exc


def convert_row(table, row, warnings):
    """Return the row as a tuple ready for INSERT into PostgreSQL."""
    r = dict(row)
    if table == "users":
        r["base_currency"] = (r["base_currency"] or "USD").upper()
        r["created_at"] = to_timestamp(r["created_at"], table, r["id"])
    elif table == "transactions":
        r["date"] = to_date(r["date"], r["id"])
        r["amount"] = to_money(r["amount"], "transactions.amount", warnings, r["id"])
        r["currency"] = (r["currency"] or "USD").upper()
        r["created_at"] = to_timestamp(r["created_at"], table, r["id"])
    elif table == "budgets":
        r["amount"] = to_money(r["amount"], "budgets.amount", warnings, r["id"])
        r["remaining_amount"] = to_money(r["remaining_amount"], "budgets.remaining_amount",
                                         warnings, r["id"])
        r["currency"] = (r["currency"] or "USD").upper()
    return tuple(r[c] for c in COLUMNS[table])


# ---------------------------------------------------------------------- #
# Source (SQLite)
# ---------------------------------------------------------------------- #
def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def open_sqlite_read_only(path):
    if not os.path.isfile(path):
        raise MigrationError(f"SQLite database not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def preflight_checks(conn):
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise MigrationError(f"SQLite integrity_check failed: {integrity}")
    orphans = conn.execute("PRAGMA foreign_key_check").fetchall()
    if orphans:
        raise MigrationError(f"SQLite has {len(orphans)} rows with broken foreign keys")
    existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = [t for t in TABLES if t not in existing]
    if missing:
        raise MigrationError(f"SQLite database is missing tables: {missing}")


def read_source(conn):
    data = {}
    for table in TABLES:
        cols = ", ".join(COLUMNS[table])
        order = ORDER_BY.get(table, "id")
        data[table] = conn.execute(f"SELECT {cols} FROM {table} ORDER BY {order}").fetchall()
    return data


def source_totals(conn):
    """Independent money totals computed by SQLite itself."""
    rows = conn.execute(
        "SELECT user_id, type, currency, ROUND(SUM(amount), 2) AS total, COUNT(*) AS n "
        "FROM transactions GROUP BY user_id, type, currency ORDER BY 1, 2, 3"
    ).fetchall()
    return [(r["user_id"], r["type"], r["currency"].upper(),
             Decimal(str(r["total"])).quantize(CENT), r["n"]) for r in rows]


# ---------------------------------------------------------------------- #
# Target (PostgreSQL)
# ---------------------------------------------------------------------- #
def target_row_counts(cur):
    counts = {}
    for table in TABLES:
        cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
        counts[table] = cur.fetchone()["n"]
    return counts


def copy_rows(cur, converted):
    for table in TABLES:
        rows = converted[table]
        if not rows:
            continue
        cols = COLUMNS[table]
        placeholders = ", ".join(["%s"] * len(cols))
        cur.executemany(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", rows
        )


def reset_identity_sequences(cur):
    """Make the next generated id = MAX(id) + 1 so new rows never collide."""
    for table in IDENTITY_TABLES:
        cur.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
        )


def comparable(table, row):
    """Normalise a PostgreSQL row so it can be compared with the converted source."""
    return tuple(row[c] for c in COLUMNS[table])


def verify(cur, converted, expected_totals):
    """Return a list of (check, passed, detail). Raises nothing."""
    results = []

    # 1. Row counts
    counts = target_row_counts(cur)
    for table in TABLES:
        ok = counts[table] == len(converted[table])
        results.append((f"row count: {table}", ok,
                        f"SQLite={len(converted[table])} PostgreSQL={counts[table]}"))

    # 2. Row-by-row comparison of every column
    for table in TABLES:
        cols = ", ".join(COLUMNS[table])
        cur.execute(f"SELECT {cols} FROM {table} ORDER BY {ORDER_BY.get(table, 'id')}")
        target = [comparable(table, r) for r in cur.fetchall()]
        mismatches = [i for i, (a, b) in enumerate(zip(converted[table], target)) if a != b]
        ok = not mismatches and len(target) == len(converted[table])
        detail = "all rows identical" if ok else f"{len(mismatches)} rows differ, e.g. #{mismatches[:3]}"
        results.append((f"row-by-row: {table}", ok, detail))

    # 3. Money totals per user / type / currency
    cur.execute(
        "SELECT user_id, type, currency, SUM(amount) AS total, COUNT(*) AS n "
        "FROM transactions GROUP BY user_id, type, currency ORDER BY 1, 2, 3"
    )
    actual_totals = [(r["user_id"], r["type"], r["currency"], r["total"], r["n"])
                     for r in cur.fetchall()]
    results.append(("money totals per user/type/currency", actual_totals == expected_totals,
                    f"{len(actual_totals)} groups compared"))

    # 4. Foreign keys really point at existing rows (constraints are enforced,
    #    this is an explicit second check for the report)
    cur.execute(
        """SELECT
             (SELECT COUNT(*) FROM transactions t LEFT JOIN users u ON u.id = t.user_id
               WHERE u.id IS NULL) +
             (SELECT COUNT(*) FROM transactions t LEFT JOIN categories c ON c.id = t.category_id
               WHERE t.category_id IS NOT NULL AND c.id IS NULL) +
             (SELECT COUNT(*) FROM budgets b LEFT JOIN users u ON u.id = b.user_id
               WHERE u.id IS NULL) +
             (SELECT COUNT(*) FROM budgets b LEFT JOIN categories c ON c.id = b.category_id
               WHERE c.id IS NULL) AS orphans"""
    )
    orphans = cur.fetchone()["orphans"]
    results.append(("orphan foreign keys", orphans == 0, f"{orphans} orphan rows"))

    # 5. Identity sequences continue after the migrated ids
    for table in IDENTITY_TABLES:
        cur.execute(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table}")
        max_id = cur.fetchone()["max_id"]
        cur.execute(f"SELECT last_value, is_called FROM "
                    f"{_sequence_name(cur, table)}")
        seq = cur.fetchone()
        next_id = seq["last_value"] + 1 if seq["is_called"] else seq["last_value"]
        results.append((f"next id: {table}", next_id > max_id,
                        f"max id={max_id}, next generated id={next_id}"))
    return results


def _sequence_name(cur, table):
    cur.execute("SELECT pg_get_serial_sequence(%s, 'id') AS seq", (table,))
    return cur.fetchone()["seq"]


# ---------------------------------------------------------------------- #
# Report
# ---------------------------------------------------------------------- #
def write_report(path, lines):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def run(args):
    report = ["# ExpenseMate migration verification", "",
              f"Run at: {datetime.now().isoformat(timespec='seconds')}", ""]

    def say(line=""):
        print(line)
        report.append(line)

    load_env_file()
    target_url = get_database_url(args.target_env)
    sqlite_path = os.path.abspath(args.sqlite)
    say(f"- Source (SQLite, read-only): `{os.path.relpath(sqlite_path, PROJECT_ROOT)}`")
    say(f"- Target (PostgreSQL): `{mask_url(target_url)}`")

    source = open_sqlite_read_only(sqlite_path)       # fails cleanly if missing
    checksum_before = sha256_of(sqlite_path)
    try:
        preflight_checks(source)
        say("- SQLite integrity_check: ok; foreign_key_check: no violations")
        raw = read_source(source)
        expected_totals = source_totals(source)
    finally:
        source.close()

    warnings = []
    converted = {t: [convert_row(t, row, warnings) for row in raw[t]] for t in TABLES}
    say("- Rows read: " + ", ".join(f"{t}={len(converted[t])}" for t in TABLES))
    for w in warnings:
        say(f"  - precision warning: {w}")

    database = Database(target_url)
    applied = apply_migrations(database)
    say(f"- PostgreSQL schema migrations applied now: {applied or 'none (already up to date)'}")

    try:
        with database.transaction():
            with database.cursor() as cur:
                existing = target_row_counts(cur)
                if any(existing.values()):
                    if not args.replace:
                        raise RefusedError(
                            f"Target already contains data {existing}. Re-run with --replace "
                            f"to overwrite the PostgreSQL copy (SQLite is never touched).")
                    cur.execute("TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")
                    say(f"- --replace: cleared existing PostgreSQL rows {existing}")

                copy_rows(cur, converted)
                reset_identity_sequences(cur)
                results = verify(cur, converted, expected_totals)

                say("")
                say("| Check | Result | Detail |")
                say("|---|---|---|")
                for name, ok, detail in results:
                    say(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
                failed = [r for r in results if not r[1]]
                if failed:
                    raise MigrationError(f"{len(failed)} verification checks failed")
    except RefusedError as exc:
        say(f"\nREFUSED: {exc}")
        return 2, report
    except Exception as exc:  # noqa: BLE001 - any failure => rollback + report
        say(f"\nFAILED and ROLLED BACK (PostgreSQL unchanged): {exc}")
        return 1, report

    checksum_after = sha256_of(sqlite_path)
    say("")
    say(f"- SQLite SHA-256 before: `{checksum_before}`")
    say(f"- SQLite SHA-256 after:  `{checksum_after}`")
    if checksum_before != checksum_after:
        say("- WARNING: SQLite file changed during migration!")
        return 1, report
    say("- Original SQLite file unchanged.")
    say("\nRESULT: MIGRATION COMMITTED - all verification checks passed.")
    return 0, report


class RefusedError(Exception):
    """Target is not empty and --replace was not given."""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Migrate ExpenseMate SQLite data to PostgreSQL.")
    parser.add_argument("--sqlite", default=DEFAULT_SQLITE_PATH, help="path to the SQLite .db file")
    parser.add_argument("--target-env", default="DATABASE_URL",
                        help="name of the environment variable holding the PostgreSQL URL")
    parser.add_argument("--replace", action="store_true",
                        help="clear the PostgreSQL tables first if they already contain data")
    parser.add_argument("--report", help="also write the verification report (Markdown) to this path")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        code, report = run(args)
    except (ConfigurationError, MigrationError, DatabaseUnavailableError) as exc:
        print(f"ERROR: {exc}")
        return 1
    if args.report:
        write_report(args.report, report)
        print(f"\nReport written to {args.report}")
    return code


if __name__ == "__main__":
    sys.exit(main())
