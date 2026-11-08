"""Routes: /api/register, /api/login"""

from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token

from ._request import json_body


def create_auth_blueprint(user_service, currency_service):
    bp = Blueprint("auth", __name__, url_prefix="/api")

    @bp.post("/register")
    def register():
        data = json_body()
        user = user_service.register(data.get("username"), data.get("password"),
                                     data.get("base_currency"))
        return jsonify({
            "access_token": create_access_token(identity=str(user.id)),
            "user_id": user.id,
            "username": user.username,
            "base_currency": user.base_currency,
        }), 201

    @bp.post("/login")
    def login():
        data = json_body()
        user = user_service.authenticate(data.get("username"), data.get("password"))
        return jsonify({
            "access_token": create_access_token(identity=str(user.id)),
            "user_id": user.id,
            "username": user.username,
            "base_currency": user.base_currency,
            "base_symbol": currency_service.symbol(user.base_currency),
        })

    return bp
