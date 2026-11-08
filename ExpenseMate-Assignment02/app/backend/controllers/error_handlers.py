"""Translate exceptions into JSON error responses ({"error": "..."})."""

import psycopg
from flask import jsonify

from ..database import DatabaseUnavailableError
from ..utils.errors import (
    AuthenticationError, ConflictError, NotFoundError, ValidationError,
)
from ..utils.logger import get_logger

log = get_logger(__name__)

_STATUS_BY_ERROR = {
    ValidationError: 400,
    AuthenticationError: 401,
    NotFoundError: 404,
    ConflictError: 409,
}


def register_error_handlers(app):
    for error_class, status in _STATUS_BY_ERROR.items():
        app.register_error_handler(
            error_class, lambda exc, status=status: (jsonify({"error": str(exc)}), status))

    @app.errorhandler(DatabaseUnavailableError)
    def database_unavailable(exc):
        return jsonify({"error": str(exc)}), 503

    @app.errorhandler(psycopg.Error)
    def database_error(exc):
        # Log the real cause for developers; never leak SQL details to users.
        log.exception("Database error: %s", exc)
        return jsonify({"error": "A database error occurred. Please try again."}), 500
