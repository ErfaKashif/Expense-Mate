"""
ExpenseMate -- Logic Layer (Layer 2: Business Logic)

Responsibility:
    * All business rules and calculations: adding income/expenses, monthly
      budgets, category-wise analytics, budget alerts, CSV import/export
      and FULL multi-currency support.

This layer knows nothing about the HTTP server; it talks only to the
Database object injected into it (dependency inversion / testability).

MULTI-CURRENCY MODEL
--------------------
* Every transaction stores the currency it was entered in (native amount).
* Every user has a `base_currency` (their reporting currency).
* All analytics (totals, per-category sums, trend, budget comparisons) are
  CONVERTED into the user's base currency, so mixing USD + PKR + EUR in one
  month produces a correct, meaningful total.
* Conversion goes through USD as the pivot:  amount * (rate[from] / rate[to])
  where rate[X] = how many USD one unit of X is worth.
* Native (un-converted) totals are still reported in `by_currency` so the UI
  can show "you spent 5,000 PKR + 100 USD" alongside the converted total.
"""

import csv
import io
import json
import re
from datetime import datetime

# --- Currency support -------------------------------------------------------
# rate[X] = value of 1 unit of X expressed in USD (USD is the pivot currency).
# For a real product this would be refreshed from an FX API; we keep an offline
# table so the app works with no network access (and is fully testable).
CURRENCY_RATES = {
    "USD": 1.00,          # US Dollar          (pivot)
    "PKR": 0.0036,        # Pakistani Rupee
    "EUR": 1.08,          # Euro
    "GBP": 1.27,          # British Pound
    "INR": 0.0120,        # Indian Rupee
    "AED": 0.2723,        # UAE Dirham
    "SAR": 0.2666,        # Saudi Riyal
    "QAR": 0.2747,        # Qatari Riyal
    "KWD": 3.2500,        # Kuwaiti Dinar
    "OMR": 2.5974,        # Omani Rial
    "CAD": 0.7300,        # Canadian Dollar
    "AUD": 0.6600,        # Australian Dollar
    "SGD": 0.7400,        # Singapore Dollar
    "MYR": 0.2130,        # Malaysian Ringgit
    "BDT": 0.0091,        # Bangladeshi Taka
    "TRY": 0.0290,        # Turkish Lira
    "JPY": 0.0067,        # Japanese Yen
    "CNY": 0.1390,        # Chinese Yuan
    "ZAR": 0.0540,        # South African Rand
    "CHF": 1.1300,        # Swiss Franc
}

# Display symbols per currency (used by the UI).
CURRENCY_SYMBOLS = {
    "USD": "$", "PKR": "Rs", "EUR": "\u20ac", "GBP": "\u00a3", "INR": "\u20b9",
    "AED": "AED", "SAR": "SAR", "QAR": "QAR", "KWD": "KWD", "OMR": "OMR",
    "CAD": "C$", "AUD": "A$", "SGD": "S$", "MYR": "RM", "BDT": "\u09f3",
    "TRY": "\u20ba", "JPY": "\u00a5", "CNY": "\u00a5", "ZAR": "R", "CHF": "CHF",
}

# Human-readable names (used by the UI rate table).
CURRENCY_NAMES = {
    "USD": "US Dollar", "PKR": "Pakistani Rupee", "EUR": "Euro",
    "GBP": "British Pound", "INR": "Indian Rupee", "AED": "UAE Dirham",
    "SAR": "Saudi Riyal", "QAR": "Qatari Riyal", "KWD": "Kuwaiti Dinar",
    "OMR": "Omani Rial", "CAD": "Canadian Dollar", "AUD": "Australian Dollar",
    "SGD": "Singapore Dollar", "MYR": "Malaysian Ringgit", "BDT": "Bangladeshi Taka",
    "TRY": "Turkish Lira", "JPY": "Japanese Yen", "CNY": "Chinese Yuan",
    "ZAR": "South African Rand", "CHF": "Swiss Franc",
}

DEFAULT_CURRENCY = "USD"
DEFAULT_CURRENCIES = ["USD", "PKR", "EUR", "GBP", "INR", "AED", "SAR"]

# Alert thresholds (fraction of budget)
WARN_RATIO = 0.80      # soft warning
CRITICAL_RATIO = 0.95  # hard alert

# Valid transaction types
TYPES = {"income", "expense"}


class ValidationError(Exception):
    """Raised when input data is invalid."""


class Logic:
    def __init__(self, db, rates=None):
        self.db = db
        self.rates = dict(rates or CURRENCY_RATES)

    # ------------------------------------------------------------------ #
    # MULTI-CURRENCY helpers
    # ------------------------------------------------------------------ #
    def supported_currencies(self):
        """Sorted list of currency codes the system understands."""
        return sorted(self.rates.keys())

    def is_supported(self, currency):
        return bool(currency) and str(currency).upper() in self.rates

    def _normalise(self, currency):
        """Validate + upper-case a currency code."""
        code = (currency or "").strip().upper()
        if code not in self.rates:
            raise ValidationError(f"Unsupported currency '{currency}'.")
        return code

    def convert(self, amount, from_currency, to_currency):
        """Convert `amount` from one currency to another, pivoting via USD."""
        frm = self.rates.get((from_currency or DEFAULT_CURRENCY).upper(), 1.0)
        to = self.rates.get((to_currency or DEFAULT_CURRENCY).upper(), 1.0)
        return amount * (frm / to)

    # Backwards-compatible private alias (older tests/callers use _convert).
    def _convert(self, amount, from_currency, to_currency):
        return self.convert(amount, from_currency, to_currency)

    def symbol(self, currency):
        return CURRENCY_SYMBOLS.get((currency or DEFAULT_CURRENCY).upper(),
                                    (currency or DEFAULT_CURRENCY).upper())

    def base_currency(self, user_id):
        """The reporting currency for a user (falls back to USD)."""
        user = self.db.get_user(user_id)
        if not user:
            return DEFAULT_CURRENCY
        return (user["base_currency"] or DEFAULT_CURRENCY).upper()

    def set_base_currency(self, user_id, currency):
        """Change the user's reporting currency (adaptive maintenance feature)."""
        code = self._normalise(currency)
        if not self.db.get_user(user_id):
            raise ValidationError("User not found.")
        self.db.update_user(user_id, base_currency=code)
        return code

    def rates_table(self, base=None):
        """Rate table for the UI: 1 unit of each currency in `base`, plus
        how many units of that currency equal 1 `base`."""
        base = (base or DEFAULT_CURRENCY).upper()
        rows = []
        for code in self.supported_currencies():
            per_base = self.convert(1.0, code, base)          # 1 CODE = ? BASE
            inverse = self.convert(1.0, base, code)           # 1 BASE = ? CODE
            rows.append({
                "code": code,
                "name": CURRENCY_NAMES.get(code, code),
                "symbol": self.symbol(code),
                "usd_rate": round(self.rates[code], 6),
                "per_base": round(per_base, 6),
                "one_base_equals": round(inverse, 4),
            })
        return {"base": base, "base_symbol": self.symbol(base), "rates": rows}

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #
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
        currency = self._normalise(currency or user["base_currency"])
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

    def transactions_view(self, user_id, month=None, type=None):
        """Transaction rows annotated with the amount converted to base
        currency -- this is what the UI table renders."""
        base = self.base_currency(user_id)
        rows = self.db.list_transactions(user_id, month=month, type=type)
        for t in rows:
            t["base_currency"] = base
            t["base_symbol"] = self.symbol(base)
            t["currency_symbol"] = self.symbol(t["currency"] or base)
            t["amount_base"] = round(self.convert(t["amount"], t["currency"], base), 2)
            t["is_foreign"] = (t["currency"] or base).upper() != base
        return rows

    # ------------------------------------------------------------------ #
    # Analytics (category-wise) -- CONVERTED into the user's base currency
    # ------------------------------------------------------------------ #
    def category_summary(self, user_id, month=None, base=None):
        """Aggregate income & expense by category for a month or all time.

        Every amount is converted into `base` (default: the user's base
        currency) so totals are meaningful when several currencies are mixed.
        Native per-currency totals are kept in `by_currency`.
        """
        base = (base or self.base_currency(user_id)).upper()
        txs = self.db.list_transactions(user_id, month=month)
        out = {"income": {}, "expense": {}, "total_income": 0.0, "total_expense": 0.0,
               "base_currency": base, "base_symbol": self.symbol(base),
               "by_currency": {}, "foreign_count": 0}
        for t in txs:
            cat = t["category_name"] or "Misc"
            cur = (t["currency"] or base).upper()
            native = float(t["amount"])
            amt = self.convert(native, cur, base)

            # native (un-converted) breakdown, purely informational
            bc = out["by_currency"].setdefault(
                cur, {"symbol": self.symbol(cur), "income": 0.0, "expense": 0.0, "count": 0})
            bc[t["type"]] += native
            bc["count"] += 1
            if cur != base:
                out["foreign_count"] += 1

            if t["type"] == "income":
                out["income"][cat] = out["income"].get(cat, 0.0) + amt
                out["total_income"] += amt
            else:
                out["expense"][cat] = out["expense"].get(cat, 0.0) + amt
                out["total_expense"] += amt

        # round for stable output / display
        for key in ("income", "expense"):
            out[key] = {k: round(v, 2) for k, v in out[key].items()}
        out["total_income"] = round(out["total_income"], 2)
        out["total_expense"] = round(out["total_expense"], 2)
        for cur in out["by_currency"].values():
            cur["income"] = round(cur["income"], 2)
            cur["expense"] = round(cur["expense"], 2)
        return out

    def balance(self, user_id, month=None, base=None):
        """Net balance (income - expense) in the base currency."""
        c = self.category_summary(user_id, month, base=base)
        return round(c["total_income"] - c["total_expense"], 2)

    def monthly_trend(self, user_id, n_months=6, base=None):
        """Total income/expense for the last n months, converted to base."""
        base = (base or self.base_currency(user_id)).upper()
        txs = self.db.list_transactions(user_id)
        buckets = {}
        for t in txs:
            m = self._month(t["date"])
            b = buckets.setdefault(m, {"income": 0.0, "expense": 0.0})
            b[t["type"]] += self.convert(float(t["amount"]),
                                         (t["currency"] or base).upper(), base)
        sorted_months = sorted(buckets.keys())[-n_months:]
        return [(m, round(buckets[m]["income"], 2), round(buckets[m]["expense"], 2))
                for m in sorted_months]

    # ------------------------------------------------------------------ #
    # Budgets & alerts (the "challenging part") -- currency aware
    # ------------------------------------------------------------------ #
    def set_budget(self, user_id, category, month, amount, currency=None):
        if not re.fullmatch(r"\d{4}-\d{2}", month):
            raise ValidationError("Month must be in YYYY-MM format.")
        amount = self._validate_amount(amount, "expense")
        user = self.db.get_user(user_id)
        if not user:
            raise ValidationError("User not found.")
        currency = self._normalise(currency or user["base_currency"])
        cat_id = self.db.ensure_category(category.strip(), "expense")
        self.db.set_budget(user_id, cat_id, month, amount, currency)

    def budget_status(self, user_id, month=None, base=None):
        """Compute spent vs budget per category and raise alerts when over
        threshold.

        Budgets may be set in a different currency than the spending, so both
        sides are converted into the user's base currency before comparing.
        Returns per-category status dicts + a list of alert messages.
        """
        month = month or datetime.now().strftime("%Y-%m")
        base = (base or self.base_currency(user_id)).upper()
        symbol = self.symbol(base)
        budgets = self.db.get_budgets(user_id, month)
        spent = self.category_summary(user_id, month, base=base)["expense"]
        status, alerts = [], []

        for b in budgets:
            cat = b["category_name"]
            b_cur = (b.get("currency") or base).upper()
            limit = round(self.convert(float(b["amount"]), b_cur, base), 2)
            used = round(spent.get(cat, 0.0), 2)
            ratio = round(used / limit, 4) if limit else 0.0
            level = "ok"
            if ratio >= CRITICAL_RATIO:
                level = "critical"
            elif ratio >= WARN_RATIO:
                level = "warning"
            remaining = round(limit - used, 2)
            status.append({"category": cat, "limit": limit, "spent": used,
                           "remaining": remaining, "ratio": ratio, "level": level,
                           "currency": base, "symbol": symbol,
                           "budget_currency": b_cur,
                           "budget_amount_native": float(b["amount"]),
                           "converted": b_cur != base})
            if level == "critical":
                alerts.append({"category": cat, "level": level,
                               "message": f"You have exceeded {int(ratio*100)}% of the "
                                          f"budget for '{cat}' (spent {symbol}{used} of "
                                          f"{symbol}{limit})."})
            elif level == "warning":
                alerts.append({"category": cat, "level": level,
                               "message": f"Budget for '{cat}' is at {int(ratio*100)}% "
                                          f"({symbol}{used} of {symbol}{limit})."})
        return {"month": month, "status": status, "alerts": alerts,
                "currency": base, "symbol": symbol}

    # ------------------------------------------------------------------ #
    # CSV import / export
    # ------------------------------------------------------------------ #
    def export_csv(self, user_id, month=None):
        """Export native amounts + their currency, and the converted base amount."""
        base = self.base_currency(user_id)
        csv_headers = ["date", "description", "amount", "type", "category",
                       "currency", f"amount_in_{base}"]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(csv_headers)
        for t in self.db.list_transactions(user_id, month=month):
            writer.writerow([t["date"], t["description"], t["amount"], t["type"],
                             t["category_name"] or "", t["currency"],
                             round(self.convert(float(t["amount"]),
                                                (t["currency"] or base).upper(), base), 2)])
        return buf.getvalue()

    def import_csv(self, user_id, raw_text):
        """Import transactions from a CSV string. Returns (imported, skipped).

        Each row may carry its own `currency` column; rows without one default
        to the user's base currency. Malformed rows are skipped, not fatal.
        """
        reader = csv.DictReader(io.StringIO(raw_text))
        required = {"date", "description", "amount", "type"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValidationError("CSV must have columns: " + ", ".join(sorted(required)))
        count = 0
        skipped = 0
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
                skipped += 1
                continue
        return count

    # ------------------------------------------------------------------ #
    # Reporting / misc
    # ------------------------------------------------------------------ #
    def to_summary_json(self, user_id, month=None):
        """Aggregate view used by the UI/dashboard (all values in base currency)."""
        base = self.base_currency(user_id)
        cat = self.category_summary(user_id, month, base=base)
        return {
            "month": month,
            "base_currency": base,
            "base_symbol": self.symbol(base),
            "currencies": self.supported_currencies(),
            "total_income": cat["total_income"],
            "total_expense": cat["total_expense"],
            "balance": round(cat["total_income"] - cat["total_expense"], 2),
            "by_category": cat["expense"],
            "by_currency": cat["by_currency"],
            "foreign_count": cat["foreign_count"],
            "budget": self.budget_status(user_id, month, base=base),
            "trend": self.monthly_trend(user_id, base=base),
        }
