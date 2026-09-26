# Metrics Report — ExpenseMate

**Team 02 · Software Construction · v1.0**
**Compiled from:** Phase 3/4 Coding & Testing Report, Phase 6 Final Report

---

## 1. Purpose

This report consolidates all quantitative metrics collected across the project —
test results, code coverage, cyclomatic complexity, and defect rates — into a single
standalone reference, as required by the Final Submission Bundle.

---

## 2. Test Execution Metrics

| Level | Test File | Cases | Pass | Fail | Pass Rate |
|-------|-----------|-------|------|------|-----------|
| Unit (Persistence) | `test_db.py` | 11 | 11 | 0 | 100% |
| Unit (Business Logic) | `test_logic.py` | 30 | 30 | 0 | 100% |
| Integration & System (API) | `test_api.py` | 21 | 21 | 0 | 100% |
| **Total** | — | **62** | **62** | **0** | **100%** |

```
===================== 62 passed in 0.78s =====================
```

**Test growth:** 22 of the 62 tests were added during the multi-currency maintenance
round (conversion via USD pivot, round-trip accuracy, unsupported-code rejection,
conversion-weighted analytics, base-currency switching, cross-currency budget alerts,
rate-table shape, converted CSV column, `/api/convert`, `/api/settings/base_currency`).

---

## 3. Code Coverage Metrics

Measured with `pytest-cov` (branch-aware).

| Module | Statements | Coverage |
|--------|-----------|----------|
| `app/backend/db.py` | 94 | 97% |
| `app/backend/logic.py` | 203 | 97% |
| `app/backend/server.py` | 145 | 89% |
| **TOTAL** | **442** | **94%** |

**Trend:** statements grew from 339 → 442 with the multi-currency feature; overall
coverage held at 94% and *improved* to 97% in both business-critical layers
(`db.py`, `logic.py`). Remaining misses are the Flask `app.run` entrypoint and
defensive error branches.

---

## 4. Code Complexity Metrics

Measured with `radon` (cyclomatic complexity).

### 4.1 Backend (Phase 3/4 snapshot)

| Module | Functions | Avg CC | Max CC (function) |
|--------|-----------|--------|-------------------|
| `db.py` | 17 | ~2.1 | 4 (`list_transactions`) |
| `logic.py` | 15 | ~3.6 | 9 (`add_transaction`) |
| `server.py` | 4 | 1.0 | 1 |
| **Total** | **37** | **2.43** | **9** |

### 4.2 Full-project snapshot (Phase 6, post-maintenance)

| Metric | Value |
|--------|-------|
| Python LOC | 910 |
| Python SLOC | 633 |
| Comments | 91 (~14%) |
| Backend blocks | 46 |
| Total CC | 125 |
| Average CC | 2.72 |
| Max CC | 10 — `category_summary`, `budget_status` (both Grade B) |
| Frontend (HTML) | 196 lines |
| Frontend (JS) | 361 lines |
| Frontend (CSS) | 179 lines |

**Grade distribution:** radon scale A = 1–5, B = 6–10, C = 11–20. Nearly all
functions grade **A**; the highest three grade **B** (9, 8, 6) — validation, alert,
and import logic, which intentionally contain several guard clauses. All remain
within the acceptable range (≤10) and were left as-is after review, since splitting
them further would hurt readability.

**Interpretation:** complexity stayed low and well-contained through two rounds of
feature growth, supporting maintainability (NFR-03) and testability (NFR-04); the
densest branches coincide with the areas covered by the highest-coverage tests.

---

## 5. Defect (Fault) Metrics

| Bug ID | Severity | Found in | Fix | Status |
|--------|----------|----------|-----|--------|
| BUG-01 | Medium | `test_db` sweep | Duplicate username now returns HTTP 409 instead of leaking `IntegrityError` | ✅ Fixed |
| BUG-02 | Low | `logic.import_csv` | Blank/unsupported currency no longer crashes import; falls back to base currency, bad rows skipped | ✅ Fixed |
| BUG-03 | Medium | CSV export | `None` category exported as `""`, displayed as `'—'` | ✅ Fixed |
| BUG-04 | Medium | Manual UI test | Chart.js CDN failure aborted the refresh chain; library vendored locally, charts destroyed/redrawn on data change | ✅ Fixed |

**Fault-find / fault-fix rate:** 4 defects found, 4 fixed — **100% fault-fix rate**.
Average time-to-fix ≈ minutes for BUG-01–03 (same-session fixes during Phase 3/4);
BUG-04 fixed and verified end-to-end during Phase 5. **0 open defects** at time of
final demo. Residual risk is cosmetic only (charts fail offline if the vendored
asset is somehow missing — mitigated by CHG-07).

---

## 6. Regression Verification

Full suite re-run after all Phase 5 maintenance changes:

```
===================== 62 passed in 0.78s =====================  (94% coverage)

app/backend/db.py       94 stmts   97%
app/backend/logic.py   203 stmts   97%
app/backend/server.py  145 stmts   89%
TOTAL                  442 stmts   94%
```

One pre-existing test (`test_currency_stored_and_summed`, asserting the old naive
native-summing behaviour) was deliberately rewritten as
`test_analytics_convert_to_base_currency` to assert the corrected, converted total —
confirming tests were updated in step with requirements rather than left stale.

---

## 7. Summary

| Metric | Result |
|--------|--------|
| Total tests | 62 / 62 passing (100%) |
| Code coverage | 94% overall · 97% business layers |
| Average cyclomatic complexity | 2.72 (Grade A) |
| Max cyclomatic complexity | 10 (Grade B, acceptable) |
| Defects found | 4 |
| Defects fixed | 4 (100% fault-fix rate) |
| Open defects | 0 |

These figures collectively support the project's Non-Functional Requirements for
maintainability (NFR-03) and testability (NFR-04), and provide objective evidence
of quality across both the initial build and the two-round maintenance cycle.

**Deliverable status:** ✅ Metrics Report complete.
