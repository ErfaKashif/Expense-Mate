# Legacy stored `remaining_amount` vs calculated remaining (migrated data)

Read-only query against the migrated application database. Calculated values come from
BudgetService/BudgetCalculator, expressed in each budget's own currency for a like-for-like comparison.

| user | month | category | budget | legacy stored remaining | calculated remaining | consistent? |
|---|---|---|---|---|---|---|
| 1 | 2026-11 | Food | 100.00 USD | -77.2 | 2.8 | **no** |
| 1 | 2026-11 | Transport | 10000.00 PKR | 2300.0 | 2300.0 | yes |
| 1 | 2026-11 | Groceries | 10000.00 PKR | 29699.78 | 1922.0 | **no** |
