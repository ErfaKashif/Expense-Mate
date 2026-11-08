"""
Application exceptions.

Services raise these; the controllers' error handlers translate them into
HTTP responses, so no service ever needs to know about HTTP status codes.

    ValidationError     -> 400 Bad Request
    AuthenticationError -> 401 Unauthorized
    NotFoundError       -> 404 Not Found
    ConflictError       -> 409 Conflict
"""


class ExpenseMateError(Exception):
    """Base class for all expected application errors."""


class ValidationError(ExpenseMateError):
    """Input data is invalid (bad amount, date, currency, ...)."""


class AuthenticationError(ExpenseMateError):
    """Username / password combination is wrong."""


class NotFoundError(ExpenseMateError):
    """The requested record does not exist (or belongs to another user)."""


class ConflictError(ExpenseMateError):
    """The record already exists (e.g. duplicate username)."""
