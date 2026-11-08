from dataclasses import dataclass

from ._convert import to_float


@dataclass
class Budget:
    """A monthly spending limit for one category, in `currency`."""
    user_id: int
    category_id: int
    month: str                    # 'YYYY-MM'
    amount: float
    currency: str = "USD"
    category_name: str | None = None
    id: int | None = None
    remaining_amount: float | None = None

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"], user_id=row["user_id"], category_id=row["category_id"],
            category_name=row.get("category_name"), month=row["month"],
            amount=to_float(row["amount"]),
            remaining_amount=to_float(row.get("remaining_amount")),
            currency=(row["currency"] or "USD").upper(),
        )


@dataclass
class BudgetStatus:
    """How one budget stands this month (all money in the reporting currency)."""
    category: str
    limit: float
    spent: float
    remaining: float
    ratio: float                  # spent / limit, e.g. 0.85 = 85 %
    level: str                    # 'ok' | 'warning' | 'critical'
    currency: str                 # reporting (base) currency
    symbol: str
    budget_currency: str          # currency the budget was set in
    budget_amount_native: float   # the budget amount in budget_currency
    converted: bool               # True if budget_currency != currency

    def to_dict(self):
        return dict(self.__dict__)


@dataclass
class BudgetAlert:
    category: str
    level: str                    # 'warning' | 'critical'
    message: str

    def to_dict(self):
        return dict(self.__dict__)
