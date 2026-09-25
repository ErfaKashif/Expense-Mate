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
  import/export, single-user-per-account data, and **full multi-currency
  support** (per-transaction currency, a per-user base/reporting currency,
  conversion-weighted analytics, an exchange-rate table and a converter).
* **Out of scope (future):** live FX feed from a third-party API (rates are a
  maintained offline table), cloud/backup sync, mobile apps, multi-wallet
  accounts, recurring/standing-order transactions.

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
* **Assumptions:** each amount is stored in its **native** currency together with
  that currency code; all analytics convert amounts into the user's **base
  currency** via USD as the pivot; exchange rates are a maintained offline table
  (no network access is required); the user has a modern browser.

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
| FR-11 | The system shall support **multi-currency** transactions: each record stores its own currency code from a supported set of **20 currencies** (USD, PKR, EUR, GBP, INR, AED, SAR, QAR, KWD, OMR, CAD, AUD, SGD, MYR, BDT, TRY, JPY, CNY, ZAR, CHF) with an offline FX rate table. | High |
| FR-12 | The system shall let each user set a **base (reporting) currency** and shall **convert all analytics** — totals, per-category sums, monthly trend and budget comparisons — into it, so mixed-currency data yields correct figures. | **High** |
| FR-13 | The system shall expose an **exchange-rate table** (1 unit of each currency in base, and 1 base in each currency) and a **quick converter** endpoint/UI. | Med |
| FR-14 | The system shall preserve **native** amounts: the transaction list shows both the native amount and the converted base amount, and CSV export includes both. | Med |
| FR-15 | The system shall **deploy as a serverless function** (Vercel) as well as run locally, honouring an injected `PORT` and a writable DB path. | Med |

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
FR-07,08→summary/charts; FR-09→csv; FR-10→db; FR-11..14→multi-currency
(`logic.convert`, `base_currency`, `rates_table`, `transactions_view`);
FR-15→`api/index.py` + `vercel.json`; NFR→layering & tests.

**Deliverable status:** ✅ 2-page SRS complete (functional + non-functional + use cases).
