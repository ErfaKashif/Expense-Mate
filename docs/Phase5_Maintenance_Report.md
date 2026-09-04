# Phase 5 — Maintenance & Evolution Report

**Team 02 · ExpenseMate · v1.0**

---

## 1. Change Log (summary)

| Change type | ID | Description | Owner | Test impact |
|-------------|----|-------------|-------|-------------|
| **Adaptive** | CHG-01 | Added **multi-currency** support: currency per transaction + a static FX rate table; currency selector in the UI; rate endpoint. | Both | +2 unit tests (passed) |
| **Corrective** | CHG-02 | Fixed **BUG-01**: duplicate username no longer leaks `IntegrityError`; API returns HTTP 409. | A | API test updated (passed) |
| **Corrective** | CHG-03 | Fixed **BUG-02**: CSV import now fails gracefully on bad rows (skip) and never crashes on blank currency. | A | `test_import_csv_skips_bad_rows` (passed) |
| **Corrective** | CHG-04 | Fixed **BUG-03**: CSV export & table render handle `category_name=None` (`""` / `'—'`). | A | `test_export_csv_roundtrip` (passed) |
| **Perfective** | CHG-05 | Refactored `logic.py` for clarity, added module/function docstrings, split responsibilities, standardised on a typed `ValidationError`. | B | Full suite still green |

---

## 2. Adaptive Maintenance — Multi-Currency (Both)

Because the design chose a clean **layered** style, adding a new capability required
changes in only a few, small places:

1. **DB** (`db.py`): `transactions.currency` column; `budgets.currency`.
2. **Logic** (`logic.py`): `CURRENCY_RATES` table + `_convert()`; `add_transaction` /
   `set_budget` accept currency; validation rejects unsupported codes.
3. **Server** (`server.py`): `/api/currencies` endpoint.
4. **Client** (`app.js`/`index.html`): currency selector populated from `/api/currencies`; currency passed with each transaction.

**Result:** users can label transactions in USD/PKR/EUR/GBP/INR/AED/SAR. The conversion
helper (`_convert`) is unit-tested. No other layers had to change — the dependency
inversion (`Logic` receives the DB) kept the blast radius tiny.

---

## 3. Corrective Maintenance — Bugs (Member A)

All 3 defects were logged in **Phase 3/4 Test Report** and fixed during Phase 5.
Fixes were minimal and localised; regression tests added so they cannot recur.
**Fault-fix rate = 100%**; **0 open defects** at the time of the demo.

---

## 4. Perfective Maintenance — Refactoring Report (Member B)

Changes that improve internal quality without changing behaviour:

| Refactor | Before | After | Benefit |
|----------|--------|-------|---------|
| Module docstrings | Some modules undocumented | Every module documents its layer & responsibility | Onboarding/maintenance |
| Validation | Ad-hoc `if` checks in server | Centralised typed `ValidationError` in logic | Consistent 400 responses |
| DB access | Logic knew about connection bookkeeping | `Logic` only calls repository methods; DB owns connections | Separation of concerns |
| Export `None` category | `None` leaked to UI/CSV | Normalised to `""` / `'—'` | No output glitches |
| Currency | Hard-coded USD | Rate table + `_convert()` helper | Extensible, testable |

**Before/after complexity:** avg CC unchanged at ~2.43; LOC increased modestly for
documentation, comment density rose to ~11% — a clear quality gain.

---

## 5. Lehman's Laws Analysis (Both)

We applied Lehman's Laws of Software Evolution to the **48-hour maintenance cycle**:

| Lehman's Law | Application to ExpenseMate | Observed |
|--------------|---------------------------|----------|
| **I. Continuing Change** | An operational system must continually adapt or become progressively less useful. | We added multi-currency (CHG-01) rather than leaving a fixed single-currency tool. ✅ |
| **II. Increasing Complexity** | As a system evolves, its complexity increases unless work is done to maintain/reduce it. | Added functions raised CC slightly; we offset this via refactoring (CHG-05) so avg CC stayed ~2.4. ✅ |
| **III. Self-Regulation** | Evolution is roughly self-regulating; measured globally. | Changes arrived in small, reviewed increments; defect count stayed near zero. ✅ |
| **IV. Conservation of Organisational Stability** | Average activity rate over a program's lifetime is invariant. | Workload per phase stayed within the Gantt plan (no late spikes). ✅ |
| **V. Conservation of Familiarity** | Evolution tends to keep the system's overall content (fidelity) stable. | Only ~4 files changed during maintenance; the architecture (layers) remained stable. ✅ |

**Conclusion:** The system followed Lehman's Laws — it *needed* continuous change
(adaptive), complexity did **not** runaway thanks to deliberate refactoring, and the
layered architecture let us evolve with minimal organisational disruption.

---

## 6. Regression & Maintenance Verification

After all Phase 5 changes, the **entire** suite re-ran:

```
===================== 40 passed in 0.31s =====================  (94% coverage)
```

This proves the maintenance was **non-disruptive** — all original functionality plus the
new feature and the bug fixes still work, confirming maintainability (NFR-03) and
testability (NFR-04).

**Deliverable status:** ✅ Change log + refactoring report.
