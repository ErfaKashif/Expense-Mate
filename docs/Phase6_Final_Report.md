# ExpenseMate — Final Project Report
*Software Construction · Team 02 · ~3 pages · v1.0 · 04 Sep 2026*

---

## 1. Project Overview

**ExpenseMate** is a complete, small software system built from scratch that lets a
single user **record income/expenses**, **set monthly budgets**, and **view visual
charts**. It was developed to exercise every stage of the Software Construction
lifecycle — Requirements → Design → Construction → Testing → Maintenance — by a 2-member
team (Members A & B; Team Lead submits).

**Delivered features**
* User register/login (hashed passwords), income & expense records.
* Monthly per-category **budgets** with automatic **budget alerts** (≥80% warning, ≥95% critical).
* **Category-wise analytics** + doughnut chart, **monthly trend** line chart.
* **CSV import/export** (malformed rows skipped safely).
* **Multi-currency** labels (USD, PKR, EUR, GBP, INR, AED, SAR) — an adaptive feature.

---

## 2. Approach & Design

We chose the **Layered (multitier) Client/Server** architectural style:

```
Browser (Client) → HTTP/REST → Flask Server → Business Logic → SQLite
```

This gave clear single-responsibility modules that could be unit-tested in isolation
and then integrated. The four views (logical/process/physical/deployment) and a 7-week
Gantt plan (Phase 1→6) are in `docs/diagrams/` and `docs/Phase2_Architecture.md`.

**Module ownership:** Member A built the **backend** (server + logic + db, `run.py`);
Member B built the **frontend/client** (`index.html`, `app.js`, `style.css`) plus each
member tested their own module. `Logic` receives the DB by injection (dependency
inversion), which is what made the system so testable and easy to evolve.

---

## 3. Construction & Testing

**Source layout**

```
ExpenseMate/
├── run.py                      # entry point
├── app/
│   ├── backend/                # server.py, logic.py, db.py
│   └── frontend/               # index.html, static/app.js, static/style.css
├── tests/                      # test_db, test_logic, test_api
├── sample_data/sample_expenses.csv
└── docs/                       # SRS, architecture, reports, diagrams
```

**Testing results**

| Level | Cases | Result |
|-------|-------|--------|
| Unit (db) | 11 | ✅ pass |
| Unit (logic) | 21 | ✅ pass |
| Integration & system (API) | 8 | ✅ pass |
| **Total** | **40** | **100% pass** · **94% code coverage** |

**Complexity (cyclomatic, via `radon`):** LOC 613, SLOC 442, 37 functions, avg CC **2.43**,
max CC **9** (all within acceptable limits). **Fault-find/fix:** 3 defects found & fixed,
**fault-fix rate 100%**, 0 open defects.

---

## 4. Maintenance & Evolution

Following Lehman's Laws, we kept the system alive:
* **Adaptive** — added multi-currency (`_convert()` rate table + UI selector).
* **Corrective** — fixed 3 defects (duplicate-username 409, CSV import resilience, `None` category export).
* **Perfective** — refactored `logic.py`, centralised validation via `ValidationError`, added docstrings.

All changes were localised because of the layer separation, and the full 40-test suite
re-ran green after maintenance — confirming non-disruptive evolution.

---

## 5. How to Run (for demo / grading)

**Prerequisites:** Python 3.11+.

```bash
cd ExpenseMate
pip install flask            # only external dependency
pip install pytest pytest-cov radon   # optional: run tests / metrics
python run.py                # starts server on http://localhost:5000
```

Then open **http://localhost:5000**, register a user, log in, and use the dashboard:
add transactions, set budgets (watch the alerts trigger at 80%/95%), view charts, and
export/import CSV. Sample data to import: `sample_data/sample_expenses.csv`.

**Run the tests:**
```bash
python -m pytest -v          # 40 tests
python -m pytest --cov=app.backend    # coverage report (94%)
python -m radon cc app/backend -s    # complexity metrics
```

**Regenerate diagrams:** `python docs/make_diagrams.py` (matplotlib only).

---

## 6. Evaluation Against Requirements

| Requirement | Status |
|-------------|--------|
| Client-Server (local) architecture, Python + SQLite | ✅ |
| Income/expense records | ✅ |
| Monthly budgets | ✅ |
| **Budget alerts** (challenging part) | ✅ |
| **CSV import/export** (challenging part) | ✅ |
| **Category-wise analytics + charts** (challenging part) | ✅ |
| Multi-currency & future cloud backup | ✅ (multi-currency) / O (backup: future) |
| Full lifecycle deliverables | ✅ (6 phases bundled) |

### 6.1 Limitations & Future Work
* CSV import is **best-effort** — duplicate rows aren't de-duplicated.
* Currency reporting sums **native** amounts (conversion offered but not forced); a
  single-currency dashboard is a future enhancement.
* Cloud backup, multiple wallets, and live FX rates remain out of scope.

---

## 7. Conclusion & Lessons Learned

ExpenseMate demonstrates how a small but complete system can be built and maintained
using disciplined software construction:
* **Layering paid off** — dependencies were one-directional, so testing and evolution
  were cheap and safe.
* **Validation at the logic layer** kept the server thin and the data trustworthy.
* **Automated tests + coverage + complexity metrics** gave objective evidence of
  quality (40/40 tests, 94% coverage, avg CC 2.4).
* **Lehman's Laws guided maintenance** — we deliberately refactored to keep complexity
  from drifting upward while adding a new feature.

The system is **complete, runnable, tested, and demo-ready.**

---
*Deliverables in the submission bundle:* SRS · Architecture + diagrams · Source code (ZIP)
· Test cases & results · Metrics report · Final report.
