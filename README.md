# 💸 ExpenseMate — Personal Expense Manager

A small but complete **Client-Server (local)** software system built from scratch for a
**Software Construction** course (Team 02).

Records income/expenses, sets monthly per-category budgets, and shows visual charts.
Includes the "challenging part": **budget alerts**, **CSV import/export**, and
**category-wise analytics**, plus an optional **multi-currency** feature.

**Stack:** Python 3.11+ · Flask (server/API) · SQLite (stdlib) · Chart.js (client charts) · pytest.

---

## 📁 Project structure

```
ExpenseMate/
├── run.py                      # entry point  ->  python run.py
├── README.md                   # this file
├── requirements.txt            # install deps
├── app/
│   ├── backend/                # SERVER side (Member A)
│   │   ├── server.py           #   REST API + serves client
│   │   ├── logic.py            #   business rules, budgets/alerts, analytics, CSV, currency
│   │   └── db.py               #   persistence (SQLite repositories)
│   └── frontend/               # CLIENT side (Member B)
│       ├── index.html
│       └── static/app.js, style.css
├── tests/                      # unit + integration + system tests (40 tests)
│   ├── conftest.py
│   ├── test_db.py
│   ├── test_logic.py
│   └── test_api.py
├── sample_data/sample_expenses.csv   # ready-to-import sample data
└── docs/                       # all written deliverables
    ├── Phase1_SRS.md
    ├── Phase2_Architecture.md
    ├── Phase3_4_Coding_Test_Report.md
    ├── Phase5_Maintenance_Report.md
    ├── Phase6_Final_Report.md
    ├── make_diagrams.py        # regenerates diagrams (matplotlib)
    └── diagrams/*.png          # use case, 4 views, gantt chart
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

### 2. Start the server (the "Server" process)
```bash
python run.py
```
You should see `Running on http://127.0.0.1:5000` (and `http://0.0.0.0:5000`).

### 3. Open the app (the "Client" in your browser)
Go to **http://localhost:5000** .

1. Click **Register** with a username/password (e.g. `demo` / `demo`), then **Log in**.
2. On the dashboard:
   - **Add Transaction** → pick income/expense, description, amount, category, currency → **Add**.
   - **Set Monthly Budget** → pick a category, enter a limit → **Set**.
     Spend past **80%** → ⚠️ warning alert; past **95%** → 🚨 critical alert (shown on screen).
   - **Charts** update automatically (category doughnut + monthly trend line).
   - **Import CSV** → choose `sample_data/sample_expenses.csv` (or any matching CSV).
   - **Export CSV** → downloads the current month's data.

---

## 🧪 How to run the tests

```bash
python -m pytest -v                     # 40 tests -> 40 passed
python -m pytest --cov=app.backend      # coverage -> 94%
python -m radon cc app/backend -s       # cyclomatic complexity metrics
```

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
```
`type` must be `income` or `expense`. Malformed rows are skipped automatically.
See `sample_data/sample_expenses.csv` for a full example.

---

## ✅ Test & quality summary

| Metric | Value |
|--------|-------|
| Unit/API tests | **40/40 passed** |
| Coverage | **94%** (logic layer 99%) |
| Cyclomatic complexity | avg **2.43** (max 9) |
| LOC / SLOC | 613 / 442 |
| Bugs found & fixed | 3 (fault-fix rate 100%) |

---

## 🗂️ Deliverable map (submission bundle)

| Required deliverable | File(s) |
|----------------------|---------|
| SRS Document | `docs/Phase1_SRS.md` |
| Architecture Diagrams | `docs/Phase2_Architecture.md` + `docs/diagrams/*.png` |
| Source Code (ZIP) | whole repo |
| Test Cases + Results | `docs/Phase3_4_Coding_Test_Report.md` + `tests/` |
| Metrics Report | `docs/Phase3_4_Coding_Test_Report.md` (complexity section) |
| Final Report | `docs/Phase6_Final_Report.md` |

---
**Team 02 · Software Construction · Deadline 18 Sep 2026 · Team Lead submits.**
