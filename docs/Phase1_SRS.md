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

| ID    | Requirement                                                                                                                                           | Priority |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-01 | The system shall let a user **register** with a unique username + password and **log in/out**.                                                        | High |
| FR-02 | The system shall allow user to create, read, update, and delete an **income or expense** with date, description, amount, type, category and currency. | High |
| FR-03 | The system shall **validate** input: date format (`YYYY-MM-DD`), non-negative amount, valid type, supported currency, non-empty description.          | High |
| FR-04 | The system shall allow **setting/updating a monthly budget** per category (`YYYY-MM` + amount).                                                       | High |
| FR-05 | The system shall **raise alert** when monthly spend ≥ **80%** (warning) or ≥ **95%** (critical) of a budget and show a message.                       | **High** |
| FR-06 | The system shall compute **category-wise analytics** (income & expense totals by category) and **net balance** for a month.                           | High |
| FR-07 | The system shall render **visual charts** for category-wise expense (pie/doughnut) and **monthly income/expense trend** (line).                       | High |
| FR-08 | The system shall **export** transactions to **CSV** and **import** transactions **from CSV**,while gracefully skipping invalid or corrupted rows.     | **High** |
| FR-9  | The system shall support **multi-currency** labels on transactions (USD, PKR, EUR, GBP, INR, AED, SAR) via a rate table.                              | Med (stretch) || 
---
## 4. Acceptance Criteria

### FR-01: User Authentication & Session Management
* **AC-01.1 (Successful Registration):** 
  * **Given** a new user provides a unique username and valid password, 
  * **When** they submit the registration form, 
  * **Then** the account is created, the password is stored as a secure hash, and the user is redirected to login.
* **AC-01.2 (Duplicate Registration Prevention):** 
  * **Given** an existing username in the database, 
  * **When** a new user attempts to register with that same username, 
  * **Then** the system rejects the registration with an error message (*"Username already exists"*).
* **AC-01.3 (Login/Logout Session Handling):** 
  * **Given** a registered user, 
  * **When** they submit correct credentials, 
  * **Then** an authenticated session is established; when they click "Logout", the session is invalidated, blocking access to protected routes.

---

### FR-02: Transaction CRUD Operations
* **AC-02.1 (Create & Read Transaction):** 
  * **Given** an authenticated user, 
  * **When** they submit a transaction with amount `50.00`, type `Expense`, category `Food`, currency `USD`, and date `2026-09-05`, 
  * **Then** the transaction is persisted in SQLite and appears immediately on their dashboard.
* **AC-02.2 (Update Transaction):** 
  * **Given** an existing transaction record, 
  * **When** the user edits the description or amount and saves changes, 
  * **Then** the updated values overwrite the old record without creating a duplicate entry.
* **AC-02.3 (Delete Transaction):** 
  * **Given** an existing transaction record, 
  * **When** the user confirms deletion, 
  * **Then** the record is permanently removed from the database and UI calculations update accordingly.

---

### FR-03: Input Validation
* **AC-03.1 (Date & Amount Validation):** 
  * **Given** a user creating or updating a transaction, 
  * **When** they submit a negative amount (`-15.00`) or an invalid date string (`05-09-2026`), 
  * **Then** the system rejects the input, highlights the invalid fields, and prevents database insertion.
* **AC-03.2 (Required Fields Enforcement):** 
  * **Given** a transaction submission, 
  * **When** the description field is empty or whitespace-only, 
  * **Then** the system displays a field-level error (*"Description cannot be empty"*).

---

### FR-04: Category Budget Configuration
* **AC-04.1 (Set Monthly Category Budget):** 
  * **Given** an authenticated user, 
  * **When** they assign a budget limit of `$500.00` to `Groceries` for period `2026-09`, 
  * **Then** the system saves the threshold for that specific month and category.
* **AC-04.2 (Update Budget Threshold):** 
  * **Given** an existing budget of `$500.00` for `Groceries` (`2026-09`), 
  * **When** the user updates the limit to `$600.00`, 
  * **Then** the system updates the threshold for `2026-09` without modifying past or future months' budgets.

---

### FR-05: Budget Threshold Alerts
* **AC-05.1 (Warning Alert Level):** 
  * **Given** a category budget of `$100.00` for `Dining`, 
  * **When** total expenses for the month reach or exceed `$80.00` (80%), 
  * **Then** the system triggers a **Warning** alert message on the UI dashboard.
* **AC-05.2 (Critical Alert Level):** 
  * **Given** a category budget of `$100.00` for `Dining`, 
  * **When** total expenses for the month reach or exceed `$95.00` (95%), 
  * **Then** the system elevates the status to a **Critical** alert message on the dashboard.

---

### FR-06: Category Analytics & Net Balance
* **AC-06.1 (Net Balance Calculation):** 
  * **Given** total income of `$3,000` and total expenses of `$1,200` in a selected month, 
  * **When** the analytics engine executes, 
  * **Then** the net balance correctly displays as `+$1,800.00`.
* **AC-06.2 (Category Aggregation):** 
  * **Given** multiple transactions under `Utilities` (`$100`, `$50`, `$25`) in the same month, 
  * **When** viewing monthly category analytics, 
  * **Then** total `Utilities` expense aggregates precisely to `$175.00`.

---

### FR-07: Data Visualization Charts
* **AC-07.1 (Category Expense Breakdown Chart):** 
  * **Given** expense data for a selected month, 
  * **When** the dashboard renders, 
  * **Then** a pie/doughnut chart visually reflects proportional category spending accurately based on underlying totals.
* **AC-07.2 (Income vs. Expense Trend Chart):** 
  * **Given** transaction history across multiple months, 
  * **When** viewing analytics, 
  * **Then** a line chart plots monthly income alongside monthly expenses chronologically.

---

### FR-08: CSV Export & Resilient CSV Import
* **AC-08.1 (CSV Export Generation):** 
  * **Given** user transaction history, 
  * **When** clicking "Export CSV", 
  * **Then** the system downloads a standard `.csv` file formatted with columns: `Date, Description, Amount, Type, Category, Currency`.
* **AC-08.2 (Resilient Import Handling):** 
  * **Given** an uploaded CSV file containing 10 rows where 2 rows contain corrupted formats (e.g., text in amount field or invalid date), 
  * **When** the import script processes the file, 
  * **Then** the 8 valid transactions are saved to SQLite, the 2 invalid rows are skipped, and a summary toast notification displays (*"8 records imported successfully, 2 skipped due to invalid data"*).

---

### FR-09: Multi-Currency Labeling & Conversion
* **AC-09.1 (Supported Currency Tagging):** 
  * **Given** a transaction entry, 
  * **When** selecting any currency from `[USD, PKR, EUR, GBP, INR, AED, SAR]`, 
  * **Then** the label is attached to the transaction record.
* **AC-09.2 (Normalized Analytics Aggregation):** 
  * **Given** transactions logged in multiple currencies, 
  * **When** computing monthly total balance or category analytics, 
  * **Then** values are normalized using the internal exchange rate table to display converted summary totals accurately in the base currency.
## 5. Non-Functional Requirements (NFR)

| ID | Category | Requirement                                                                                                                                                                                                            |
|----|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| NFR-01 | Usability | The web interface must provide an intuitive dashboard displaying summary cards, charts, budget bars, and CSV controls immediately after login. Zero host or port configuration is required beyond starting the server. |
| NFR-02 | Performance | CRUD and analytics respond in < 300 ms locally for datasets containing 10,000 to 50,000 transactions.                                                                                                                  |
| NFR-03 | Maintainability | **Layered** code (UI / Server / Logic / DB) so modules can be unit-tested and changed independently.                                                                                                                   |
| NFR-04 | Testability | Each layer has unit tests; the API has integration/system tests. Runs headless via `pytest`.                                                                                                                           |
| NFR-05 | Security | Passwords stored as SHA-256 hashes; read/write of a user's data requires an authenticated user id.                                                                                                                     |
| NFR-06 | Reliability | Strict input validation prevents corrupt records; DB constraints (foreign keys, CHECK, UNIQUE) protect integrity and transactions ACID safety.                                                                         |
| NFR-07 | Portability | Pure Python + SQLite + Flask; works on Windows/macOS/Linux with one `pip install Flask`.                                                                                                                                  |

---

## 6. Use Case Diagram & Description

The use case diagram is in **`diagrams/use_case_diagram.png`** (Member B). Main use cases:

1. **Log in / Register** — enters system.
2. **Add Income** / **Add Expense** — creates a transaction (FR-02).
3. **Set Monthly Budget** — sets/updates a category limit (FR-04).
4. **View Budget Alerts** — sees warnings/critical alerts (FR-05).
5. **View Charts & Reports** — category analytics + trend (FR-06, FR-07).
6. **Export CSV** / **Import CSV** — data interchange (FR-08).
7. **Manage Transactions** — list & delete (FR-02).
8. **Currency conversions** — Multi-Currency (FR-09).

---

## 7. Appendix — Traceability

### Requirements Traceability Matrix (RTM)

| FR ID | Related NFR ID(s) | Test Suite Verification Path |
| :---|:---|:---|
| **FR-01** | NFR-01, NFR-03, NFR-05 | `tests/test_auth.py` |
| **FR-02** | NFR-02, NFR-03, NFR-06 | `tests/test_transactions.py` |
| **FR-03** | NFR-03, NFR-06 | `tests/test_validation.py` |
| **FR-04** | NFR-02, NFR-03, NFR-06 | `tests/test_budgets.py` |
| **FR-05** | NFR-01, NFR-03, NFR-06 | `tests/test_alerts.py` |
| **FR-06** | NFR-02, NFR-03, NFR-06 | `tests/test_analytics.py` |
| **FR-07** | NFR-01, NFR-02, NFR-07 | `tests/test_dashboard_ui.py` |
| **FR-08** | NFR-02, NFR-06 | `tests/test_csv_import_export.py` |
| **FR-09** | NFR-02, NFR-03, NFR-06 | `tests/test_currency.py` |