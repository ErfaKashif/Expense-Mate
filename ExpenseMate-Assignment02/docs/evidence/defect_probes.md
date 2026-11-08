# Defect probes: Assignment 01 baseline vs Assignment 02

Same five scenarios run against the code at tag assignment-01-baseline (SQLite) and at branch assignment-02 (PostgreSQL).
The automated equivalents are in tests/integration/test_system_flows.py and tests/unit/test_budget_calculator.py.

## Before (assignment-01-baseline)
```
1. invalid amount on POST /api/transactions -> HTTP 500
2. bob deletes alice's transaction -> HTTP 200 | alice rows left: 0
3. budget without category -> HTTP 500
4. after 91 spent of 100: budget_status level = warning remaining = 9.0 | add_transaction alert = None | stored remaining_amount = 99.0
5. budget set as 'groceries', expense entered as 'groceries' -> budget rows: {'Food': 91.0, 'groceries': 0.0}
```

## After (assignment-02)
```
1. invalid amount on POST /api/transactions -> HTTP 400 {'error': 'Amount cannot be negative.'}
2. bob deletes alice's transaction -> HTTP 404 | alice rows left: 1
3. budget without category -> HTTP 400 {'error': 'Missing required field(s): category'}
4. after 91 spent of 100: budget_status level = warning remaining = 9.0 | add_expense alert = {'category': 'Food', 'level': 'warning', 'message': "Budget for 'Food' is at 91% ($91.0 of $100.0)."}
5. budget 'groceries' + expense 'groceries' -> budget rows: {'Food': 91.0, 'Groceries': 45.0}
```
