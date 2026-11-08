from dataclasses import dataclass

from ._convert import to_timestamp_text


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    base_currency: str = "USD"
    created_at: str | None = None

    @classmethod
    def from_row(cls, row):
        return cls(id=row["id"], username=row["username"], password_hash=row["password"],
                   base_currency=(row["base_currency"] or "USD").upper(),
                   created_at=to_timestamp_text(row.get("created_at")))
