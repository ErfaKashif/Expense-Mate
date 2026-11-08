"""Unit tests - CsvImporter (rewritten CSV parsing). No database."""
import os

import pytest

from app.backend.services.csv_importer import CsvImporter
from app.backend.utils.errors import ValidationError

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "..", "app", "sample_data",
                          "sample_expenses.csv")


@pytest.fixture
def importer():
    return CsvImporter()


def test_parses_rows_and_trims_cells(importer):
    parsed = importer.parse("date,description,amount,type,category,currency\n"
                            "2026-09-01, rice ,25,expense,Food,USD\n")
    assert parsed.rows == [{"date": "2026-09-01", "description": "rice", "amount": "25",
                            "type": "expense", "category": "Food", "currency": "USD"}]
    assert parsed.blank_rows == 0


def test_headers_are_case_and_space_insensitive_and_bom_removed(importer):
    parsed = importer.parse("﻿ Date ,DESCRIPTION,Amount,Type\n2026-09-01,a,1,income\n")
    assert parsed.rows[0]["date"] == "2026-09-01"
    assert parsed.rows[0]["category"] is None and parsed.rows[0]["currency"] is None


def test_missing_required_column_rejected(importer):
    with pytest.raises(ValidationError, match="amount, date, description, type"):
        importer.parse("foo,bar\n1,2\n")


def test_empty_text_rejected(importer):
    with pytest.raises(ValidationError):
        importer.parse("")


def test_blank_rows_counted(importer):
    parsed = importer.parse("date,description,amount,type\n,,,\n2026-09-01,a,1,expense\n")
    assert parsed.blank_rows == 1 and len(parsed.rows) == 1


def test_short_row_does_not_crash(importer):
    # Assignment 01 crashed with AttributeError ('NoneType'.strip) on short rows.
    parsed = importer.parse("date,description,amount,type\n2026-09-01,only two\n")
    assert parsed.rows[0]["amount"] == "" and parsed.rows[0]["type"] == ""


def test_non_text_rejected(importer):
    with pytest.raises(ValidationError):
        importer.parse(None)


def test_sample_file_parses(importer):
    with open(SAMPLE_CSV, encoding="utf-8") as fh:
        parsed = importer.parse(fh.read())
    assert len(parsed.rows) == 15 and parsed.blank_rows == 0
