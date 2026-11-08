"""Helpers that turn PostgreSQL values into the plain Python values the API uses."""

from datetime import date, datetime
from decimal import Decimal


def to_float(value):
    """NUMERIC columns arrive as Decimal; the API and calculations use float."""
    if value is None:
        return None
    return float(value) if isinstance(value, Decimal) else value


def to_iso_date(value):
    """DATE -> 'YYYY-MM-DD' (the format the frontend and CSV files use)."""
    return value.isoformat() if isinstance(value, date) else value


def to_timestamp_text(value):
    """TIMESTAMP -> 'YYYY-MM-DD HH:MM:SS' (same text format SQLite produced)."""
    return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value
