"""
User service: registration, login and the user's reporting (base) currency.

In Assignment 01 the register/login routes in server.py queried the
database directly; that logic now lives here.
"""

import hashlib

from ..utils.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from .currency_service import DEFAULT_CURRENCY


def hash_password(password):
    """SHA-256 hex digest. Kept identical to Assignment 01 so that accounts
    migrated from SQLite can still log in (see 'unfinished work' in README)."""
    return hashlib.sha256(password.encode()).hexdigest()


class UserService:
    def __init__(self, user_repository, currency_service):
        self.users = user_repository
        self.currency = currency_service

    def register(self, username, password, base_currency=None):
        if not username or not password:
            raise ValidationError("username and password required")
        code = self.currency.normalise(base_currency or DEFAULT_CURRENCY)
        if self.users.get_by_username(username):
            raise ConflictError("user already exists")
        user_id = self.users.create(username, hash_password(password), code)
        return self.users.get_by_id(user_id)

    def authenticate(self, username, password):
        user = self.users.get_by_username(username or "")
        if not user or user.password_hash != hash_password(password or ""):
            raise AuthenticationError("invalid credentials")
        return user

    def get_user(self, user_id):
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")
        return user

    def base_currency(self, user_id):
        """The user's reporting currency (USD if the user does not exist)."""
        user = self.users.get_by_id(user_id) if user_id else None
        return user.base_currency if user else DEFAULT_CURRENCY

    def set_base_currency(self, user_id, currency):
        code = self.currency.normalise(currency)
        self.get_user(user_id)
        self.users.update_base_currency(user_id, code)
        return code
