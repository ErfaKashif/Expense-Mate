from dataclasses import asdict, dataclass


@dataclass
class Category:
    id: int
    name: str
    kind: str          # 'income' or 'expense'

    @classmethod
    def from_row(cls, row):
        return cls(id=row["id"], name=row["name"], kind=row["kind"])

    def to_dict(self):
        return asdict(self)
