# Maintainability Comparison: Before vs After

**Before** = tag `assignment-01-baseline` (commit `390ed18`). **After** = branch `assignment-02`.
Both were measured with the same commands on the same machine, on 2026-11-07. The raw outputs are in
`docs/evidence/metrics_before.txt`, `metrics_after.txt` and `test_results.txt`. The "before" numbers were
re-measured from a git worktree of the tag, so anyone can reproduce them.

## How each metric was measured

| Metric | Tool / command (run inside `app/backend/`) |
|---|---|
| Cyclomatic complexity (CC) | `radon cc -s -a -n A .` (average) and `radon cc -s -n B .` (blocks with CC ≥ 6) |
| Maintainability index (MI) | `radon mi -s .` (0–100, higher is better) |
| Source lines | `radon raw -s .` (SLOC total) |
| Largest class | `ast` script counting `def` statements directly inside each class (in the evidence files) |
| SQL location | `grep -E 'SELECT … FROM\|INSERT INTO\|UPDATE x SET\|DELETE FROM'` per file |
| Layer bypasses | route handlers calling `db.*` (before) or any repository/cursor (after) in controllers; calls to `logic._private` methods |
| Duplicated rules | number of `>= CRITICAL_RATIO / WARN_RATIO` (before) vs `>= self.thresholds.*` (after) comparisons |
| Tests and coverage | `pytest --cov=app/backend` |

## Results

| # | Indicator | Before | After | Change |
|---|---|---|---|---|
| 1 | Highest CC of any method | **16** (`Logic.add_transaction`), 15 (`Logic.import_csv`) | **9** (`AnalyticsService.category_summary`) | better |
| 2 | Methods with CC ≥ 6 (radon rank B or worse) | 4 (16, 15, 10, 10) | 1 (9) | better |
| 3 | Average CC per block | 2.87 (53 blocks) | 2.31 (137 blocks) | better |
| 4 | Lowest file MI | 35.55 (`logic.py`) | 60.35 (`expense_repository.py`) | better |
| 5 | Largest class (methods) | 26 (`Logic`), 21 (`Database`) | 8 (`ExpenseService`) | better |
| 6 | Responsibilities in the largest class | ~7 in `Logic`: currency, users, validation, transactions, analytics, budgets/alerts, CSV | 1 per class (e.g. `BudgetCalculator` = budget rules only) | better (qualitative count from reading the methods) |
| 7 | Route handlers calling data access directly | 4 | 0 | better |
| 8 | Controller calls to private service methods | 3 (`logic._normalise`) | 0 | better |
| 9 | SQL statements outside the repository/database layer | 0 (all 22 in `db.py`) | 0 (16 in 4 repositories + 3 in `database/schema.py`) | **unchanged**: already true before |
| 10 | Budget-threshold comparisons (duplication) | 4, in 2 places | 2, in 1 place (`BudgetCalculator.level_for`) | better |
| 11 | Automated tests | 73 | 225 (106 unit, 34 integration, 85 regression) | more |
| 12 | Tests runnable without a database | 0 | 106 (≈0.2 s) | better |
| 13 | Statement coverage of `app/backend` | 93% of 542 statements | 97% of 890 statements | better |
| 14 | Total SLOC of `app/backend` | 772 (4 files) | 1129 (36 files) | **worse: +46%** |

## Interpretation (honest)

- The clearest gains are in **complexity concentration** (indicators 1, 2, 4 and 5) and **dependency separation**
  (7 and 8). No single unit is now hard to read or test. The two most complex Assignment 01 methods, CC 16 and 15,
  were exactly the two rewritten modules.
- **Indicator 9 did not improve.** Assignment 01 already kept SQL inside `db.py`. The gain is that the SQL is now
  split per table, and services group statements into transactions, which `db.py` could not do.
- **The code base is larger** (indicator 14). This is the cost of more files, docstrings, dataclass models,
  explicit dependency injection and the migration tooling. More, smaller units are easier to change locally, but
  there is more to navigate. A student needs the architecture diagram to find things.
- Coverage numbers compare different amounts of code (542 vs 890 statements), so they show that the new code is
  at least as well tested, not that testing "improved by 4%".
- `AnalyticsService.category_summary` (CC 9) is now the most complex method. It is a candidate for further
  splitting, but it was only moved (not rewritten) and all its tests pass.
