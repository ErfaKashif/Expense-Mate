import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from .db import Database
from .logic import Logic, ValidationError

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

import hashlib


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def create_app(db_path=None, testing=False):
    app = Flask(
        __name__,
        static_folder=os.path.join(FRONTEND_DIR, "static"),
        template_folder=FRONTEND_DIR,
        static_url_path="/static",
    )
    # Reads JWT_SECRET_KEY from .env (falls back to a default key if missing)
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "fallback-secret-key-for-dev")
    jwt = JWTManager(app)
    db = Database(db_path)
    logic = Logic(db)
    app.config["TESTING"] = testing

    # ================== STATIC / CLIENT =================================== #
    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    # ================== AUTH ============================================== #
    @app.post("/api/register")
    def register():
        d = request.get_json(silent=True) or {}
        if not d.get("username") or not d.get("password"):
            return jsonify({"error": "username and password required"}), 400
        if db.get_user_by_name(d["username"]):
            return jsonify({"error": "user already exists"}), 409
        try:
            base = logic._normalise(d.get("base_currency") or "USD")
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

        uid = db.create_user(d["username"], hash_password(d["password"]), base)
        access_token = create_access_token(identity=str(uid))

        return jsonify({
            "access_token": access_token,
            "user_id": uid,
            "username": d["username"],
            "base_currency": base
        }), 201

    @app.post("/api/login")
    def login():
        d = request.get_json(silent=True) or {}
        u = db.get_user_by_name(d.get("username", ""))
        if not u or u["password"] != hash_password(d.get("password", "")):
            return jsonify({"error": "invalid credentials"}), 401

        # Issue JWT Access Token with user ID as identity string
        access_token = create_access_token(identity=str(u["id"]))

        return jsonify({
            "access_token": access_token,
            "user_id": u["id"],
            "username": u["username"],
            "base_currency": (u["base_currency"] or "USD").upper(),
            "base_symbol": logic.symbol(u["base_currency"] or "USD"),
        })

    # ================== CATEGORIES ======================================== #
    @app.get("/api/categories")
    def categories():
        return jsonify(db.list_categories())

    # ================== MULTI-CURRENCY ==================================== #
    @app.get("/api/currencies")
    @jwt_required(optional=True)
    def currencies():
        uid_str = get_jwt_identity()
        uid = int(uid_str) if uid_str else None
        base = logic.base_currency(uid) if uid else "USD"
        table = logic.rates_table(base)
        return jsonify({
            "rates": logic.rates,
            "symbols": {c: logic.symbol(c) for c in logic.rates},
            "currencies": logic.supported_currencies(),
            "base_currency": base,
            "base_symbol": logic.symbol(base),
            "table": table["rates"],
        })

    @app.post("/api/convert")
    def convert_currency():
        d = request.get_json(silent=True) or {}
        try:
            frm = logic._normalise(d.get("from", "USD"))
            to = logic._normalise(d.get("to", "USD"))
            amount = float(d.get("amount", 0))
        except (ValidationError, TypeError, ValueError) as e:
            return jsonify({"error": str(e)}), 400
        result = round(logic.convert(amount, frm, to), 4)
        return jsonify({
            "amount": amount,
            "from": frm,
            "to": to,
            "result": result,
            "from_symbol": logic.symbol(frm),
            "to_symbol": logic.symbol(to),
        })

    @app.get("/api/settings")
    @jwt_required()
    def get_settings():
        uid = int(get_jwt_identity())
        return jsonify({
            "base_currency": logic.base_currency(uid),
            "base_symbol": logic.symbol(logic.base_currency(uid)),
            "currencies": logic.supported_currencies(),
        })

    @app.post("/api/settings/base_currency")
    @jwt_required()
    def set_base_currency():
        uid = int(get_jwt_identity())
        d = request.get_json(silent=True) or {}
        try:
            code = logic.set_base_currency(uid, d.get("base_currency"))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"ok": True, "base_currency": code, "base_symbol": logic.symbol(code)})

    # ================== TRANSACTIONS ====================================== #
    @app.get("/api/transactions")
    @jwt_required()
    def transactions():
        uid = int(get_jwt_identity())
        month = request.args.get("month")
        return jsonify(logic.transactions_view(uid, month=month))

    @app.post("/api/transactions")
    @jwt_required()
    def add_transaction():
        d = request.json or {}
        uid = int(get_jwt_identity())

        tx_id, alert = logic.add_transaction(
            user_id=uid,
            date=d.get("date"),
            description=d.get("description"),
            amount=d.get("amount"),
            type=d.get("type"),
            category=d.get("category"),
            currency=d.get("currency"),
        )

        return jsonify({
            "status": "success",
            "id": tx_id,
            "alert": alert
        }), 201

    @app.delete("/api/transactions/<int:tid>")
    @jwt_required()
    def delete_transaction(tid):
        uid = int(get_jwt_identity())
        try:
            logic.delete_transaction(uid, tid)
            return jsonify({"ok": True})
        except ValidationError as e:
            return jsonify({"error": str(e)}), 404

    # ================== BUDGETS & ANALYTICS ============================== #
    @app.get("/api/summary")
    @jwt_required()
    def summary():
        uid = int(get_jwt_identity())
        month = request.args.get("month") or datetime.now().strftime("%Y-%m")
        return jsonify(logic.to_summary_json(uid, month))

    @app.post("/api/budgets")
    @jwt_required()
    def set_budget():
        uid = int(get_jwt_identity())
        d = request.get_json(silent=True) or {}
        try:
            logic.set_budget(uid, d.get("category"), d.get("month"),
                             d.get("amount"), d.get("currency"))
            return jsonify({"ok": True}), 201
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/budgets/by-category", methods=["DELETE"])
    @jwt_required()
    def delete_budget_by_category_route():
        uid = int(get_jwt_identity())
        d = request.json or {}
        category_name = d.get("category")
        month = d.get("month")
        if not category_name or not month:
            return jsonify({"error": "Missing parameters"}), 400
        success = logic.delete_budget_by_category(uid, month, category_name)
        if success:
            return jsonify({"status": "success", "message": "Budget deleted successfully."}), 200
        return jsonify({"error": "Budget record not found."}), 404

    # ================== CSV ============================================== #
    @app.get("/api/export")
    @jwt_required()
    def export_csv():
        uid = int(get_jwt_identity())
        csv_text = logic.export_csv(uid, request.args.get("month"))
        return app.response_class(
            csv_text,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=expenses.csv"},
        )

    @app.post("/api/import")
    @jwt_required()
    def import_csv():
        uid = int(get_jwt_identity())
        d = request.get_json(silent=True) or {}
        try:
            imported_count, skipped_count = logic.import_csv(uid, d.get("csv", ""))
            return jsonify({"imported": imported_count, "skipped": skipped_count})
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

    return app


def main():
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


if __name__ == "__main__":
    main()