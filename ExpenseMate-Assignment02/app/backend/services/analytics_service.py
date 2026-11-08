"""
Analytics service: category-wise summaries and the monthly trend.

All amounts are converted into the user's base currency so that a month
with USD + PKR + EUR records still produces a meaningful total. Native
(un-converted) per-currency totals are kept in `by_currency`.
"""


class AnalyticsService:
    def __init__(self, expense_repository, user_service, currency_service):
        self.expenses = expense_repository
        self.users = user_service
        self.currency = currency_service

    def category_summary(self, user_id, month=None, base=None):
        """Income and expense totals per category for one month (or all time)."""
        base = (base or self.users.base_currency(user_id)).upper()
        summary = {"income": {}, "expense": {}, "total_income": 0.0, "total_expense": 0.0,
                   "base_currency": base, "base_symbol": self.currency.symbol(base),
                   "by_currency": {}, "foreign_count": 0}

        for tx in self.expenses.list_for_user(user_id, month=month):
            category = tx.category_name or "Misc"
            native_currency = (tx.currency or base).upper()
            converted = self.currency.convert(tx.amount, native_currency, base)

            native = summary["by_currency"].setdefault(native_currency, {
                "symbol": self.currency.symbol(native_currency),
                "income": 0.0, "expense": 0.0, "count": 0})
            native[tx.type] += tx.amount
            native["count"] += 1
            if native_currency != base:
                summary["foreign_count"] += 1

            summary[tx.type][category] = summary[tx.type].get(category, 0.0) + converted
            summary["total_" + tx.type] += converted

        for kind in ("income", "expense"):
            summary[kind] = {name: round(v, 2) for name, v in summary[kind].items()}
            summary["total_" + kind] = round(summary["total_" + kind], 2)
        for native in summary["by_currency"].values():
            native["income"] = round(native["income"], 2)
            native["expense"] = round(native["expense"], 2)
        return summary

    def balance(self, user_id, month=None, base=None):
        """Net balance (income - expense) in the base currency."""
        summary = self.category_summary(user_id, month, base=base)
        return round(summary["total_income"] - summary["total_expense"], 2)

    def monthly_trend(self, user_id, n_months=6, base=None):
        """[(month, income, expense), ...] for the last `n_months` months with data."""
        base = (base or self.users.base_currency(user_id)).upper()
        buckets = {}
        for tx in self.expenses.list_for_user(user_id):
            bucket = buckets.setdefault(tx.month, {"income": 0.0, "expense": 0.0})
            bucket[tx.type] += self.currency.convert(tx.amount, (tx.currency or base).upper(), base)
        months = sorted(buckets)[-n_months:]
        return [(m, round(buckets[m]["income"], 2), round(buckets[m]["expense"], 2))
                for m in months]
