"""
Shared pytest fixtures.

Unit tests (tests/unit) use mocks and need no database.

Integration and regression tests use a SEPARATE PostgreSQL database given by
TEST_DATABASE_URL (from the environment or .env). Every table is emptied
before each test, so tests never see each other's data and never touch the
real application database. As a safety guard the tests refuse to run if the
test database name does not contain "test" or equals DATABASE_URL.
"""

import os
import sys
from urllib.parse import urlparse

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.backend.database import (  # noqa: E402
    TABLES, Database, DatabaseUnavailableError, apply_migrations, load_env_file,
)
from app.backend.server import build_services, create_app  # noqa: E402

load_env_file()


def _test_database_url():
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set - skipping PostgreSQL tests")
    db_name = urlparse(url).path.lstrip("/")
    if "test" not in db_name.lower():
        pytest.exit(f"Refusing to run: test database '{db_name}' does not contain 'test'.")
    if url == os.environ.get("DATABASE_URL"):
        pytest.exit("Refusing to run: TEST_DATABASE_URL is the same as DATABASE_URL.")
    return url


@pytest.fixture(scope="session")
def database_url():
    return _test_database_url()


@pytest.fixture(scope="session")
def database(database_url):
    db = Database(database_url)
    try:
        apply_migrations(db)
    except DatabaseUnavailableError as exc:
        pytest.skip(f"PostgreSQL test database unavailable: {exc}")
    return db


@pytest.fixture
def clean_db(database):
    """Empty every table (and reset ids) before the test runs."""
    with database.cursor() as cur:
        cur.execute("TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")
    return database


@pytest.fixture
def services(clean_db):
    return build_services(clean_db)


@pytest.fixture
def user(services):
    """Id of a fresh USD user called 'tester'."""
    return services["users"].register("tester", "x", "USD").id


@pytest.fixture
def client(clean_db, database_url):
    app = create_app(database_url, testing=True)
    return app.test_client()


@pytest.fixture
def login(client):
    """login(name, pw) -> Authorization headers for a newly registered user."""
    def _login(name="demo", pw="pw", base_currency=None):
        body = {"username": name, "password": pw}
        if base_currency:
            body["base_currency"] = base_currency
        client.post("/api/register", json=body)
        token = client.post("/api/login", json={"username": name, "password": pw}
                            ).get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _login
