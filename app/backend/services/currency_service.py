"""
Currency service: exchange rates, conversion and display symbols.

Pure business logic with no database access. Moved out of the Assignment 01
`Logic` class, where it was mixed with expenses, budgets and CSV handling.

Conversion pivots through USD:  amount * (rate[from] / rate[to]),
where rate[X] = value of one unit of X in US dollars.
"""

from ..utils.errors import ValidationError

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


class CurrencyService:
    def __init__(self, rates=None):
        self.rates = dict(rates or CURRENCY_RATES)

    def supported_currencies(self):
        """Sorted list of currency codes the system understands."""
        return sorted(self.rates.keys())

    def normalise(self, currency):
        """Validate and upper-case a currency code (raises ValidationError)."""
        code = (currency or "").strip().upper() if isinstance(currency, str) else ""
        if code not in self.rates:
            raise ValidationError(f"Unsupported currency '{currency}'.")
        return code

    def convert(self, amount, from_currency, to_currency):
        """Convert `amount` between currencies, pivoting via USD."""
        rate_from = self.rates.get((from_currency or DEFAULT_CURRENCY).upper(), 1.0)
        rate_to = self.rates.get((to_currency or DEFAULT_CURRENCY).upper(), 1.0)
        return amount * (rate_from / rate_to)

    def symbol(self, currency):
        code = (currency or DEFAULT_CURRENCY).upper()
        return CURRENCY_SYMBOLS.get(code, code)

    def symbols(self):
        return {code: self.symbol(code) for code in self.rates}

    def rates_table(self, base=None):
        """For the UI: 1 unit of each currency in `base`, and 1 `base` in each currency."""
        base = (base or DEFAULT_CURRENCY).upper()
        rows = []
        for code in self.supported_currencies():
            rows.append({
                "code": code,
                "name": CURRENCY_NAMES.get(code, code),
                "symbol": self.symbol(code),
                "usd_rate": round(self.rates[code], 6),
                "per_base": round(self.convert(1.0, code, base), 6),
                "one_base_equals": round(self.convert(1.0, base, code), 4),
            })
        return {"base": base, "base_symbol": self.symbol(base), "rates": rows}
