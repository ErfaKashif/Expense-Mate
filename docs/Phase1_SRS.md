# Software Requirements Specification (SRS) — ExpenseMate

**Course:** Software Construction
**Team:** 02 (Team Lead submits) · **Members:** Member A & Member B
**Document:** SRS (2 pages target) · **Version:** 1.0 · **Date:** 04 Sep 2026
**Deadline:** 18 Sep 2026

---

## 1. Introduction

### 1.1 Purpose
ExpenseMate is a small, self-contained **Personal Expense Manager** that lets a
single user record income and expenses, define monthly budgets per category,
and view visual analytics (category-wise charts and monthly trends). It is
built from scratch to demonstrate the full Software Construction lifecycle:
*Requirements → Design → Construction → Testing → Maintenance.*

### 1.2 Scope
* **In scope:** user accounts, income/expense records, monthly category budgets,
  automatic budget alerts, category-wise analytics & visual charts, CSV
  import/export, single-user-per-account data.
* **Out of scope (future):** multi-currency *conversion-weighted* reporting,
  cloud/backup sync, mobile apps, multiple currencies per wallet UI.
  A simple multi-currency *label* (currency per transaction) is a stretch goal.

### 1.3 Definitions & Terms
| Term | Meaning |
|------|---------|
| Transaction | A single income or expense record (date, description, amount, type, category, currency). |
| Budget | A spending limit on a category for one month (`YYYY-MM`). |
| Alert | A soft warning (≥80%) or hard alert (≥95%) when a category is near/over budget. |
| Category | A named grouping of transactions ("Food", "Salary", …). |

---

## 2. Overall Description

* **Operating environment:** single workstation; Python 3.11+; SQLite (no external DB server).
* **Architecture style:** 4-tier **Client-Server** (Presentation / Server API / Logic / Persistence).
* **Users:** one authenticated owner per account (single-user sessions).
* **Assumptions:** amounts stored in native currency; analytics sum native amounts
  except where noted; user has a browser.

---

## 3. Functional Requirements (FR)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | The system shall let a user **register** with a unique username + password and **log in/out**. | High |
| FR-02 | The system shall allow adding an **income or expense** with date, description, amount, type, category and currency. | High |
| FR-03 | The system shall **validate** input: date format, non-negative amount, valid type, supported currency, non-empty description. | High |
| FR-04 | The system shall **list and delete** a user's transactions (filterable by month). | High |
| FR-05 | The system shall allow **setting/updating a monthly budget** per category (`YYYY-MM` + amount). | High |
| FR-06 | The system shall **raise alert** when monthly spend ≥ **80%** (warning) or ≥ **95%** (critical) of a budget and show a message. | **High** |
| FR-07 | The system shall compute **category-wise analytics** (income & expense totals by category) and **net balance** for a month. | High |
| FR-08 | The system shall render **visual charts** for category-wise expense (pie/doughnut) and **monthly income/expense trend** (line). | High |
| FR-09 | The system shall **export** transactions to **CSV** and **import** transactions **from CSV**, skipping malformed rows. | **High** |
| FR-10 | The system shall **persist** all data in SQLite and restore it across restarts. | High |
| FR-11 | The system shall support **multi-currency** labels on transactions (USD, PKR, EUR, GBP, INR, AED, SAR) via a rate table. | Med (stretch) |

---

## 4. Non-Functional Requirements (NFR)

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Usability | Browser UI is simple: register/log-in → dashboard with cards, charts, budget bars, CSV controls. No host/port config beyond starting the server. |
| NFR-02 | Performance | CRUD and analytics respond in < 300 ms locally for a few thousand transactions. |
| NFR-03 | Maintainability | **Layered** code (UI / Server / Logic / DB) so modules can be unit-tested and changed independently. |
| NFR-04 | Testability | Each layer has unit tests; the API has integration/system tests. Runs headless via `pytest`. |
| NFR-05 | Security | Passwords stored as SHA-256 hashes; read/write of a user's data requires an authenticated user id. |
| NFR-06 | Reliability | Input validation prevents corrupt records; DB constraints (foreign keys, CHECK, UNIQUE) protect integrity. |
| NFR-07 | Portability | Pure Python + SQLite + Flask; works on Windows/macOS/Linux with one `pip install Flask`. |
| NFR-08 | Completeness | Meets the "challenging part": budget alerts, CSV import/export, category analytics. |

---

## 5. Use Case Diagram & Description

The use case diagram is in **`diagrams/use_case_diagram.png`** (Member B). Main use cases:

1. **Log in / Register** — enters system.
2. **Add Income** / **Add Expense** — creates a transaction (FR-02).
3. **Set Monthly Budget** — sets/updates a category limit (FR-05).
4. **View Budget Alerts** — sees warnings/critical alerts (FR-06).
5. **View Charts & Reports** — category analytics + trend (FR-07, FR-08).
6. **Export CSV** / **Import CSV** — data interchange (FR-09).
7. **Manage Transactions** — list & delete (FR-04).

---

## 6. Appendix — Traceability

FR-01→auth; FR-02→transactions; FR-03,06→logic; FR-04→list/delete; FR-05,06→budget;
FR-07,08→summary/charts; FR-09→csv; FR-10→db; FR-11→currency; NFR→layering & tests.

**Deliverable status:** ✅ 2-page SRS complete (functional + non-functional + use cases).
