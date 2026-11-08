"""Small helpers shared by all controllers."""

from flask import request
from flask_jwt_extended import get_jwt_identity

from ..utils.errors import ValidationError


def json_body():
    """The request's JSON object, or {} if the body is missing.

    A body that is valid JSON but not an object (e.g. a list) is rejected.
    """
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    return data


def require_fields(data, *names):
    """Basic presence check, done in the controller before calling a service."""
    missing = [n for n in names if data.get(n) in (None, "")]
    if missing:
        raise ValidationError("Missing required field(s): " + ", ".join(missing))


def current_user_id():
    """User id stored in the JWT (the token identity is a string)."""
    return int(get_jwt_identity())
