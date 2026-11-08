"""
CsvImporter: reads CSV text into plain row dictionaries.

REWRITE of the parsing half of Assignment 01 `Logic.import_csv`
(cyclomatic complexity 15). The old method parsed, validated, wrote to the
database and updated budgets row by row, each row in its own connection,
so a failure half-way left a partial import.

Now the work is split:
    CsvImporter.parse()       text -> rows        (this class, pure)
    ExpenseValidator          row  -> Transaction (pure)
    ExpenseService.import_csv saves all valid rows in ONE transaction
"""

import csv
import io
from dataclasses import dataclass, field

from ..utils.errors import ValidationError

REQUIRED_COLUMNS = ("amount", "date", "description", "type")
OPTIONAL_COLUMNS = ("category", "currency")


@dataclass
class ParsedCsv:
    rows: list = field(default_factory=list)   # dicts with the 6 known columns
    blank_rows: int = 0                         # rows with no date/description/amount


class CsvImporter:
    def parse(self, raw_text):
        """Parse CSV text. Raises ValidationError if required columns are missing."""
        if not isinstance(raw_text, str):
            raise ValidationError("CSV content must be text.")
        reader = csv.DictReader(io.StringIO(raw_text.lstrip("\ufeff")))   # Excel adds a BOM
        reader.fieldnames = self._checked_headers(reader.fieldnames)

        parsed = ParsedCsv()
        for raw_row in reader:
            row = {col: self._cell(raw_row, col) for col in REQUIRED_COLUMNS + OPTIONAL_COLUMNS}
            if self._is_blank(row):
                parsed.blank_rows += 1
            else:
                parsed.rows.append(row)
        return parsed

    @staticmethod
    def _checked_headers(fieldnames):
        """Lower-case, trimmed header names; all required columns must be present."""
        headers = [h.strip().lower() for h in fieldnames or [] if h]
        if not set(REQUIRED_COLUMNS).issubset(headers):
            raise ValidationError("CSV must have columns: " + ", ".join(REQUIRED_COLUMNS))
        return headers

    @staticmethod
    def _is_blank(row):
        return not any(row[col] for col in ("date", "description", "amount"))

    @staticmethod
    def _cell(row, column):
        """Trimmed cell text; missing/empty optional cells become None."""
        value = row.get(column)
        if not isinstance(value, str):    # missing column or extra-cell list
            return None if column in OPTIONAL_COLUMNS else ""
        value = value.strip()
        if column in OPTIONAL_COLUMNS and not value:
            return None
        return value
