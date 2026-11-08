# ExpenseMate: Software Evolution (Migration, Refactoring & Rewriting)

**Software Construction & Development · Assignment 02 · Section SE-5B**

| Roll no. | Name | Section |
|---|---|---|
| 24K-3010 | Erfa Kashif | SE-5B |
| 24K-3037 | Daneya Shafiq | SE-5B |

Repository branch: `assignment-02` · Baseline preserved as tag `assignment-01-baseline` and branch `assignment-01`.

## 1. Introduction

ExpenseMate is a personal expense manager. A user registers (JWT login), records income and expenses in any of
20 currencies, sets monthly budgets per category, receives warning (80%) and critical (95%) alerts, sees
category-wise and monthly-trend charts (Chart.js), converts currencies, and imports or exports CSV files.
Assignment 01 delivered this with Flask, SQLite and an HTML/CSS/JS frontend.

Assignment 02 evolves the *same* application in three ways. It migrates the database to PostgreSQL, refactors the
backend into a Controller → Service → Repository → Database architecture, and rewrites the two worst modules. The
frontend was not changed at all: the API contract was kept, and this was checked by the original tests and a
browser run.

## 2. Migration (details: `migration_report.md`)

SQLite was replaced by PostgreSQL 16 using the psycopg 3 driver. Credentials come from `DATABASE_URL` /
`TEST_DATABASE_URL` (a `.env` file that is git-ignored; `.env.example` is provided). The schema is versioned SQL
(`database/migrations/001_initial_schema.sql`) applied automatically and idempotently at start-up. Type changes
include `REAL` → `NUMERIC(14,2)` for exact money, `TEXT` → `DATE`/`TIMESTAMP`, identity keys, all foreign keys
and checks, plus a month check and a `(user_id, date)` index.

`migration/migrate_sqlite_to_postgres.py` is repeatable and safe. It opens SQLite read-only (checksum unchanged),
copies every row with its original id inside one transaction, resets the sequences, and verifies the copy (counts,
row-by-row comparison, money totals, orphan FKs, next ids). It commits only if every check passes, refuses to
overwrite existing data without `--replace`, and rolls back on any error. On the real data (2 users,
11 categories, 12 transactions, 3 budgets) **16/16 checks passed**.

## 3. Refactoring (details: `refactoring_report.md`, `architecture_before_after.md`)

The old `server.py` → `Logic` → `Database` modules only *claimed* to be layers. Route handlers called the database
directly (4 places) and called private logic methods (3 places), and `Logic` had 26 methods covering about
7 responsibilities. The new backend has:

- **controllers/**: four Flask blueprints that only parse input, perform basic checks, call one service and return
  JSON, plus central error handlers (400/401/404/409/500/503);
- **services/**: business rules (expense, budget, analytics, user, currency), with no SQL and no Flask;
- **repositories/**: all SQL, parameterised, one class per table;
- **database/**: configuration, connections, a shared-connection `transaction()` and schema migrations.

`server.py` is the composition root that injects every dependency. Feature 1 (**Add Expense**) flows
`ExpenseController → ExpenseService → ExpenseRepository → PostgreSQL`. Feature 2 (**Monthly Budget Summary**) flows
`BudgetController → BudgetService → BudgetRepository → PostgreSQL`. The new boundaries fixed real bugs: invalid
input returned HTTP 500, and any logged-in user could delete any other user's transaction.

## 4. Rewriting (details: `rewriting_report.md`)

Assignment 01 contained only two classes (`Logic`, `Database`), so we rewrote two **modules within them**:

1. **Budget calculation module** (`Logic.budget_status`, `Logic.set_budget`, the budget branches of
   `Logic.add_transaction`/`delete_transaction`, and `Database.get_single_budget`/`update_budget_remaining`/
   `get_budget_remaining_amount`). It became `BudgetCalculator`, a pure class whose remaining budget is
   *calculated* from transactions instead of a stored running balance. The stored balance was wrong for 2 of the
   3 budgets in the real data. The new class removes the duplicated threshold logic and makes the add-expense
   alert agree with the dashboard.
2. **Expense management module** (`Logic.add_transaction` CC 16, `Logic.import_csv` CC 15,
   `Logic._validate_amount`/`_validate_date`, `Logic.delete_transaction`). It became the pure `ExpenseValidator`
   and `CsvImporter` plus a coordinating `ExpenseService`. CSV import is now atomic, short rows no longer crash,
   and one category-name rule applies to expenses and budgets.

Five defects were confirmed by running the baseline and fixed (`evidence/defect_probes.md`).

## 5. Testing and regression

All tests were executed. **225 passed, 0 failed** (`evidence/test_results.txt`). Coverage of `app/backend`
is 97%.

| Suite | Tests | Database | What it shows |
|---|---|---|---|
| `tests/unit` | 106 | none (mocks) | Rewritten classes; expense, budget, user and currency services with mocked repositories; repositories with a fake cursor; connection manager with mocked psycopg; controllers with mocked services |
| `tests/integration` | 34 | PostgreSQL test DB | The 5 required flows (store expense, retrieve, budget + summary, remaining after add/delete, category summary), sample CSV import, atomic import on DB failure, invalid inputs → 400, cross-user delete → 404, DB down → 503, constraints, migration script end to end |
| `tests/regression` | 85 | PostgreSQL test DB | All 73 Assignment 01 tests re-run on the new backend, plus 12 feature tests (add/view expenses, income, budgets, category summaries, chart data, CSV import/export, currency, frontend assets) |

Tests use only `TEST_DATABASE_URL`, empty the tables before each test, and refuse to run against a database whose
name lacks "test" or equals `DATABASE_URL`. Without a test database, the 119 DB tests are *skipped*, not failed.

All 73 original tests pass. Their requests, inputs and expected values were kept. What changed: the fixtures (a
SQLite temp file became the PostgreSQL test DB), the call targets (old `Logic`/`Database` method names are mapped
onto the new services and repositories), and the expected exception type for a duplicate username
(`sqlite3.IntegrityError` became `psycopg.errors.UniqueViolation`). In addition, **six tests contain a deliberate
change, each marked `A02`** in the code:

- the "invalid amount" test previously accepted an HTTP 500 and now requires 400;
- an unknown user now raises `NotFoundError`;
- the `Logic._convert` alias was removed;
- the schema check reads `schema_migrations`;
- deleting a transaction now requires the owner id;
- the stored `remaining_amount` column is no longer written.

The real frontend was also driven with Playwright against a migrated copy of the data: register, budget, two
expenses (critical alert pop-up at 96%), income, sample CSV import (15/15) and month switch, with **no JS errors**.
Screenshots are in `evidence/screenshots/`. CI (GitHub Actions) now starts a PostgreSQL service. It has **not been
run on GitHub yet**, because the branch has not been pushed.

## 6. Maintainability metrics (details: `maintainability_comparison.md`)

| Indicator (radon / grep / pytest) | Before | After |
|---|---|---|
| Highest method CC | 16 | 9 |
| Methods with CC ≥ 6 | 4 | 1 |
| Lowest file maintainability index | 35.6 | 60.4 |
| Largest class (methods) | 26 | 8 |
| Direct data-access calls from route handlers | 4 | 0 |
| SQL outside repository/database layer | 0 | 0 (unchanged) |
| Tests / backend coverage | 73 / 93% | 225 / 97% |
| SLOC of backend | 772 | 1129 (worse) |

## 7. Team contributions

| Member | Area of ownership (agreed division) |
|---|---|
| **24K-3010 Erfa Kashif** | PostgreSQL migration and script, database configuration (`database/`), repositories, `.env.example`, database/repository/migration tests, migration report |
| **24K-3037 Daneya Shafiq** | Layered architecture integration, services and controllers, rewriting of the budget and expense modules, frontend compatibility checks, regression tests, refactoring/rewriting/final reports |
| Both | Test review, regression run, metrics review, viva preparation |

**Accuracy note:** the code, tests and reports in this branch were produced with an AI coding assistant
(Claude Code) working on the team's repository, following the division above. Before submission, each member
should review the commits in their area, re-run the tests, and edit this table if the real division of work
differed. The commits currently carry the assistant's Git identity, not the team members' identities.

## 8. Challenges, trade-offs and lessons learned

- **Behaviour preservation vs fixing bugs.** We kept the API shapes byte-compatible so the frontend did not need to
  change, but deliberately changed buggy behaviour (500 → 400, cross-user delete → 404). Each change is listed in
  the refactoring report and pinned by a test.
- **Stored vs calculated values.** Calculating "remaining" re-reads the month's transactions on every request.
  That is slightly more work for the database, but there is one source of truth. At personal-finance scale this is
  negligible, and the `(user_id, date)` index supports it.
- **Legacy data.** We migrated data exactly, including inconsistencies (`'food'` and `'Food'`, a username with a
  trailing space, drifted balances), rather than "cleaning" it silently. Cleaning would be a separate,
  user-approved step.
- **Floats vs Decimal.** The database stores exact `NUMERIC` values, but services still calculate with `float`, to
  keep Assignment 01's results identical. A full switch to `Decimal` arithmetic is future work.
- **More files.** SLOC grew by 46%. Smaller units are easier to test and change, but newcomers need the
  architecture diagram.
- **Lesson:** measure before changing. Running the baseline exposed five real defects and the corrupted balances.
  Without that evidence, the rewrite would have been a matter of taste.
