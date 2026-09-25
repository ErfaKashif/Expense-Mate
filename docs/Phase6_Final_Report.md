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
* **Full multi-currency support** — **20 currencies**, a currency per transaction, a per-user
  **base (reporting) currency** switchable at runtime, **conversion-weighted analytics**
  (totals, per-category sums, monthly trend *and* budget comparisons all converted through
  USD as pivot), **native amounts preserved** (`by_currency` breakdown, `amount_base` on every
  row, converted column in CSV export), an **exchange-rate table** and a **quick converter**.
* **Navigation bar** mapping 1:1 to features (Dashboard, Add Transaction, View Transactions,
  Analytics & Reports, Budgets & Alerts, Currency, CSV Tools) with smooth scroll + slide-down
  reveal; **light theme** (soft blues, white, neutral grays, sage greens); Chart.js
  **vendored locally** so charts always render and refresh without internet.
* **Deployable** as a Vercel serverless function (`api/index.py` + `vercel.json`) as well as
  locally (`run.py`, PORT-aware, debugger disabled on deployed hosts).

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
| Unit (logic) | 30 | ✅ pass |
| Integration & system (API) | 21 | ✅ pass |
| **Total** | **62** | **100% pass** · **94% code coverage** (442 statements) |

**Coverage by module:** `logic.py` **97%** · `db.py` **97%** · `server.py` **89%**.

**Complexity (cyclomatic, via `radon`):** Python LOC **910**, SLOC **633**, comments **91**;
backend **46** blocks, total CC **125**, **avg CC 2.72**, **max CC 10**
(`category_summary` and `budget_status`, both grade **B** = well-structured, low risk).
The front end adds 196 (HTML) + 361 (JS) + 179 (CSS) lines.
**Fault-find/fix:** 4 defects found & fixed, **fault-fix rate 100%**, 0 open defects.

---

## 4. Maintenance & Evolution

Following Lehman's Laws, we kept the system alive across **nine** logged changes:
* **Adaptive** — multi-currency in two rounds. CHG-01 added currency *labels*; a design review
  then showed analytics were summing **native** amounts (`100 USD + 5000 PKR → 5100`, which is
  meaningless), so **CHG-06** upgraded it to *real conversion*: 20 currencies, per-user base
  currency, conversion-weighted totals/trends/budgets, native breakdown preserved, converter +
  rate table. **No schema migration was required** — Round 1's schema already carried
  `base_currency`/`currency`, the payoff of designing for change.
* **Corrective** — 4 defects fixed: duplicate-username 409, CSV import resilience, `None`
  category export, and **BUG-04 "charts don't update"**: Chart.js was loaded from a CDN, so when
  it failed to load `drawPie()` threw and aborted the whole refresh chain (cards, table and
  charts all froze). The library is now **vendored locally** and charts are destroyed and
  redrawn on every data change. CHG-09 also removed a genuine security exposure —
  `debug=True` on a public host permits remote code execution.
* **Perfective** — refactored `logic.py`, centralised validation via `ValidationError`, added
  docstrings, replaced hard-coded `$` formatting with base-symbol-driven `fmt()`, and added the
  navigation bar + CSS-custom-property light theme.

All changes were localised because of the layer separation, and the full **62-test** suite
re-ran green after maintenance (coverage *rose* to 97% in both business layers) — confirming
non-disruptive evolution. One legacy test that asserted the old naive currency summing was
deliberately rewritten to assert the corrected, converted behaviour.

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
python -m pytest -v          # 62 tests
python -m pytest --cov=app.backend    # coverage report (94%)
python -m radon cc app/backend -s    # complexity metrics
```

### 5.1 Try the multi-currency feature
1. **Add Transaction** → enter an amount with currency **PKR** (e.g. 5000) and another in **USD**.
2. Open **Currency** in the nav → the rate table shows 20 currencies; the converter turns
   `100 USD` into `Rs 27,777.78`.
3. Switch **Base currency** to **PKR** → every card, chart, budget bar and alert instantly
   re-converts; switch back to **USD** and it reverts. Native amounts are still visible per
   currency in "This Month — Native Totals per Currency".
4. **View Transactions** shows both the native amount (`Rs5,000.00`) and the converted base
   amount (`$18.00`), with a `⇄` marker on foreign rows.

### 5.2 Deploy it (Vercel / Render / PythonAnywhere)
```bash
npm install -g vercel && vercel login
cd ExpenseMate && vercel --prod
```
Full step-by-step instructions, environment variables, troubleshooting and the SQLite
persistence caveat are in **`docs/Deployment_Vercel.md`**.

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
| **Multi-currency** (20 currencies, base switching, converted analytics) | ✅ Delivered in full |
| Deployment (Vercel serverless + local/PaaS) | ✅ `api/index.py`, `vercel.json`, guide |
| Cloud backup / persistent hosted database | O (future — see `docs/Deployment_Vercel.md`) |
| Full lifecycle deliverables | ✅ (6 phases bundled) |

### 6.1 Limitations & Future Work
* CSV import is **best-effort** — duplicate rows aren't de-duplicated.
* Exchange rates are a **maintained offline table**, not a live FX feed — connecting an API
  (e.g. exchangerate.host) with caching is future work.
* SQLite on a **serverless** host (Vercel) is ephemeral (`/tmp` is wiped); persistent storage
  needs an external DB (Turso/libSQL or Postgres) or a host with a real disk (Render,
  Railway, PythonAnywhere). Options are documented in `docs/Deployment_Vercel.md`.
* Cloud backup, multiple wallets/accounts per user, and recurring transactions remain out of scope.

---

## 7. Conclusion & Lessons Learned

ExpenseMate demonstrates how a small but complete system can be built and maintained
using disciplined software construction:
* **Layering paid off** — dependencies were one-directional, so testing and evolution
  were cheap and safe.
* **Validation at the logic layer** kept the server thin and the data trustworthy.
* **Automated tests + coverage + complexity metrics** gave objective evidence of
  quality (**62/62 tests**, 94% coverage, avg CC 2.72, 97% on the business layers).
* **Lehman's Laws guided maintenance** — we deliberately refactored to keep complexity
  from drifting upward while adding a new feature, and we let a review finding
  (naive currency summing) drive a second adaptive round rather than shipping a
  subtly wrong number.
* **Tests encode requirements** — when the currency behaviour was corrected, the test that
  asserted the old behaviour was rewritten; the suite stayed the project's source of truth.

The system is **complete, runnable, tested, and demo-ready.**

---
*Deliverables in the submission bundle:* SRS · Architecture + diagrams · Source code (ZIP)
· Test cases & results · Metrics report · Final report.
