# 💸 ExpenseMate — Personal Expense Manager

A small but complete **Client-Server** software system built from scratch for a
**Software Construction** course (Team 02).

Records income/expenses, sets monthly per-category budgets, and shows visual charts.
Includes the "challenging part": **budget alerts**, **CSV import/export**, and
**category-wise analytics** — plus **full multi-currency support** (20 currencies with
conversion-weighted reporting).

**Stack:** Python 3.10+ · Flask (server/API) · SQLite (stdlib) · Chart.js (bundled locally) · pytest.

---

## ✨ Features

| Feature | Detail |
|---|---|
| Accounts | Register / login, SHA-256 hashed passwords, per-user data isolation |
| Records | Income & expense with date, description, amount, category, **currency** |
| Budgets | Monthly per-category limits |
| **Budget alerts** | ⚠️ warning at ≥80%, 🚨 critical at ≥95% — **currency aware** |
| Analytics | Category-wise doughnut chart + 6-month income/expense trend line |
| CSV | Export (native + converted column) and import (malformed rows skipped) |
| **Multi-currency** | **20 currencies**, per-user **base currency** (switchable at runtime), **all analytics converted** via USD pivot, native amounts preserved, rate table + quick converter |
| UI | Sticky **navigation bar** (one tab per feature) with smooth scroll + slide-down reveal; **light theme** — soft blues, white, neutral grays, sage greens |
| Deploy | Local (`run.py`), PaaS (Render/Railway/PythonAnywhere), **Vercel serverless** (`api/index.py`) |

---

## 📁 Project structure

```
ExpenseMate/
├── run.py                      # local entry point  ->  python run.py
├── api/index.py                # Vercel serverless entry point (exposes `app`)
├── vercel.json                 # Vercel build + rewrite config
├── requirements.txt            # install deps
├── .gitignore
├── README.md                   # this file
├── app/
│   ├── backend/                # SERVER side (Member A)
│   │   ├── server.py           #   REST API + serves the client
│   │   ├── logic.py            #   business rules, budgets/alerts, analytics, CSV, MULTI-CURRENCY
│   │   └── db.py               #   persistence (SQLite repositories)
│   └── frontend/               # CLIENT side (Member B)
│       ├── index.html          #   layout + navigation bar + 7 feature sections
│       └── static/
│           ├── app.js          #   controller: charts, nav slide-down, currency, refresh
│           ├── style.css       #   light blue / white / gray / sage-green theme
│           └── chart.umd.min.js#   Chart.js vendored locally (works with no internet)
├── tests/                      # 62 tests: unit + integration + system
│   ├── conftest.py
│   ├── test_db.py              #   11 persistence tests
│   ├── test_logic.py           #   30 business-rule tests (incl. 13 currency)
│   └── test_api.py             #   21 HTTP/API tests (incl. 12 currency)
├── sample_data/sample_expenses.csv   # ready-to-import sample data
└── docs/                       # all written deliverables
    ├── Phase1_SRS.md
    ├── Phase2_Architecture.md
    ├── Phase3_4_Coding_Test_Report.md
    ├── Phase5_Maintenance_Report.md
    ├── Phase6_Final_Report.md
    ├── Deployment_Vercel.md     # step-by-step deploy guide (+ Render/PythonAnywhere)
    ├── make_diagrams.py         # regenerates diagrams (matplotlib)
    └── diagrams/*.png           # use case, 4 views, gantt chart
```

---

## 🚀 How to run (Client + Server)

### 1. Install dependencies
```bash
cd ExpenseMate
pip install flask                # required to run
# optional (for tests / metrics / diagrams):
pip install pytest pytest-cov radon matplotlib
```
> On Windows PowerShell, if bare `pip` is "not recognized", use `py -m pip install flask`.

### 2. Start the server (the "Server" process)
```bash
python run.py
```
You should see `Running on http://127.0.0.1:5000`.

### 3. Open the app (the "Client" in your browser)
Go to **http://localhost:5000**, click **Register** (pick your base currency), then **Log in**.

Use the **navigation bar** to move between features — clicking a tab smoothly scrolls and
slides that section down into view:

- **Dashboard** → income / expense / balance / alert cards + budget alerts.
- **Add Transaction** → type, description, amount, category, date, **currency** → **Add**.
  Also **Set Monthly Budget** (category, amount, **budget currency**) → alerts at 80% / 95%.
- **View Transactions** → history table showing the **native amount** *and* the amount
  **converted to your base currency** (`⇄` marks foreign-currency rows).
- **Analytics & Reports** → doughnut + trend charts; they **redraw on every change**.
- **Budgets & Alerts** → per-category bars, remaining/over amounts, cross-currency notes.
- **Currency** → switch your **base currency** (everything re-converts instantly),
  **quick converter**, **exchange-rate table** (20 currencies), and this month's
  **native totals per currency**.
- **CSV Tools** → export the month / import a CSV file.

### 4. Try multi-currency in 30 seconds
1. Add `5000` in **PKR** and `100` in **USD** (both expenses).
2. Dashboard shows the total in your base currency — e.g. `$118.00`, not `5100`.
3. Open **Currency** → switch base to **PKR** → totals, charts, budgets and alerts all
   re-convert (e.g. `Rs 32,777.78`). Switch back any time.

---

## 🔌 REST API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/register` | Create account (`username`, `password`, optional `base_currency`) |
| POST | `/api/login` | Authenticate → `user_id`, `base_currency`, `base_symbol` |
| GET | `/api/categories` | Category list |
| GET/POST | `/api/transactions` | List (annotated with `amount_base`) / add a record |
| DELETE | `/api/transactions/<id>` | Delete a record |
| GET | `/api/summary?month=YYYY-MM` | Cards, by-category, by-currency, budget status, alerts, trend |
| POST | `/api/budgets` | Set a monthly category budget (any currency) |
| GET | `/api/currencies` | Rate table, symbols, supported codes, current base |
| POST | `/api/convert` | Convert `amount` `from` → `to` |
| GET | `/api/settings` | Current base currency |
| POST | `/api/settings/base_currency` | **Change base currency** (re-converts all analytics) |
| GET | `/api/export?month=` | CSV download (native + `amount_in_<BASE>`) |
| POST | `/api/import` | CSV upload |

Auth for the demo is a simple `X-User-Id` header (or `?uid=`) returned by login.

---

## 🧪 How to run the tests

```bash
python -m pytest -v                     # 62 tests -> 62 passed
python -m pytest --cov=app.backend      # coverage -> 94%
python -m radon cc app/backend -s       # cyclomatic complexity metrics
```

---

## 🌐 How to deploy

**Vercel (serverless):**
```bash
npm install -g vercel
vercel login
cd ExpenseMate
vercel --prod
```
Full step-by-step instructions, env vars, troubleshooting, and the SQLite-persistence
caveat (plus Render / Railway / PythonAnywhere alternatives) are in
**`docs/Deployment_Vercel.md`**.

**Local/PaaS:** `python run.py` honours the injected `$PORT` and disables the debug
console automatically on deployed hosts.

---

## 📐 How to regenerate diagrams

```bash
pip install matplotlib
python docs/make_diagrams.py            # writes PNGs into docs/diagrams/
```

---

## 🧾 CSV format for import

```csv
date,description,amount,type,category,currency
2026-09-01,Weekly groceries,120.50,expense,Groceries,USD
2026-09-05,Karachi chai,2500,expense,Dining,PKR
```
`type` must be `income` or `expense`; `currency` is optional (defaults to your base
currency) and each row may use a different one. Malformed rows are skipped automatically.
See `sample_data/sample_expenses.csv`.

---

## ✅ Test & quality summary

| Metric | Value |
|--------|-------|
| Unit / integration / system tests | **62/62 passed** |
| Coverage | **94%** overall (`logic.py` 97%, `db.py` 97%, `server.py` 89%) |
| Cyclomatic complexity | avg **2.72**, max **10** (grade B) across 46 backend blocks |
| Python LOC / SLOC / comments | 910 / 633 / 91 (+ 736 front-end lines) |
| Currencies supported | **20** |
| Bugs found & fixed | 4 (fault-fix rate 100%, 0 open) |

---

## 🗂️ Deliverable map (submission bundle)

| Required deliverable | File(s) |
|----------------------|---------|
| SRS Document | `docs/Phase1_SRS.md` |
| Architecture Diagrams | `docs/Phase2_Architecture.md` + `docs/diagrams/*.png` |
| Source Code (ZIP) | whole repo |
| Test Cases + Results | `docs/Phase3_4_Coding_Test_Report.md` + `tests/` |
| Metrics Report | `docs/Phase3_4_Coding_Test_Report.md` (complexity section) |
| Maintenance Report | `docs/Phase5_Maintenance_Report.md` |
| Final Report | `docs/Phase6_Final_Report.md` |
| Deployment guide | `docs/Deployment_Vercel.md` |

---
**Team 02 · Software Construction · Deadline 18 Sep 2026 · Team Lead submits.**
