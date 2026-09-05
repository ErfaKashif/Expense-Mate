# Software Requirements Specification (SRS) — ExpenseMate

* **Course:** Software Construction 
* **Team:** [24K-3010, 24K-3037] 
* **Version:** 1.0 

---

## 1. Introduction & Overview

### 1.1 Purpose & Scope
ExpenseMate is a lightweight, single-user **Personal Expense Manager** demonstrating the full Software Construction lifecycle.
* **In Scope:** Authentication, transaction CRUD, category monthly budgets, spending alerts, visual analytics, and CSV import/export.
* **Out of Scope:** Multi-user data sharing, cloud backup sync, mobile platforms, and live external bank syncing.

### 1.2 Target Operating Environment
* **Platform:** Local Workstation (Windows / macOS / Linux) | **Runtime:** Python 3.11+, Flask
* **Database:** SQLite (embedded, file-based ACID compliance) | **Interface:** Standard Browser UI

---

## 2. Requirements & Acceptance Criteria

### 2.1 Functional Requirements (FR) & Acceptance Criteria

| ID | Priority | Functional Requirement | Acceptance Criteria                                                                                                                                                     |
| :--- | :--- | :--- |:------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **FR-01** | High | User registration, login, and session logout. | **AC-01:** *Given* unique credentials, *When* submitted, *Then* store password via salted hash (`pbkdf2:sha256`) and initiate session. Reject duplicates.               |
| **FR-02** | High | Full CRUD for income and expense records. | **AC-02:** *Given* an auth session, *When* adding/editing/deleting a record (date, description, amount, category, currency), *Then* instantly commit to SQLite.         |
| **FR-03** | High | Input data validation. | **AC-03:** *Given* input fields, *When* date $\neq$ `YYYY-MM-DD`, amount $< 0$, or description is empty, *Then* reject write and raise a field error.                   |
| **FR-04** | High | Category monthly budget limits (`YYYY-MM`). | **AC-04:** *Given* a target month/category, *When* assigning a spending cap, *Then* persist the limit without altering adjacent months.                                 |
| **FR-05** | High | Automated budget alert notifications. | **AC-05:** *Given* monthly expenses in a category, *When* total spend reaches $\ge 80\%$, trigger **Warning**; when $\ge 95\%$, trigger **Critical** alert.             |
| **FR-06** | High | Monthly category analytics & net balance. | **AC-06:** *Given* monthly transactions, *When* viewed, *Then* calculate $\text{Net Balance} = \sum \text{Income} - \sum \text{Expenses}$ and group totals by category. |
| **FR-07** | High | Dashboard charts (Pie/Doughnut & Line). | **AC-07:** *Given* transaction history, *When* rendering dashboard, *Then* draw pie chart (category breakdown) and line chart (income vs. expense trend).               |
| **FR-08** | High | Fault-tolerant CSV export and import. | **AC-08:** *Given* a CSV upload, *When* invalid rows exist, *Then* process valid records, skip corrupted rows, and display an import summary toast.                     |
| **FR-09** | Stretch | Multi-currency transaction labeling. | **AC-09:** *Given* currencies (`USD, PKR, EUR, GBP`), *When* selected, *Then* tag record and normalize totals via internal exchange rate table.                         |

---

## 3. Non-Functional Requirements (NFR)

| ID | Category | Performance & Technical Constraint |
| :--- | :--- | :--- |
| **NFR-01** | Usability | Browser UI renders summary cards, charts, and budget bars immediately after login; zero host/port setup needed. |
| **NFR-02** | Performance | End-to-end response time **$< 300\text{ ms}$** locally for datasets between $10,000$ and $50,000$ records. |
| **NFR-03** | Maintainability | Strict 4-tier architecture (Presentation / API Server / Core Logic / Data Access) allowing modular testing. |
| **NFR-04** | Testability | Automated test suite executable headlessly via `pytest` covering unit, integration, and API layers. |
| **NFR-05** | Security | Passwords hashed using salted `pbkdf2:sha256` or `bcrypt`. All endpoints restrict access to authenticated sessions. |
| **NFR-06** | Reliability | Schema constraints (`FOREIGN KEY`, `CHECK`, `UNIQUE`) enforce data integrity and strict local ACID compliance. |
| **NFR-07** | Portability | Cross-platform compatibility (Windows, macOS, Linux) with single `pip install Flask` execution. |

---

## 4. System Verification & Traceability Matrix (RTM)

| FR ID | Description | Target NFR(s) | Verification Test Suite |
| :---|:---|:---|:---|
| **FR-01** | User Auth & Session Handling | NFR-01, NFR-03, NFR-05 | `tests/test_auth.py` |
| **FR-02** | Income/Expense Transaction CRUD | NFR-02, NFR-03, NFR-06 | `tests/test_transactions.py` |
| **FR-03** | Input Validation Engine | NFR-03, NFR-06 | `tests/test_validation.py` |
| **FR-04** | Monthly Budget Configuration | NFR-02, NFR-03, NFR-06 | `tests/test_budgets.py` |
| **FR-05** | Budget Alert Engine ($\ge 80\%, \ge 95\%$) | NFR-01, NFR-03, NFR-06 | `tests/test_alerts.py` |
| **FR-06** | Category Analytics & Net Balance | NFR-02, NFR-03, NFR-06 | `tests/test_analytics.py` |
| **FR-07** | Visual Chart Rendering | NFR-01, NFR-02, NFR-07 | `tests/test_dashboard_ui.py` |
| **FR-08** | Fault-Tolerant CSV Import/Export | NFR-02, NFR-06 | `tests/test_csv_import_export.py` |
| **FR-09** | Multi-Currency Labeling & Rates | NFR-02, NFR-03, NFR-06 | `tests/test_currency.py` |