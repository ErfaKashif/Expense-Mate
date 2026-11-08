"""
Database configuration.

All connection settings come from environment variables so that no
credentials ever live in the source code or in Git.

    DATABASE_URL       PostgreSQL URL used by the running application
    TEST_DATABASE_URL  Separate PostgreSQL database used by the test-suite

Example (see .env.example):
    DATABASE_URL=postgresql://expensemate:<password>@localhost:5432/expensemate
"""

import os


class ConfigurationError(Exception):
    """Raised when a required configuration value is missing."""


def load_env_file():
    """Load variables from a local `.env` file if python-dotenv is installed.

    Values that are already set in the real environment are NOT overwritten,
    so deployment platforms (and CI) always win over the local file.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:  # dotenv is optional; plain env vars still work
        return
    load_dotenv(override=False)


def get_database_url(variable="DATABASE_URL"):
    """Return the PostgreSQL connection URL stored in `variable`."""
    url = os.environ.get(variable, "").strip()
    if not url:
        raise ConfigurationError(
            f"{variable} is not set. Copy .env.example to .env and fill in "
            f"your PostgreSQL connection details."
        )
    if not url.startswith(("postgresql://", "postgres://")):
        raise ConfigurationError(f"{variable} must be a postgresql:// URL.")
    return url


def mask_url(url):
    """Hide the password part of a URL so it can be logged safely."""
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    credentials, host = rest.rsplit("@", 1)
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:****@{host}"
