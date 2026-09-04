# Architecture & Construction Plan — ExpenseMate

**Phase 2 deliverable · Team 02 · v1.0**

---

## 1. Architectural Style (chosen by Both)

We use the **Layered (Multitier) — Client/Server** architectural style, locally.

```
┌──────────────────────────────────────────────────────┐
│  Layer 1  Presentation   (Client)  index.html, app.js │  ← the "Client"
├──────────────────────────────────────────────────────┤
│  Layer 2  Server / REST   (Flask)  server.py          │  TCP :5000
├──────────────────────────────────────────────────────┤
│  Layer 3  Business Logic          logic.py            │
├──────────────────────────────────────────────────────┤
│  Layer 4  Persistence             db.py → SQLite      │
└──────────────────────────────────────────────────────┘
```

**Why this style:**
* Each tier has a single responsibility ⇒ easy to unit test in isolation.
* Client communicates with the server **only** over HTTP/REST (JSON) ⇒ the UI can be
  changed or replaced without touching business rules (testability, maintainability).
* SQLite gives a zero-configuration, crash-safe persistent store for a local app.
* Clean dependency direction — higher layers depend on lower layers, never the reverse.
  The DB is injected into `Logic` (dependency inversion) so tests can swap in a temp DB.

---

## 2. The Four Architectural Views (Member A)

All diagrams rendered in **`diagrams/`**.

### 2.1 Logical View — `logical_view.png`
Components & their dependencies: Presentation (browser) → Server/REST → Business Logic →
Persistence. Documented as 4 layers with the exact module each maps to.

### 2.2 Process View — `process_view.png`
Runtime processes: Browser (client process), Flask web server process (worker), SQLite
DB process (file I/O). Includes an annotated request flow: *UI action → POST
/api/transactions → logic validates/stores → 201 JSON response.*

### 2.3 Physical View — `physical_view.png`
Physical nodes & environment: a single **Laptop/PC** running the Browser client, the
server on **localhost:5000**, and the **`expensemate.db`** file. Node selection:
Python 3.11+, Flask 3.x, SQLite (stdlib), CSV files under `sample_data/`.

### 2.4 Deployment View — `deployment_view.png`
«device» User Workstation hosting the components: Browser UI, server.py (process),
logic.py (component), SQLite db (database), tests/ (test harness) — with connectors
HTTP, pytest, and SQL. Confirms a **local** single-host deployment.

---

## 3. Coding Standards & Tools (Member B)

### 3.1 Tools
| Concern | Tool |
|---------|------|
| Language | Python 3.11+ |
| Web framework | Flask 3.x |
| Database | SQLite (stdlib `sqlite3`) |
| Server testing | `pytest` |
| Complexity metrics | `radon` (cyclomatic) |
| Charts (client) | Chart.js CDN |
| VCS | Git |

### 3.2 Coding standards (adopted)
* **Naming:** modules `lower_snake_case`, classes `PascalCase`, functions `lower_case`.
* **Layering:** only the Server layer touches HTTP; only the Logic layer applies business
  rules/validation; only the DB layer writes SQL. No SQL in the server or logic modules.
* **Docstrings:** every module documents its responsibility; key functions have docstrings.
* **Error handling:** raise a typed `ValidationError` for bad input; the server maps it to
  HTTP 400; unexpected → 500.
* **Testing:** one test file per module (`test_db`, `test_logic`, `test_api`); logic tests
  never require a running server.
* **Formatting:** ~4-space indent, ≤ ~90 chars/line, blank lines between functions.

---

## 4. Construction Timeline (Gantt) — Member B

Gantt chart in **`diagrams/gantt_chart.png`** (≈7 weeks / 40 working days):

| Phase | Days | Owner |
|-------|------|-------|
| 1 Requirements & SRS + Use Case | 0–6 | A / B |
| 2 Architecture + Views + Standards | 6–11 | Both / A / B |
| 3 Coding (backend + frontend) + unit tests | 11–24 | A / B / Both |
| 4 Integration + system tests + metrics | 23–29 | A / B / A |
| 5 Maintenance (feat + 2 bugs + refactor) | 28–34 | Both |
| 6 Final report + demo | 34–39 | Both |

---

## 5. Maintenance Scope

* **Adaptive:** add multi-currency support (new feature) — small rate table + currency field.
* **Corrective:** fix 2 seeded/real bugs (see Phase 5 churn log).
* **Perfective:** refactor for clarity, add docstrings, reduce complexity.
* **Optional/future:** cloud backup, single source of FX rates via API.
* **Lehman's Laws analysis:** in Phase 5 (change log).

**Deliverable status:** ✅ Architecture document + Gantt chart.
