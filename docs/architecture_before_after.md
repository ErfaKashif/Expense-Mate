# Architecture: Before and After

## Before (Assignment 01, tag `assignment-01-baseline`)

```
 Browser (index.html + app.js + Chart.js)
          │ JSON over HTTP + JWT
          ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ server.py   create_app(): 21 route functions in one closure  │
 │   • register/login/categories call db.* DIRECTLY (bypass)    │──────────┐
 │   • calls private logic._normalise()                         │          │
 └──────────────────────┬───────────────────────────────────────┘          │
                        ▼                                                  │
 ┌──────────────────────────────────────────────────────────────┐          │
 │ logic.py   class Logic  (26 methods, ~7 responsibilities)    │          │
 │   currency · users · validation · transactions · analytics  │          │
 │   · budgets & alerts (rules duplicated) · CSV import/export  │          │
 │   add_transaction CC=16, import_csv CC=15                    │          │
 └──────────────────────┬───────────────────────────────────────┘          │
                        ▼                                                  ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ db.py   class Database (21 methods, all 5 tables, schema, connections)   │
 │   one connection per method → no multi-statement transactions            │
 └──────────────────────┬───────────────────────────────────────────────────┘
                        ▼
              SQLite file app/data/expensemate.db
```

The modules were labelled "layers", but the layering was not enforced: the HTTP code called the database directly,
and `Logic` mixed business rules with data coordination.

## After (Assignment 02, branch `assignment-02`)

```
 Browser (UNCHANGED index.html + app.js + Chart.js)
          │ same JSON API
          ▼
 CONTROLLERS  app/backend/controllers/     (HTTP only: parse, basic checks, call service, JSON)
   auth_controller · currency_controller · expense_controller · budget_controller
   error_handlers: ValidationError→400 · Auth→401 · NotFound→404 · Conflict→409 · DB down→503
          │
          ▼
 SERVICES     app/backend/services/        (business rules & calculations, no SQL, no Flask)
   ExpenseService ──► BudgetService ──► BudgetCalculator (pure)
        │  ExpenseValidator (pure)   AnalyticsService
        │  CsvImporter (pure)        UserService · CurrencyService (pure)
          │
          ▼
 REPOSITORIES app/backend/repositories/    (ALL SQL, no business rules)
   ExpenseRepository · BudgetRepository · CategoryRepository · UserRepository
          │
          ▼
 DATABASE     app/backend/database/        (config from env, connections, transactions, schema migrations)
          │
          ▼
 PostgreSQL 16   (expensemate; tests use expensemate_test)

 models/  dataclasses passed between layers     utils/  validators · errors · logger
```

**Dependency direction:** every arrow points downwards. Controllers know only services. Services know
repositories, other services and models. Repositories know only `database` and models. Nothing imports a higher
layer. `server.py` is the single *composition root* that builds the objects and injects them through
constructors. This is a layered architecture, not MVC: there are no view templates or "model controllers", and the
frontend is a separate static client.

## Feature flows

**Feature 1: Add Expense** (`POST /api/transactions`)
```
ExpenseController.add_transaction      require date/amount/type, read JWT user
  → ExpenseService.add_expense
      → UserService.get_user           default currency
      → ExpenseValidator.validate      pure: date, type, amount, currency, description, category name
      → Database.transaction():
          CategoryRepository.get_or_create   INSERT … ON CONFLICT DO NOTHING RETURNING id
          ExpenseRepository.add              INSERT … RETURNING id
      → BudgetService.alert_for_category → BudgetCalculator (same rules as the dashboard)
  ← 201 {"status":"success","id":…, "alert":…}
```

**Feature 2: Monthly Budget Summary** (`GET /api/summary?month=YYYY-MM`, also `GET /api/budgets`)
```
BudgetController.summary               validate month (default: current month)
  → BudgetService.monthly_summary
      → AnalyticsService.category_summary → ExpenseRepository.list_for_user (month range)
      → BudgetRepository.list_for_month   SELECT budgets JOIN categories
      → CurrencyService.convert           limits → base currency
      → BudgetCalculator.evaluate_month   remaining, ratio, level, alerts
      → AnalyticsService.monthly_trend
  ← 200 {totals, by_category, by_currency, budget:{status, alerts}, trend}
```

## Folder structure (actual)

```
Expense-Mate/
├── app/
│   ├── backend/
│   │   ├── controllers/  __init__, _request, auth_, budget_, currency_, expense_controller, error_handlers
│   │   ├── services/     __init__, expense_service, budget_service, budget_calculator, csv_importer,
│   │   │                 analytics_service, currency_service, user_service
│   │   ├── repositories/ __init__, expense_repository, budget_repository, category_repository, user_repository
│   │   ├── database/     __init__, config, connection, schema, migrations/001_initial_schema.sql
│   │   ├── models/       __init__, expense, budget, category, user, _convert
│   │   ├── utils/        __init__, validators, errors, logger
│   │   ├── server.py
│   │   └── __init__.py
│   ├── frontend/         (unchanged) index.html, static/app.js, chart.umd.min.js, style.css
│   ├── data/expensemate.db   (original SQLite, kept read-only as migration source)
│   └── sample_data/sample_expenses.csv
├── tests/  conftest.py, unit/, integration/, regression/
├── migration/  migrate_sqlite_to_postgres.py, README.md
├── docs/   reports + evidence/
├── api/index.py   (serverless entry point)
├── requirements.txt · .env.example · .gitignore · README.md · run.py
```

The folders deviate slightly from the suggested template, for reasons tied to the real code. There are extra
`analytics/currency/user` services and `auth/currency` controllers because Assignment 01 already had those features.
There are `category`/`user` models and repositories because those tables exist. `budget_calculator.py` and
`csv_importer.py` are the rewritten modules.
