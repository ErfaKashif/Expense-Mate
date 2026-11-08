"""Unit tests - Database connection/transaction manager with a mocked psycopg."""
from unittest.mock import MagicMock

import psycopg
import pytest

from app.backend.database import connection as connection_module
from app.backend.database.config import ConfigurationError, get_database_url, mask_url
from app.backend.database.connection import Database, DatabaseUnavailableError


@pytest.fixture
def fake_connect(monkeypatch):
    connections = []

    def _connect(*args, **kwargs):
        conn = MagicMock(name=f"conn{len(connections)}")
        connections.append(conn)
        return conn
    monkeypatch.setattr(connection_module.psycopg, "connect", _connect)
    return connections


def test_transaction_commits_and_closes(fake_connect):
    db = Database("postgresql://u:p@h/db_test")
    with db.transaction():
        pass
    conn = fake_connect[0]
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    conn.close.assert_called_once()


def test_transaction_rolls_back_on_error(fake_connect):
    db = Database("postgresql://u:p@h/db_test")
    with pytest.raises(RuntimeError):
        with db.transaction():
            raise RuntimeError("boom")
    conn = fake_connect[0]
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
    conn.close.assert_called_once()


def test_nested_transactions_share_one_connection(fake_connect):
    db = Database("postgresql://u:p@h/db_test")
    with db.transaction() as outer:
        with db.transaction() as inner:
            with db.cursor():
                pass
        assert inner is outer
    assert len(fake_connect) == 1
    fake_connect[0].commit.assert_called_once()


def test_error_in_nested_block_rolls_back_outer(fake_connect):
    db = Database("postgresql://u:p@h/db_test")
    with pytest.raises(ValueError):
        with db.transaction():
            with db.transaction():
                raise ValueError
    fake_connect[0].rollback.assert_called_once()


def test_unreachable_server_raises_database_unavailable(monkeypatch):
    def refuse(*a, **k):
        raise psycopg.OperationalError("connection refused")
    monkeypatch.setattr(connection_module.psycopg, "connect", refuse)
    with pytest.raises(DatabaseUnavailableError):
        with Database("postgresql://u:p@h/db").cursor():
            pass


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://a:b@localhost/x")
    assert get_database_url() == "postgresql://a:b@localhost/x"
    monkeypatch.setenv("DATABASE_URL", "")
    with pytest.raises(ConfigurationError):
        get_database_url()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
    with pytest.raises(ConfigurationError):
        get_database_url()


def test_mask_url_hides_password():
    assert mask_url("postgresql://me:s3cret@db:5432/x") == "postgresql://me:****@db:5432/x"
