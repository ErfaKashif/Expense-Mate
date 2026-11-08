"""
BudgetCalculator: the budget rules, rewritten as pure calculations.

REWRITE of the Assignment 01 budget-calculation module, which was spread
over `Logic.budget_status`, the budget branch of `Logic.add_transaction`,
the credit-back branch of `Logic.delete_transaction` and four `Database`
methods that kept a running `remaining_amount` column up to date.

Key design decision
-------------------
The remaining budget is CALCULATED (limit - money actually spent) every
time, instead of being stored and patched on every insert/delete. A stored
running balance went wrong whenever a budget was created or changed after
expenses already existed (the old code reset it to the full amount), so
the dashboard and the "add expense" alert disagreed. Calculating it means
there is only one source of truth: the transactions.

This class has no database, HTTP or currency-table access. It receives
numbers and returns BudgetStatus / BudgetAlert objects, so every rule can
be unit-tested with plain values.
"""

from dataclasses import dataclass

from ..models import BudgetAlert, BudgetStatus

OK, WARNING, CRITICAL = "ok", "warning", "critical"


@dataclass(frozen=True)
class BudgetThresholds:
    """Fractions of the budget at which an alert is raised."""
    warning: float = 0.80
    critical: float = 0.95

    def __post_init__(self):
        if not 0 < self.warning <= self.critical:
            raise ValueError("thresholds must satisfy 0 < warning <= critical")


class BudgetCalculator:
    def __init__(self, thresholds=None):
        self.thresholds = thresholds or BudgetThresholds()

    # ------------------------------------------------------------------ #
    # Single rules
    # ------------------------------------------------------------------ #
    @staticmethod
    def usage_ratio(spent, limit):
        """Fraction of the budget used, rounded to 4 places.

        A zero budget with spending counts as fully used (1.0): "no money
        allowed" was exceeded. (Assignment 01 reported 0 % and 'ok'.)
        """
        if limit > 0:
            return round(spent / limit, 4)
        return 1.0 if spent > 0 else 0.0

    def level_for(self, ratio):
        if ratio >= self.thresholds.critical:
            return CRITICAL
        if ratio >= self.thresholds.warning:
            return WARNING
        return OK

    # ------------------------------------------------------------------ #
    # One budget
    # ------------------------------------------------------------------ #
    def evaluate(self, category, limit, spent, currency, symbol,
                 budget_currency=None, budget_amount_native=None):
        """Status of one budget. `limit` and `spent` must be in `currency`."""
        limit = round(limit, 2)
        spent = round(spent, 2)
        ratio = self.usage_ratio(spent, limit)
        budget_currency = (budget_currency or currency).upper()
        return BudgetStatus(
            category=category,
            limit=limit,
            spent=spent,
            remaining=round(limit - spent, 2),
            ratio=ratio,
            level=self.level_for(ratio),
            currency=currency,
            symbol=symbol,
            budget_currency=budget_currency,
            budget_amount_native=float(limit if budget_amount_native is None
                                       else budget_amount_native),
            converted=budget_currency != currency,
        )

    @staticmethod
    def alert_for(status):
        """The alert to show for a status, or None when the budget is fine."""
        percent = int(status.ratio * 100)
        used = f"{status.symbol}{status.spent}"
        limit = f"{status.symbol}{status.limit}"
        if status.level == CRITICAL:
            message = (f"You have exceeded {percent}% of the budget for "
                       f"'{status.category}' (spent {used} of {limit}).")
        elif status.level == WARNING:
            message = f"Budget for '{status.category}' is at {percent}% ({used} of {limit})."
        else:
            return None
        return BudgetAlert(category=status.category, level=status.level, message=message)

    # ------------------------------------------------------------------ #
    # A whole month
    # ------------------------------------------------------------------ #
    def evaluate_month(self, budget_lines, spent_by_category, currency, symbol):
        """Statuses and alerts for every budget of a month.

        budget_lines       list of dicts: category, limit (already in `currency`),
                           budget_currency, budget_amount_native
        spent_by_category  {category name: amount spent, in `currency`}
        Returns (statuses, alerts).
        """
        statuses = [
            self.evaluate(line["category"], line["limit"],
                          spent_by_category.get(line["category"], 0.0),
                          currency, symbol, line.get("budget_currency"),
                          line.get("budget_amount_native"))
            for line in budget_lines
        ]
        alerts = [a for a in map(self.alert_for, statuses) if a is not None]
        return statuses, alerts
