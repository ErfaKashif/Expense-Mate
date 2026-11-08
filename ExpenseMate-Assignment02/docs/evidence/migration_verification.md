# ExpenseMate migration verification

Run at: 2026-11-07T12:32:11

- Source (SQLite, read-only): `app/data/expensemate.db`
- Target (PostgreSQL): `postgresql://expensemate:****@localhost:5432/expensemate`
- SQLite integrity_check: ok; foreign_key_check: no violations
- Rows read: users=2, categories=11, transactions=12, budgets=3, settings=0
- PostgreSQL schema migrations applied now: ['001']

| Check | Result | Detail |
|---|---|---|
| row count: users | PASS | SQLite=2 PostgreSQL=2 |
| row count: categories | PASS | SQLite=11 PostgreSQL=11 |
| row count: transactions | PASS | SQLite=12 PostgreSQL=12 |
| row count: budgets | PASS | SQLite=3 PostgreSQL=3 |
| row count: settings | PASS | SQLite=0 PostgreSQL=0 |
| row-by-row: users | PASS | all rows identical |
| row-by-row: categories | PASS | all rows identical |
| row-by-row: transactions | PASS | all rows identical |
| row-by-row: budgets | PASS | all rows identical |
| row-by-row: settings | PASS | all rows identical |
| money totals per user/type/currency | PASS | 5 groups compared |
| orphan foreign keys | PASS | 0 orphan rows |
| next id: users | PASS | max id=2, next generated id=3 |
| next id: categories | PASS | max id=11, next generated id=12 |
| next id: transactions | PASS | max id=36, next generated id=37 |
| next id: budgets | PASS | max id=8, next generated id=9 |

- SQLite SHA-256 before: `d985437fcb95340084ad4354a9151eb8775f7b876ae87b800c5e4628162528a6`
- SQLite SHA-256 after:  `d985437fcb95340084ad4354a9151eb8775f7b876ae87b800c5e4628162528a6`
- Original SQLite file unchanged.

RESULT: MIGRATION COMMITTED - all verification checks passed.
