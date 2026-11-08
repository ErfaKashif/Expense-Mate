# Refactoring Report: Layered Architecture

**Owner:** 24K-3037 Daneya Shafiq (layers, services, controllers) with 24K-3010 Erfa Kashif (repositories, database)
**Commit:** `5b0e345 refactor: restructure backend into Controller -> Service -> Repository -> Database`

## 1. Old architecture

Assignment 01 had three backend modules: `server.py` (Flask routes), `logic.py` (`class Logic`) and `db.py`
(`class Database`). The docstrings described them as layers, but the code did not respect that:

- `server.py` route handlers called the database directly in 4 places (`db.get_user_by_name`, `db.create_user`
  and `db.list_categories` in register/login/categories). They also called the *private* `logic._normalise()`
  in 3 places.
- `Logic` was a god class: 26 methods spanning currency conversion, users, validation, transactions, analytics,
  budgets/alerts and CSV.
- `Database` held SQL for all five tables plus the schema and connection handling. Each method committed alone.
- Route handlers had no error handling for invalid expenses or budgets, so bad input produced **HTTP 500**
  (verified on the baseline: `docs/evidence` probe results in the rewriting report).

Diagrams for both versions are in `architecture_before_after.md`.

## 2. New architecture: Controller → Service → Repository → Database

| Layer | Package | Responsibility | Must not contain |
|---|---|---|---|
| Controller | `controllers/` | Read the request, basic checks (`json_body`, `require_fields`), call one service, return JSON; central error handlers | SQL, calculations |
| Service | `services/` | Business rules, calculations, coordination, transaction boundaries | SQL, Flask |
| Repository | `repositories/` | Parameterised SQL, row-to-model mapping | Business rules |
| Database | `database/` | Config from env, connections, `transaction()`, schema migrations | Business rules |

These rules are checked mechanically: a grep shows no SQL keyword or `cursor()` call in `controllers/` or
`services/`, and no `flask`/`psycopg` import in `services/`. `tests/unit/test_repositories.py` also asserts that
repository modules contain no budget-rule constants.

## 3. The two refactored features

**Feature 1: Add Expense.** `ExpenseController.add_transaction → ExpenseService.add_expense →
ExpenseRepository.add → PostgreSQL`. The controller checks required fields and the JWT user. The service
validates, sets the default currency and category, and runs the category lookup and the insert in **one
transaction**. The repository runs `INSERT … RETURNING id`.

**Feature 2: Monthly Budget Summary.** `BudgetController.summary → BudgetService.monthly_summary →
BudgetRepository.list_for_month → PostgreSQL`. The controller validates `?month=`. The service gathers the
spending (via `AnalyticsService`) and the budgets, converts currencies, and delegates the rules to
`BudgetCalculator`. A new read-only endpoint, `GET /api/budgets?month=`, exposes just the budget status.

The JSON response shapes are unchanged, so `app/frontend` was **not modified**. This was confirmed by the 27
original API tests and a Playwright run of the real page with no JS errors.

## 4. Dependency direction and injection

`server.py:build_services()` builds the repositories with the `Database`, the services with the repositories, and
the controllers (blueprint factories) with the services. Nothing creates its own dependencies. As a result, every
unit test can pass in a `MagicMock` instead: controllers with mocked services, services with mocked repositories,
and repositories with a fake cursor.

## 5. Code-quality improvements (with evidence)

1. **Single responsibility.** The largest class shrank from 26 methods (`Logic`) to 8 (`ExpenseService`). The
   worst cyclomatic complexity fell from 16 to 9 and the lowest file maintainability index rose from 35.6 to 60.4
   (`maintainability_comparison.md`).
2. **No layer bypasses.** Direct data-access calls from route handlers went from 4 to 0, and calls to private
   service methods from controllers went from 3 to 0 (`CurrencyService.normalise` is now public).
3. **Consistent error handling.** One `register_error_handlers()` maps typed exceptions to 400/401/404/409/503
   and logs real DB errors without exposing SQL. Invalid expenses and budgets now return 400 instead of 500.
4. **Correct authorisation.** Assignment 01 let any logged-in user delete *any* transaction by id, and missing ids
   returned "ok". The repository now deletes `WHERE id = %s AND user_id = %s` and the controller returns 404
   (`test_users_cannot_delete_each_others_transactions`).
5. **Atomic operations.** `Database.transaction()` groups several repository calls. A CSV import is now
   all-or-nothing on DB failure (tested).
6. **Testability.** There are 106 unit tests that run in about 0.2 s with no database. The original suite could
   only run with a real DB file.
7. **Configuration.** Credentials and the JWT secret come from env/.env. Debug mode is off unless
   `FLASK_DEBUG=1`. Assignment 01 always ran with `debug=True`.

## 6. Behaviour intentionally changed (documented, all tested)

| Situation | Assignment 01 | Assignment 02 |
|---|---|---|
| Invalid expense (e.g. amount −5) | HTTP 500 | 400 + message |
| Budget without category | HTTP 500 | 400 |
| Delete someone else's / missing transaction | 200, deleted / "ok" | 404, nothing deleted |
| Month `2026-13` | accepted | 400 |
| Unknown user id in a service call | `ValidationError` | `NotFoundError` (404) |
| Unused code removed | `Database.delete_budget`, `get_budget_remaining_amount`, `Logic._convert`, `Logic.is_supported` | n/a (no callers) |
