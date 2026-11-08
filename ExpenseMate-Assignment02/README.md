# ExpenseMate: Personal Expense Manager

Track income and expenses in 20 currencies, set monthly budgets with alerts, view category and trend charts, and
import or export CSV files.

**Assignment 02 (SCD, SE-5B):** 24K-3010 Erfa Kashif · 24K-3037 Daneya Shafiq
**Stack:** Python 3.10+ · Flask · PostgreSQL 16 (psycopg 3) · HTML/CSS/JavaScript + Chart.js

```
Browser → controllers/ → services/ → repositories/ → database/ → PostgreSQL
```

## 1. Install

```bash
git clone https://github.com/ErfaKashif/Expense-Mate.git
```

```bash
cd Expense-Mate && git checkout assignment-02
```

```bash
python -m venv .venv && source .venv/bin/activate
```

On Windows, activate with `.venv\Scripts\activate`.

```bash
pip install -r requirements.txt
```

## 2. Create the PostgreSQL databases (once)

Open a PostgreSQL shell (`sudo -u postgres psql` on Linux, or pgAdmin's Query Tool on Windows/macOS) and run:

```sql
CREATE ROLE expensemate LOGIN PASSWORD 'choose-a-password';
CREATE DATABASE expensemate      OWNER expensemate;
CREATE DATABASE expensemate_test OWNER expensemate;
```

## 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and put your password into `DATABASE_URL` and `TEST_DATABASE_URL`. Also set a long random
`JWT_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

`.env` is git-ignored. Never commit it.

## 4. Migrate the Assignment 01 SQLite data (once)

```bash
python migration/migrate_sqlite_to_postgres.py --report docs/evidence/migration_verification.md
```

The script copies `app/data/expensemate.db` into PostgreSQL, verifies the copy, and leaves the SQLite file
untouched. Exit code 0 means all checks passed. See `migration/README.md`. You can skip this step to start with an
empty database: the schema is created automatically.

## 5. Run

```bash
python run.py
```

Open <http://localhost:5000>. Use `FLASK_DEBUG=1 python run.py` for auto-reload during development. If PostgreSQL
is not reachable or `DATABASE_URL` is missing, the app exits with a clear message.

## 6. Test

```bash
pytest
```

```bash
pytest tests/unit
```

```bash
pytest --cov=app/backend --cov-report=term-missing
```

- `tests/unit`: 106 tests, no database needed (mocks).
- `tests/integration`: 34 tests, and `tests/regression`: 85 tests. These use **`TEST_DATABASE_URL` only**. They
  empty its tables before every test and refuse to run if its name does not contain "test" or if it equals
  `DATABASE_URL`. Without a test database they are skipped.

Last full run: **225 passed, 0 failed, 97% backend coverage** (`docs/evidence/test_results.txt`).

## 7. Project layout

```
app/backend/controllers/   HTTP routes (Flask blueprints) + error handlers
app/backend/services/      business rules: expense, budget (+ BudgetCalculator), analytics, user, currency, CSV
app/backend/repositories/  all SQL (one class per table)
app/backend/database/      config from env, connections/transactions, schema migrations
app/backend/models/        dataclasses passed between layers
app/backend/utils/         validators, errors, logging
app/frontend/              unchanged Assignment 01 UI
migration/                 SQLite → PostgreSQL migration script
tests/                     unit / integration / regression
docs/                      reports and evidence
```

## 8. API (unchanged from Assignment 01, plus `GET /api/budgets`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/register`, `/api/login` | n/a | Create account / log in → JWT |
| GET | `/api/categories`, `/api/currencies` | optional | Lists, rates table |
| POST | `/api/convert` | n/a | Currency converter |
| GET/POST | `/api/settings`, `/api/settings/base_currency` | JWT | Reporting currency |
| GET/POST | `/api/transactions` | JWT | List (`?month=YYYY-MM`) / add income or expense |
| DELETE | `/api/transactions/<id>` | JWT | Delete your own record (404 otherwise) |
| GET | `/api/summary?month=` | JWT | Dashboard: totals, category summary, budgets, alerts, trend |
| GET/POST | `/api/budgets` | JWT | Budget status for a month / set a budget |
| DELETE | `/api/budgets/by-category` | JWT | Remove a budget |
| GET/POST | `/api/export`, `/api/import` | JWT | CSV download / upload |

## 9. Reports

`docs/final_report.md` · `docs/migration_report.md` · `docs/refactoring_report.md` · `docs/rewriting_report.md` ·
`docs/architecture_before_after.md` · `docs/maintainability_comparison.md` · `docs/change_log.md` ·
`docs/evidence/` (migration verification, test run, metrics, defect probes, screenshots)

## 10. Unfinished work / manual configuration

- **PostgreSQL must be installed and the role/databases created manually** (step 2), and `.env` must be filled in.
- **Passwords are still unsalted SHA-256**, kept so migrated Assignment 01 accounts can still log in. Upgrade to
  `werkzeug.security` hashing with re-hash-on-login.
- Money is stored as exact `NUMERIC`, but services still calculate with `float`, to match Assignment 01 results.
- No connection pool: each request/transaction opens one connection. Add `psycopg_pool` for production.
- Legacy data is migrated as-is: duplicate-case categories (`food`/`Food`) and the unused legacy column
  `budgets.remaining_amount` are kept.
- The GitHub Actions workflow was updated for PostgreSQL but has not yet run on GitHub (the branch must be pushed).
- `python run.py` uses Flask's development server. Use a WSGI server (e.g. gunicorn) to deploy.
