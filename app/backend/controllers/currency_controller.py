"""Routes: /api/currencies, /api/convert, /api/settings, /api/settings/base_currency"""

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..utils.errors import ValidationError
from ._request import current_user_id, json_body


def create_currency_blueprint(user_service, currency_service):
    bp = Blueprint("currency", __name__, url_prefix="/api")

    @bp.get("/currencies")
    @jwt_required(optional=True)
    def currencies():
        identity = get_jwt_identity()
        base = user_service.base_currency(int(identity)) if identity else "USD"
        return jsonify({
            "rates": currency_service.rates,
            "symbols": currency_service.symbols(),
            "currencies": currency_service.supported_currencies(),
            "base_currency": base,
            "base_symbol": currency_service.symbol(base),
            "table": currency_service.rates_table(base)["rates"],
        })

    @bp.post("/convert")
    def convert():
        data = json_body()
        source = currency_service.normalise(data.get("from", "USD"))
        target = currency_service.normalise(data.get("to", "USD"))
        try:
            amount = float(data.get("amount", 0))
        except (TypeError, ValueError):
            raise ValidationError("Amount must be a number.") from None
        return jsonify({
            "amount": amount, "from": source, "to": target,
            "result": round(currency_service.convert(amount, source, target), 4),
            "from_symbol": currency_service.symbol(source),
            "to_symbol": currency_service.symbol(target),
        })

    @bp.get("/settings")
    @jwt_required()
    def get_settings():
        base = user_service.base_currency(current_user_id())
        return jsonify({
            "base_currency": base,
            "base_symbol": currency_service.symbol(base),
            "currencies": currency_service.supported_currencies(),
        })

    @bp.post("/settings/base_currency")
    @jwt_required()
    def set_base_currency():
        code = user_service.set_base_currency(current_user_id(),
                                              json_body().get("base_currency"))
        return jsonify({"ok": True, "base_currency": code,
                        "base_symbol": currency_service.symbol(code)})

    return bp
