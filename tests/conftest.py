"""Pytest fixtures — each test gets an isolated temporary database."""
import pytest

from app.backend.db import Database
from app.backend.logic import Logic


@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def logic(db):
    return Logic(db)


@pytest.fixture
def user(logic):
    return logic.db.create_user("tester", "x", "USD")
