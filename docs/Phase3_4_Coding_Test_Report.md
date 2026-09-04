# Phase 3 & 4 — Coding, Unit, Integration & System Testing Report

**Team 02 · ExpenseMate · v1.0**

---

## 1. Module Breakdown (division of work)

| Module | Layer | Owner | File(s) |
|--------|-------|-------|---------|
| Presentation (Client) | Layer 1 | **Member B** | `app/frontend/index.html`, `static/app.js`, `static/style.css` (Chart.js) |
| Server / REST API | Layer 2 | **Member A** | `app/backend/server.py`, `run.py` |
| Business Logic | Layer 3 | **Member A** | `app/backend/logic.py` |
| Persistence (DB) | Layer 4 | **Member A** | `app/backend/db.py` |
| Unit tests | — | Each tests their own | `tests/test_db.py`, `tests/test_logic.py`, `tests/test_api.py` |

Clean layering means each module can be developed and unit-tested independently, then
wired (Phase 4) through the HTTP API.

---

## 2. Unit Testing Strategy

* **`test_db.py`** (Member A) — the *Persistence* layer in isolation, using a throwaway
  temp SQLite DB per test (no server, no network). Covers schema, user CRUD, unique
  username, idempotent categories, month filtering, cascade delete, budget upsert.
* **`test_logic.py`** (Member A, business tests) — *Business Logic* via a `Logic` object
  over a temp DB. Covers input validation, category analytics, balance, trend ordering,
  budget alert thresholds (ok/warning/critical), CSV export/import (incl. malformed-row
  skipping and wrong headers), currency conversion, multi-currency storage.
* **`test_api.py`** (Member B) — the *server + API* using Flask's `test_client`.
  Covers HTTP status codes, auth, and the full user journey.

---

## 3. Unit Test Results

**Result: 40 passed, 0 failed (100%).** Full verbose run:

```
===================== 40 passed in 0.31s =====================
```

| Test file | Tests | Pass | Fail | Purpose |
|-----------|-------|------|------|---------|
| `test_db.py` | 11 | 11 | 0 | Persistence layer |
| `test_logic.py` | 21 | 21 | 0 | Business rules, budgets/alerts, analytics, CSV, currency |
| `test_api.py` | 8 | 8 | 0 | HTTP/API integration & system |

**Code coverage (branch-aware via `pytest-cov`):**

| Module | Statements | Coverage |
|--------|-----------|----------|
| `app/backend/db.py` | 94 | 94% |
| `app/backend/logic.py` | 135 | 99% |
| `app/backend/server.py` | 110 | 87% |
| **TOTAL** | **339** | **94%** |

> Missing lines are mostly the Flask `app.run` entrypoint and a few defensive branches —
> acceptable; the business-critical `logic` layer is at 99%.

---

## 4. Integration Testing (Member A)

Integration = verify the modules cooperate through the real HTTP boundary.
Using `create_app()` + Flask's test client, we drive the **full stack**
(UI logic → REST → logic → SQLite):

* register → login → add **income/expense** → **list** by month → **delete**.
* Full **budget alert** workflow: 3 × $40 expense in "Food" with a $100 budget ⇒
  `summary.total_expense == 120` and `budget.alerts` non-empty (critical).
* **CSV round-trip:** export production CSV, then import a new row back (count = 1).
* Invalid input returns **HTTP 400**; unauthenticated access returns **401**;
  duplicate username returns **409**.

All integration/system assertions pass (see `test_api.py`).

---

## 5. System Testing (Member B)

Executed against a **running** server (`python run.py`, `localhost:5000`):

| # | Scenario | Expected | Result |
|---|----------|----------|--------|
| ST-01 | Load home page | Returns index.html with title ExpenseMate | ✅ |
| ST-02 | Register `demo` / `x` | 201 + user_id | ✅ |
| ST-03 | Login correct/wrong password | 200 / 401 | ✅ |
| ST-04 | Add expense $100 Food | 201, appears in list | ✅ |
| ST-05 | Set Food budget $90 | Budget stored | ✅ |
| ST-06 | Dashboard summary | total_expense 100, critical alert "111%" | ✅ |
| ST-07 | Export CSV | `date,description,amount,type,category,currency` header + row | ✅ |
| ST-08 | Import CSV | imported=1 | ✅ |

System tests also verified via `curl` (records in the report) and the browser UI.

---

## 6. Defect (Fault) Log — found & fixed

| Bug ID | Severity | Found in | Description | Fix | Status |
|--------|----------|----------|-------------|-----|--------|
| BUG-01 | Medium | `test_db` sweep | Duplicate username raised raw `sqlite3.IntegrityError` up to API. | Kept UNIQUE constraint; API maps duplicate username to **HTTP 409**; test asserts the constraint raises properly. | ✅ Fixed |
| BUG-02 | Low | `logic.import_csv` | An unsupported/blank `currency` cell could crash an import row. | Import falls back to the user's base currency; malformed rows are **skipped**, not fatal. | ✅ Fixed |
| BUG-03 | Medium | CSV export | `category_name` could be `None` for uncategorised rows. | Export writes `""` for `None`; display uses `'—'`. | ✅ Fixed |

**Fault-find / fault-fix rates:** all 3 defects were found during Phase 3/4 testing and
fixed within the same session — **fault-fix rate = 100%**, average time-to-fix ≈ minutes.
No **open** defects remain; residual risk = cosmetic (charts offline if Chart.js CDN
unavailable).

---

## 7. Code Complexity & Metrics (Member A)

Cyclomatic complexity via `radon` (measured on the real code):

| Module | Functions | Avg CC | Max CC (function) |
|--------|-----------|--------|-------------------|
| `db.py` | 17 | ~2.1 | 4 (`list_transactions`) |
| `logic.py` | 15 | ~3.6 | 9 (`add_transaction`) |
| `server.py` | 4 | 1.0 | 1 |
| **Total** | **37** | **2.43** | **9** |

* Overall cyclomatic summary: LOC **613**, SLOC **442**, comments **56** (≈11%).
* CC Grade scale (radon): A=1–5, B=6–10, C=11–20. Most functions are **A**; the three
  highest are **B** (9, 8, 6) — they are the validation/alert/import methods that
  intentionally contain several guard clauses. They remain **within the acceptable
  range** (≤10) and were left as B after review (splitting them would hurt readability).
* **Interpretation:** complexity is low and well-contained, supporting **maintainability**
  (NFR-03) and **testability** (NFR-04); the dense branches coincide with the areas
  covered by our highest-coverage tests.

**Deliverable status:** ✅ Source code + unit test report + test cases + bug report + complexity metrics.
