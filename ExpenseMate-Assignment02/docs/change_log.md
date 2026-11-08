# Change Log: Assignment 02

Baseline: tag **`assignment-01-baseline`** (and branch `assignment-01`) → commit `390ed18` (2026-11-05). Neither is
modified. All Assignment 02 work is on branch **`assignment-02`**.

"Responsible" shows the team member who **owns** that area for review and the viva, following the agreed division.
The implementation in this branch was produced with the help of an AI coding assistant (Claude Code). Each owner
must review their commits and be able to explain them (see "Team contributions" in `final_report.md`).

| Version / commit | Date | Files / classes affected | Change performed | Reason | Responsible |
|---|---|---|---|---|---|
| `390ed18` (tag `assignment-01-baseline`) | 2026-11-05 | whole project | Assignment 01 final state (SQLite) | Preserved baseline | Erfa Kashif, Daneya Shafiq |
| `6093473` | 2026-11-07 | `.gitignore`, `app/backend/__pycache__/*`, `tests/__pycache__/*` | Stopped tracking compiled `.pyc` files; ignore `.env`, coverage output, virtualenvs | Bytecode changed on every test run; keep secrets out of Git | Erfa Kashif |
| `84e03b2` | 2026-11-07 | `app/backend/database/{config,connection,schema}.py`, `migrations/001_initial_schema.sql`, `utils/logger.py`, `migration/migrate_sqlite_to_postgres.py`, `migration/README.md`, `.env.example`, `requirements.txt`, `docs/evidence/migration_verification.md` | PostgreSQL configuration from env, connection + transaction manager, versioned schema, verified migration script (16/16 checks passed on real data); added psycopg, removed unused matplotlib | Part A: SQLite → PostgreSQL | Erfa Kashif |
| `5b0e345` | 2026-11-07 | **removed** `db.py` (`Database`), `logic.py` (`Logic`); **new** `controllers/*`, `services/{currency,user,analytics,expense,budget}_service.py`, `repositories/*`, `models/*`, `utils/{errors,validators}.py`; rewritten `server.py`, `run.py`, `api/index.py`; tests moved to `tests/regression/` | Controller → Service → Repository → Database; dependency injection; central error handling (400/404/409/503); owner-scoped delete | Part B: layered architecture; fix HTTP 500s and cross-user delete | Daneya Shafiq (controllers, services), Erfa Kashif (repositories) |
| `eb51cab` | 2026-11-07 | `sample_data/` → `app/sample_data/` | Moved folder | Part D target structure | Daneya Shafiq |
| `67d627d` | 2026-11-07 | **new** `services/budget_calculator.py` (`BudgetCalculator`, `BudgetThresholds`), `services/csv_importer.py` (`CsvImporter`), `utils/validators.py` (`ExpenseValidator`, `normalise_category`), `models/budget.py` (`BudgetStatus`, `BudgetAlert`); rewritten `ExpenseService`, `BudgetService`; `BudgetRepository` (2 methods removed) | Remaining budget calculated instead of stored; one rule set for alerts; pure validator/CSV parser; atomic CSV import; one category-name rule | Part C: rewrite budget-calculation and expense-management modules (5 confirmed defects) | Daneya Shafiq |
| `8c8c277` | 2026-11-07 | `tests/unit/*` (8 files), `tests/integration/*` (3 files), `tests/regression/test_assignment01_features.py`, `tests/conftest.py`, `.github/workflows/python-tests.yml` | 225 tests on a separate PostgreSQL test DB with safety guard; CI with a postgres:16 service | Part E: testing | Erfa Kashif (DB/repository/migration tests), Daneya Shafiq (service/controller/regression tests) |
| `c47ac09` | 2026-11-07 | `services/csv_importer.py`; `docs/evidence/*` | Split `CsvImporter.parse` (CC 11 → 5); added metrics, screenshots, data-drift evidence | Part F finding; evidence | Daneya Shafiq |
| `165394f` | 2026-11-07 | `docs/*.md`, `README.md` | Migration, refactoring, rewriting, architecture, maintainability and final reports; README | Part H | Daneya Shafiq (reports), Erfa Kashif (migration report) |
| Word report commit | 2026-11-07 | `docs/ExpenseMate_Assignment02_Report.docx` (+ `.pdf`), `docs/maintainability_comparison.md`, `docs/change_log.md` | Combined Word report (cover, contents, final report, appendices A–H, screenshots); fixed a Markdown table that split on `\|` | Submission document | Daneya Shafiq |
