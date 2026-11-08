"""
Transaction model.

ExpenseMate stores both expenses and income in one `transactions` table;
`type` tells them apart. "Expense" in class/module names refers to this
ledger of money in and out, as in Assignment 01.
"""

from dataclasses import asdict, dataclass

from ._convert import to_float, to_iso_date, to_timestamp_text


@dataclass
class Transaction:
    user_id: int
    date: str                    # 'YYYY-MM-DD'
    description: str
    amount: float                # native amount, in `currency`
    type: str                    # 'income' or 'expense'
    currency: str = "USD"
    category_id: int | None = None
    category_name: str | None = None
    id: int | None = None
    created_at: str | None = None

    @property
    def month(self):
        """'YYYY-MM' of the transaction date."""
        return self.date[:7]

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"], user_id=row["user_id"], date=to_iso_date(row["date"]),
            description=row["description"], amount=to_float(row["amount"]),
            type=row["type"], currency=(row["currency"] or "USD").upper(),
            category_id=row.get("category_id"), category_name=row.get("category_name"),
            created_at=to_timestamp_text(row.get("created_at")),
        )

    def to_dict(self):
        """Same keys the Assignment 01 API returned for a transaction row."""
        return asdict(self)
