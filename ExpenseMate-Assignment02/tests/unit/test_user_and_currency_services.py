"""Unit tests - UserService (mocked repository) and CurrencyService (pure)."""
from unittest.mock import MagicMock

import pytest

from app.backend.models import User
from app.backend.services.currency_service import CurrencyService
from app.backend.services.user_service import UserService, hash_password
from app.backend.utils.errors import (
    AuthenticationError, ConflictError, NotFoundError, ValidationError,
)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def users(repo):
    return UserService(repo, CurrencyService())


def test_register_hashes_password_and_normalises_currency(users, repo):
    repo.get_by_username.return_value = None
    repo.create.return_value = 5
    repo.get_by_id.return_value = User(5, "a", "h", "PKR")
    assert users.register("a", "secret", "pkr").id == 5
    repo.create.assert_called_once_with("a", hash_password("secret"), "PKR")


def test_register_duplicate_and_invalid(users, repo):
    repo.get_by_username.return_value = User(1, "a", "h")
    with pytest.raises(ConflictError):
        users.register("a", "pw")
    with pytest.raises(ValidationError):
        users.register("", "pw")
    with pytest.raises(ValidationError):
        users.register("b", "pw", "XYZ")


def test_authenticate(users, repo):
    repo.get_by_username.return_value = User(1, "a", hash_password("pw"))
    assert users.authenticate("a", "pw").id == 1
    with pytest.raises(AuthenticationError):
        users.authenticate("a", "wrong")
    repo.get_by_username.return_value = None
    with pytest.raises(AuthenticationError):
        users.authenticate("ghost", "pw")


def test_base_currency_and_switch(users, repo):
    repo.get_by_id.return_value = User(1, "a", "h", "EUR")
    assert users.base_currency(1) == "EUR"
    assert users.set_base_currency(1, "gbp") == "GBP"
    repo.update_base_currency.assert_called_once_with(1, "GBP")
    repo.get_by_id.return_value = None
    assert users.base_currency(1) == "USD"
    with pytest.raises(NotFoundError):
        users.set_base_currency(1, "GBP")


def test_currency_conversion_and_table():
    c = CurrencyService()
    assert c.convert(100, "USD", "PKR") == pytest.approx(100 / 0.0036)
    assert c.convert(c.convert(250, "PKR", "USD"), "USD", "PKR") == pytest.approx(250)
    assert c.normalise(" eur ") == "EUR" and c.symbol("PKR") == "Rs"
    for bad in ("XYZ", "", None, 5):
        with pytest.raises(ValidationError):
            c.normalise(bad)
    pkr = next(r for r in c.rates_table("USD")["rates"] if r["code"] == "PKR")
    assert pkr["name"] == "Pakistani Rupee" and pkr["one_base_equals"] > 100
