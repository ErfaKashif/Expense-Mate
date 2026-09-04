"""
ExpenseMate -- Logic Layer (Layer 2: Business Logic)

Responsibility:
    * All business rules and calculations: adding income/expenses, monthly
      budgets, category-wise analytics, budget alerts, CSV import/export
      and multi-currency helpers.

This layer knows nothing about the HTTP server; it talks only to the
Database object injected into it (dependency inversion / testability).
"""

import csv
import io
import json
import re
from datetime import datetime

# --- Currency support (optional feature, simple static rates vs USD) -------
# Rates are "1 units of BASE equals X USD". For a real product this would be
# refreshed from an FX API; here we keep a small offline table to demonstrate
# the multi-currency capability without network access.
CURRENCY_RATES = {
    "USD": 1.00,
    "PKR": 0.0036,
    "EUR": 1.17,
    "GBP": 1.35,
    "INR": 0.012,
    "AED": 0.27,
    "SAR": 1.00 / 3.75,
}
DEFAULT_CURRENCIES = ["USD", "PKR"]

# Alert thresholds (fraction of budget)
WARN_RATIO = 0.80     # soft warning
CRITICAL_RATIO = 0.95  # hard alert

# Valid transaction types
TYPES = {"income", "expense"}


class ValidationError(Exception):
    """Raised when input data is invalid."""


class Logic:
    def __init__(self, db, rates=None):
        self.db = db
        self.rates = rates or CURRENCY_RATES

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _convert(self, amount, from_currency, to_currency):
        """Convert amount from one currency to another via USD."""
        from_rate = self.rates.get(from_currency, 1.0)
        to_rate = self.rates.get(to_currency, 1.0)
        return amount * (from_rate / to_rate)

    @staticmethod
    def _validate_amount(amount, type):
        if type not in TYPES:
            raise ValidationError(f"Invalid type '{type}'.")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValidationError("Amount must be a number.")
        if amount < 0:
            raise ValidationError("Amount cannot be negative.")
        return round(amount, 2)

    @staticmethod
    def _validate_date(date):
        try:
            datetime.strptime(date, "%Y-%m-%d")
            return date
        except (TypeError, ValueError):
            raise ValidationError("Date must be in YYYY-MM-DD format.")

    def _month(self, date):
        return date[:7]

    # ------------------------------------------------------------------ #
    # Transactions
    # ------------------------------------------------------------------ #
    def add_transaction(self, user_id, date, description, amount, type,
                        category=None, currency=None):
        """Validated add of an income/expense record. Returns new id."""
        user = self.db.get_user(user_id)
        if not user:
            raise ValidationError("User not found.")
        date = self._validate_date(date)
        amount = self._validate_amount(amount, type)
        currency = currency or user["base_currency"]
        if currency not in self.rates:
            raise ValidationError(f"Unsupported currency '{currency}'.")
        if not description or not description.strip():
            raise ValidationError("Description is required.")
        kind = type
        category = (category or "").strip() or ("Income" if type == "income" else "Misc")
        cat_id = self.db.ensure_category(category, kind)
        return self.db.add_transaction(user_id, date, description.strip(),
                                       amount, type, cat_id, currency)

    def delete_transaction(self, tx_id):
        if not self.db.delete_transaction(tx_id):
            raise ValidationError("Transaction not found.")

    # ------------------------------------------------------------------ #
    # Analytics (category-wise)
    # ------------------------------------------------------------------ #
    def category_summary(self, user_id, month=None):
        """Aggregate income & expense by category for a month or all time."""
        txs = self.db.list_transactions(user_id, month=month)
        out = {"income": {}, "expense": {}, "total_income": 0.0, "total_expense": 0.0}
        for t in txs:
            cat = t["category_name"] or "Misc"
            amt = t["amount"]
            if t["type"] == "income":
                out["income"][cat] = out["income"].get(cat, 0.0) + amt
                out["total_income"] += amt
            else:
                out["expense"][cat] = out["expense"].get(cat, 0.0) + amt
                out["total_expense"] += amt
        return out

    def balance(self, user_id, month=None):
        """Net balance (income - expense)."""
        c = self.category_summary(user_id, month)
        return round(c["total_income"] - c["total_expense"], 2)

    def monthly_trend(self, user_id, n_months=6):
        """Total income/expense for the last n months (with a month label)."""
        txs = self.db.list_transactions(user_id)
        buckets = {}
        for t in txs:
            m = self._month(t["date"])
            b = buckets.setdefault(m, {"income": 0.0, "expense": 0.0})
            b[t["type"]] += t["amount"]
        sorted_months = sorted(buckets.keys())[-n_months:]
        return [(m, round(buckets[m]["income"], 2), round(buckets[m]["expense"], 2))
                for m in sorted_months]

    # ------------------------------------------------------------------ #
    # Budgets & alerts (the "challenging part")
    # ------------------------------------------------------------------ #
    def set_budget(self, user_id, category, month, amount, currency=None):
        if not re.fullmatch(r"\d{4}-\d{2}", month):
            raise ValidationError("Month must be in YYYY-MM format.")
        amount = self._validate_amount(amount, "expense")
        user = self.db.get_user(user_id)
        currency = currency or user["base_currency"]
        cat_id = self.db.ensure_category(category.strip(), "expense")
        self.db.set_budget(user_id, cat_id, month, amount, currency)

    def budget_status(self, user_id, month=None):
        """Compute spent vs budget per category and raise alerts when over
        threshold. Returns a list of per-category status dicts + list of alerts."""
        month = month or datetime.now().strftime("%Y-%m")
        budgets = self.db.get_budgets(user_id, month)
        spent = self.category_summary(user_id, month)["expense"]
        status, alerts = [], []

        for b in budgets:
            cat = b["category_name"]
            limit = b["amount"]
            used = round(spent.get(cat, 0.0), 2)
            ratio = round(used / limit, 4) if limit else 0.0
            level = "ok"
            if ratio >= CRITICAL_RATIO:
                level = "critical"
            elif ratio >= WARN_RATIO:
                level = "warning"
            remaining = round(limit - used, 2)
            status.append({"category": cat, "limit": limit, "spent": used,
                           "remaining": remaining, "ratio": ratio, "level": level})
            if level == "critical":
                alerts.append({"category": cat, "level": level,
                               "message": f"You have exceeded {int(ratio*100)}% of the "
                                          f"budget for '{cat}' (spent {used} of {limit})."})
            elif level == "warning":
                alerts.append({"category": cat, "level": level,
                               "message": f"Budget for '{cat}' is at {int(ratio*100)}% "
                                          f"({used} of {limit})."})
        return {"month": month, "status": status, "alerts": alerts}

    # ------------------------------------------------------------------ #
    # CSV import / export (the other "challenging part")
    # ------------------------------------------------------------------ #
    def export_csv(self, user_id, month=None):
        csv_headers = ["date", "description", "amount", "type", "category", "currency"]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(csv_headers)
        for t in self.db.list_transactions(user_id, month=month):
            writer.writerow([t["date"], t["description"], t["amount"], t["type"],
                             t["category_name"] or "", t["currency"]])
        return buf.getvalue()

    def import_csv(self, user_id, raw_text):
        """Import transactions from a CSV string. Returns count imported."""
        reader = csv.DictReader(io.StringIO(raw_text))
        required = {"date", "description", "amount", "type"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValidationError("CSV must have columns: " + ", ".join(sorted(required)))
        count = 0
        for row in reader:
            try:
                self.add_transaction(
                    user_id,
                    row["date"], row["description"], row["amount"], row["type"],
                    category=row.get("category"), currency=row.get("currency") or None,
                )
                count += 1
            except ValidationError:
                # Skip malformed rows but keep importing the rest.
                continue
        return count

    # ------------------------------------------------------------------ #
    # Reporting / misc
    # ------------------------------------------------------------------ #
    def to_summary_json(self, user_id, month=None):
        """Aggregate view used by the UI/dashboard."""
        cat = self.category_summary(user_id, month)
        return {
            "month": month,
            "total_income": round(cat["total_income"], 2),
            "total_expense": round(cat["total_expense"], 2),
            "balance": self.balance(user_id, month),
            "by_category": cat["expense"],
            "budget": self.budget_status(user_id, month),
            "trend": self.monthly_trend(user_id),
        }
