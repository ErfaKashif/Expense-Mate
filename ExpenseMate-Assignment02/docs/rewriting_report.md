# Rewriting Report

**Owner:** 24K-3037 Daneya Shafiq · **Commits:** `67d627d rewrite: …`, `c47ac09 refactor(csv): …`

## What existed

The Assignment 01 backend had only **two real classes**: `Logic` (`app/backend/logic.py`, 26 methods) and
`Database` (`app/backend/db.py`, 21 methods), plus the exception `ValidationError`. There was no `ExpenseManager`
or `BudgetCalculator` class. The expense and budget responsibilities were *modules inside those two classes*. We
therefore rewrote the two responsibility clusters below and replaced them with new classes. We did not simply
rename methods.

---

## Rewrite 1: Budget calculation module

**Original code (exact names):**
- `Logic.budget_status`, `Logic.set_budget` (`app/backend/logic.py`)
- the budget branch of `Logic.add_transaction` (about 50 lines) and the credit-back branch of `Logic.delete_transaction`
- `Database.set_budget`, `Database.get_single_budget`, `Database.update_budget_remaining`, and the unused
  `Database.get_budget_remaining_amount` (`app/backend/db.py`)

**Original responsibilities:** store budgets, keep a *running balance* column `budgets.remaining_amount` (decreased on
every expense insert, increased on every delete), compute the warning (80%) and critical (95%) levels, and format
alert messages.

**Problems found in the code and confirmed by running it** (`docs/evidence/defect_probes.md`):
1. **Two sources of truth.** `budget_status` computed "remaining" from the transactions, while
   `add_transaction` used the stored `remaining_amount`. `set_budget` reset the stored value to the full amount
   even when money had already been spent. Result: after spending 91 of 100, the dashboard said *warning* but the
   add-expense alert said *nothing*. In the **real Assignment 01 data**, 2 of 3 stored balances were wrong.
   For example, Groceries showed 29,699.78 PKR remaining on a 10,000 PKR budget
   (`docs/evidence/legacy_remaining_vs_calculated.md`).
2. **Duplicated rules.** The threshold comparisons and both alert messages were written twice, in
   `add_transaction` and in `budget_status`.
3. **Mixed concerns and complex conditionals.** Data retrieval, currency conversion, persistence and the rules
   were interleaved. `add_transaction` had a cyclomatic complexity of 16, and a "guard against corrupted historical
   remaining amounts" hack showed the design was already fighting itself.
4. **Inconsistent category names.** Expenses were title-cased and budgets were not, so a budget for "groceries"
   never saw any spending.
5. **Hard to test.** Every rule needed a database and a full transaction insert to exercise.

**Why a rewrite instead of a small refactor:** the defect is in the *design*, not in a line of code. A stored
running balance must be patched correctly on every insert, delete, budget change and currency change, forever.
Fixing one path, as Assignment 01 tried with its "FIX" comments, left the others wrong. Removing the stored
balance and **calculating** it changes the algorithm, the data flow, the repository API (two methods deleted) and
both callers. That is more than extracting a method.

**New design:** `services/budget_calculator.py`
- `BudgetThresholds` (frozen dataclass, validated: `0 < warning ≤ critical`, default 0.80/0.95)
- `BudgetCalculator.usage_ratio`, `level_for`, `evaluate`, `alert_for`, `evaluate_month`. These are **pure
  functions of numbers**, with no DB, HTTP or currency table. They return the `BudgetStatus`/`BudgetAlert`
  dataclasses (`models/budget.py`).
- `BudgetService` gathers the data (budgets and spending), converts currencies, and calls the calculator.
- `utils/validators.normalise_category()` applies one naming rule to both expenses and budgets.

**Changes in dependent code:** `ExpenseService.add_expense` asks `BudgetService.alert_for_category()`, which uses
the same calculation as the dashboard. `delete_expense` no longer does any budget bookkeeping.
`BudgetRepository.update_remaining`/`get_for_category` were deleted, and `upsert` no longer writes
`remaining_amount` (migrated values are left untouched). `server.py` injects `BudgetCalculator()`.

**Behaviour preserved:** the same 80%/95% thresholds, the identical alert message text, the same `status` dict keys,
and currency conversion into the base currency. All Assignment 01 budget tests still pass, including
"remaining 100 → 60 after expense → 100 after delete". **Behaviour changed on purpose:** a zero budget with
spending is reported as *critical* (it was "ok, 0%"), and the stored column is no longer maintained (the one
legacy assertion on it is updated and marked `A02`).

**Unit tests:** `tests/unit/test_budget_calculator.py` has 20 tests (boundaries 0.7999/0.80/0.9499/0.95, custom and
invalid thresholds, zero budgets, negative remaining, rounding, exact message texts, a whole month, no budgets).
`tests/unit/test_budget_service.py` has 12 tests with mocks. Integration tests: `test_4_…` and `test_4b_…` (spending
before the budget exists).

---

## Rewrite 2: Expense management module

**Original code (exact names):** `Logic.add_transaction` (CC 16), `Logic.import_csv` (CC 15),
`Logic._validate_amount`, `Logic._validate_date`, `Logic.delete_transaction` (`app/backend/logic.py`).

**Original responsibilities:** validate input, choose default currency and category, write the category and the
transaction, update the budget, compute and format alerts, and parse CSV by calling `add_transaction` once per row.

**Problems:**
1. `add_transaction` did six jobs: validation, defaults, two DB writes, budget arithmetic and message formatting.
2. Validation was tangled with persistence. It could not be reused or tested without a database.
3. `import_csv` opened about 5 database connections **per CSV row**. A failure half-way left a **partial import**.
   A short row (`2026-09-01,only two`) crashed with `AttributeError` (`None.strip()`).
4. `_validate_amount(amount, type)` validated the *type* inside the amount check (hidden coupling) and accepted
   `NaN`/`inf`.
5. `delete_transaction` did not check ownership (any user could delete any id), and when the id did not exist it returned `False`, which the route ignored, so it answered `{"ok": true}`.

**Why a rewrite:** the method had no seams to extract along. Validation, persistence and budget logic shared local
variables throughout. Making CSV import atomic also requires a different structure: validate everything first,
then save in one transaction.

**New design:**
- `ExpenseValidator` (`utils/validators.py`) turns raw input into a validated, unsaved `Transaction`. It is pure;
  its only dependency is a currency-normalising function. It is reused for single entries and for CSV rows.
- `CsvImporter` (`services/csv_importer.py`) turns text into row dicts. It is pure, handles BOMs, header case and
  short rows, and counts blank rows. It was split again in `c47ac09` (CC 11 → 5).
- `ExpenseService` coordinates: `validate → transaction(get_or_create category, insert) → BudgetService alert`.
  `import_csv` validates all rows and then saves the valid ones **in one transaction** with a category cache.
  `delete_expense` is a single owner-scoped delete.

**Behaviour preserved:** the same validation messages, the same title-casing and "Income"/"Misc" defaults, the
same `(id, alert)` and `(imported, skipped)` return values, and malformed CSV rows are still skipped rather than
fatal. All 33 original `Logic` tests and 27 API tests pass.

**Unit tests:** `test_expense_validator.py` (18), `test_csv_importer.py` (8) and `test_expense_service.py` (12, with
mocks, e.g. "invalid expense never reaches the repository" and "import uses one transaction and two category
lookups for five rows"). Integration: `test_csv_import_is_all_or_nothing_on_database_failure`.

## Result

| | Before | After |
|---|---|---|
| Worst method CC (radon) | 16 (`Logic.add_transaction`), 15 (`import_csv`) | `add_expense` 2, `import_csv` 4, `CsvImporter.parse` 5, `BudgetCalculator.evaluate` 3 |
| Places where alert thresholds are compared | 2 (4 comparisons) | 1 (`level_for`, 2 comparisons) |
| DB needed to test budget rules / validation | yes | no (pure classes) |
| Five confirmed defects | present | fixed and covered by tests |
