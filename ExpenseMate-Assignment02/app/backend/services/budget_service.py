"""
BudgetService: monthly budgets, budget status/alerts and the monthly summary.

It gathers the data (budgets from BudgetRepository, spending from
AnalyticsService), converts budget limits into the user's reporting
currency, and hands plain numbers to BudgetCalculator, which applies the
rules. No SQL here, and no budget arithmetic either.

Feature 2 - Monthly Budget Summary:
    BudgetController -> BudgetService.monthly_summary
                     -> BudgetRepository.list_for_month -> PostgreSQL
"""

from datetime import datetime

from ..utils.validators import normalise_category, require_text, validate_amount, validate_month


class BudgetService:
    def __init__(self, database, budget_repository, category_repository, analytics_service,
                 user_service, currency_service, calculator):
        self.db = database
        self.budgets = budget_repository
        self.categories = category_repository
        self.analytics = analytics_service
        self.users = user_service
        self.currency = currency_service
        self.calculator = calculator

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #
    def set_budget(self, user_id, category, month, amount, currency=None):
        """Create or replace the user's budget for a category and month."""
        month = validate_month(month)
        amount = validate_amount(amount)
        name = normalise_category(require_text(category, "Category"), "expense")
        user = self.users.get_user(user_id)
        currency = self.currency.normalise(currency or user.base_currency)
        with self.db.transaction():
            category_id = self.categories.get_or_create(name, "expense")
            return self.budgets.upsert(user_id, category_id, month, amount, currency)

    def delete_budget(self, user_id, month, category):
        """Delete a budget by month and category name. True if one was deleted."""
        return self.budgets.delete_by_category(user_id, month, category)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    def evaluate_budgets(self, user_id, month, base):
        """(statuses, alerts) for every budget of `month`, in currency `base`."""
        spent = self.analytics.category_summary(user_id, month, base=base)["expense"]
        lines = [{
            "category": b.category_name,
            "limit": self.currency.convert(b.amount, b.currency, base),
            "budget_currency": b.currency,
            "budget_amount_native": b.amount,
        } for b in self.budgets.list_for_month(user_id, month)]
        return self.calculator.evaluate_month(lines, spent, base, self.currency.symbol(base))

    def budget_status(self, user_id, month=None, base=None):
        """Budget status for a month, shaped exactly like the Assignment 01 API."""
        month = month or datetime.now().strftime("%Y-%m")
        base = (base or self.users.base_currency(user_id)).upper()
        statuses, alerts = self.evaluate_budgets(user_id, month, base)
        return {"month": month,
                "status": [s.to_dict() for s in statuses],
                "alerts": [a.to_dict() for a in alerts],
                "currency": base, "symbol": self.currency.symbol(base)}

    def alert_for_category(self, user_id, month, category):
        """Alert dict for one category after an expense was added, or None.

        Uses exactly the same calculation as the dashboard, so the pop-up
        and the budget panel can no longer disagree.
        """
        base = self.users.base_currency(user_id)
        statuses, _ = self.evaluate_budgets(user_id, month, base)
        for status in statuses:
            if status.category == category:
                alert = self.calculator.alert_for(status)
                return alert.to_dict() if alert else None
        return None

    def monthly_summary(self, user_id, month):
        """Everything the dashboard shows for one month (base currency)."""
        base = self.users.base_currency(user_id)
        summary = self.analytics.category_summary(user_id, month, base=base)
        return {
            "month": month,
            "base_currency": base,
            "base_symbol": self.currency.symbol(base),
            "currencies": self.currency.supported_currencies(),
            "total_income": summary["total_income"],
            "total_expense": summary["total_expense"],
            "balance": round(summary["total_income"] - summary["total_expense"], 2),
            "by_category": summary["expense"],
            "by_currency": summary["by_currency"],
            "foreign_count": summary["foreign_count"],
            "budget": self.budget_status(user_id, month, base=base),
            "trend": self.analytics.monthly_trend(user_id, base=base),
        }
