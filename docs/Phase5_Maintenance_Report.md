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
| **Adaptive** | CHG-06 | **Upgraded multi-currency from labels to real conversion:** 20 currencies, per-user **base currency** with switching, all analytics/trends/budgets **converted** into base, native amounts preserved (`by_currency`, `amount_base`), `/api/convert` converter, rate table, **Currency** UI panel. | Both | **+22 tests** (62 total, all pass) |
| **Corrective** | CHG-07 | Fixed **BUG-04**: charts did not render/update because Chart.js was loaded from a CDN (blocked offline), which threw and aborted the whole refresh chain. Chart.js is now **vendored locally** (`/static/chart.umd.min.js`) and charts are destroyed + redrawn on every data change. | B | Verified E2E; manual UI test |
| **Perfective** | CHG-08 | **UI overhaul:** sticky **navigation bar** exposing every feature (Dashboard, Add, View Transactions, Analytics, Budgets, Currency, CSV) with smooth scroll + slide-down reveal; new **light theme** (soft blues, white, neutral grays, sage greens). | B | Manual UI test; no API change |
| **Corrective** | CHG-09 | **Deployment hardening:** `run.py` now honours an injected `$PORT` and disables the Werkzeug debugger on deployed hosts (it permits RCE); added `api/index.py` + `vercel.json` for serverless deployment with a writable `/tmp` DB path. | A | Entrypoint verified with `VERCEL=1` |

---

## 2. Adaptive Maintenance — Multi-Currency, Round 1 then Round 2 (Both)

### Round 1 (CHG-01) — currency *labels*
1. **DB** (`db.py`): `transactions.currency` column; `budgets.currency`; `users.base_currency`.
2. **Logic** (`logic.py`): `CURRENCY_RATES` table + `_convert()`; `add_transaction` /
   `set_budget` accept currency; validation rejects unsupported codes.
3. **Server** (`server.py`): `/api/currencies` endpoint.
4. **Client**: currency selector populated from the API.

**Limitation found in review:** analytics summed *native* amounts, so `100 USD + 5000 PKR`
was reported as `5100` — arithmetically meaningless. This became a maintenance request.

### Round 2 (CHG-06) — currency *conversion* (the real feature)
The conversion model: `rate[X]` = value of 1 unit of X in USD; USD is the pivot, so
`amount_in_base = amount * rate[from] / rate[to]`.

1. **Logic** (`logic.py`):
   * `CURRENCY_RATES` expanded to **20 currencies**; added `CURRENCY_SYMBOLS` and
     `CURRENCY_NAMES` for display.
   * public `convert()`, `_normalise()`, `symbol()`, `is_supported()`; `_convert()` kept
     as a back-compatible alias.
   * `base_currency(user_id)` / `set_base_currency(user_id, code)` (validated).
   * `category_summary()`, `balance()`, `monthly_trend()` now **convert every amount into
     the base currency**, and additionally report the **native** per-currency breakdown
     in `by_currency` plus a `foreign_count`.
   * `budget_status()` converts **both sides** — spent *and* the budget limit — so a budget
     set in USD can be compared with spending in PKR; each row reports `budget_currency`,
     `budget_amount_native` and a `converted` flag.
   * `transactions_view()` annotates rows with `amount_base`, `currency_symbol`,
     `base_symbol` and `is_foreign`.
   * `export_csv()` adds an `amount_in_<BASE>` column; `import_csv()` accepts a per-row
     `currency` column and skips (does not crash on) bad rows.
   * `rates_table(base)` produces the UI rate table (per-base and inverse).
2. **Server** (`server.py`): richer `/api/currencies` (rates, symbols, codes, base,
   table), new `POST /api/convert`, `GET /api/settings`,
   `POST /api/settings/base_currency`; `/api/register` validates and echoes the base
   currency; `/api/login` returns base currency + symbol; `/api/transactions` returns the
   annotated view.
3. **Client**: a **Currency** panel in the nav (base-currency switcher that re-converts
   everything instantly, a quick converter, the rate table, native per-currency totals);
   money formatting uses the base symbol everywhere (cards, charts, tooltips, budgets);
   the transaction table shows native **and** converted amounts with a `⇄` marker on
   foreign rows.
4. **DB**: *no schema change was required* — `users.base_currency`,
   `transactions.currency` and `budgets.currency` already existed, so the upgrade was
   purely behavioural. That is the payoff of the Round-1 schema design.

**Result (verified live):** a demo month holding USD + PKR + AED + GBP records reports
`$1,244.56` total expense (converted) while still showing the native
`Rs 14,500 / AED 95 / £320 / $1,166.49`; switching the base to PKR re-reports the same
data as `Rs 345,710.69`. Cross-currency budget alerts fire correctly.

Because `Logic` receives the DB by injection and the server only orchestrates, the blast
radius stayed inside 3 files + the client; **no existing endpoint contract broke**
(`/api/currencies` still returns `rates`).

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
| Currency | Hard-coded USD | Rate table + `convert()` helper | Extensible, testable |
| Money formatting | Hard-coded `$` in the client | Single `fmt()` driven by the user's base symbol | Correct for any base currency |
| Navigation | One scrolling page, features hard to find | Sticky nav bar mapping 1:1 to features, slide-down reveal | Usability (NFR) |
| Theme | Dark palette | Light palette via CSS custom properties | One place to re-theme |
| Chart library | CDN `<script>` (fails offline, broke refresh) | Vendored locally in `/static` | Works with no internet |
| Entrypoint | `run.py` with `debug=True`, fixed port 5000 | `$PORT` aware, debug off when deployed, `api/index.py` for serverless | Deployable & safer |

**Before/after complexity:** avg CC unchanged at ~2.43; LOC increased modestly for
documentation, comment density rose to ~11% — a clear quality gain.

---

## 5. Lehman's Laws Analysis (Both)

We applied Lehman's Laws of Software Evolution to the **48-hour maintenance cycle**:

| Lehman's Law | Application to ExpenseMate | Observed |
|--------------|---------------------------|----------|
| **I. Continuing Change** | An operational system must continually adapt or become progressively less useful. | Multi-currency evolved twice (CHG-01 labels → CHG-06 real conversion), plus a deployment target (CHG-09). ✅ |
| **II. Increasing Complexity** | As a system evolve, its complexity increases unless work is done to maintain/reduce it. | Statements grew 339 → 442; we offset this with small single-purpose currency helpers and refactoring (CHG-05/CHG-08), keeping avg CC ≈2.4 and **raising** coverage of `logic.py` to 97%. ✅ |
| **III. Self-Regulation** | Evolution is roughly self-regulating; measured globally. | Changes arrived in small, reviewed increments; defect count stayed near zero. ✅ |
| **IV. Conservation of Organisational Stability** | Average activity rate over a program's lifetime is invariant. | Workload per phase stayed within the Gantt plan (no late spikes). ✅ |
| **V. Conservation of Familiarity** | Evolution tends to keep the system's overall content (fidelity) stable. | Only ~5 source files changed across both rounds; the 4-layer architecture and every existing endpoint contract remained stable (no DB migration was needed for CHG-06). ✅ |

**Conclusion:** The system followed Lehman's Laws — it *needed* continuous change
(adaptive), complexity did **not** runaway thanks to deliberate refactoring, and the
layered architecture let us evolve with minimal organisational disruption.

---

## 6. Regression & Maintenance Verification

After all Phase 5 changes, the **entire** suite re-ran:

```
===================== 62 passed in 0.78s =====================  (94% coverage)

app/backend/db.py       94 stmts   97%
app/backend/logic.py   203 stmts   97%
app/backend/server.py  145 stmts   89%
TOTAL                  442 stmts   94%
```

One pre-existing test (`test_currency_stored_and_summed`) asserted the *old* naive
behaviour (native summing = 150). It was **deliberately rewritten** as
`test_analytics_convert_to_base_currency` to assert the corrected, converted total
(100.18 USD) — an example of tests encoding requirements and evolving with them.

This proves the maintenance was **non-disruptive** — all original functionality plus the
new feature and the bug fixes still work, confirming maintainability (NFR-03) and
testability (NFR-04).

**Deliverable status:** ✅ Change log + refactoring report.
