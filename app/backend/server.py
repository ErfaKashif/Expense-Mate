"""
ExpenseMate -- Client-Server / Presentation Layer (Layer 1)

The 'server' process exposes a small REST API and serves the single-page
'browser client' (the frontend/ folder is the Client). The SQLite database
lives on the server side only -- this is a classic local client-server
architecture:  Browser (Client)  ->  HTTP/REST  ->  Flask (Server)  ->  SQLite
"""

import os
import json
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory

from .db import Database
from .logic import Logic, ValidationError

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# A tiny in-memory session store would not be "real"; however, to keep the
# demo self-contained and dependency-free we use a simple token = user_id.
# In production replace with JWT + hashed passwords. Passwords are hashed here.
import hashlib


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def create_app(db_path=None, testing=False):
    app = Flask(__name__, static_folder=os.path.join(FRONTEND_DIR, "static"),
                template_folder=FRONTEND_DIR, static_url_path="/static")
    db = Database(db_path)
    logic = Logic(db)
    app.config["TESTING"] = testing

    # -- helpers: fake auth token = plain user id for the demo ------------- #
    def _uid():
        token = request.headers.get("X-User-Id") or request.args.get("uid")
        return int(token) if token else None

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
        return jsonify({"user_id": uid, "username": d["username"],
                        "base_currency": base}), 201

    @app.post("/api/login")
    def login():
        d = request.get_json(silent=True) or {}
        u = db.get_user_by_name(d.get("username", ""))
        if not u or u["password"] != hash_password(d.get("password", "")):
            return jsonify({"error": "invalid credentials"}), 401
        return jsonify({"user_id": u["id"], "username": u["username"],
                        "base_currency": (u["base_currency"] or "USD").upper(),
                        "base_symbol": logic.symbol(u["base_currency"] or "USD")})

    # ================== CATEGORIES ======================================== #
    @app.get("/api/categories")
    def categories():
        return jsonify(db.list_categories())

    # ================== MULTI-CURRENCY ==================================== #
    @app.get("/api/currencies")
    def currencies():
        """Rate table + symbols + the caller's base currency (if logged in)."""
        uid = _uid()
        base = logic.base_currency(uid) if uid else "USD"
        table = logic.rates_table(base)
        return jsonify({"rates": logic.rates,              # kept for back-compat
                        "symbols": {c: logic.symbol(c) for c in logic.rates},
                        "currencies": logic.supported_currencies(),
                        "base_currency": base,
                        "base_symbol": logic.symbol(base),
                        "table": table["rates"]})

    @app.post("/api/convert")
    def convert_currency():
        """Quick converter used by the Currency panel in the UI."""
        d = request.get_json(silent=True) or {}
        try:
            frm = logic._normalise(d.get("from", "USD"))
            to = logic._normalise(d.get("to", "USD"))
            amount = float(d.get("amount", 0))
        except (ValidationError, TypeError, ValueError) as e:
            return jsonify({"error": str(e)}), 400
        result = round(logic.convert(amount, frm, to), 4)
        return jsonify({"amount": amount, "from": frm, "to": to, "result": result,
                        "from_symbol": logic.symbol(frm), "to_symbol": logic.symbol(to)})

    @app.get("/api/settings")
    def get_settings():
        uid = _uid()
        if not uid:
            return jsonify({"error": "not authorized"}), 401
        return jsonify({"base_currency": logic.base_currency(uid),
                        "base_symbol": logic.symbol(logic.base_currency(uid)),
                        "currencies": logic.supported_currencies()})

    @app.post("/api/settings/base_currency")
    def set_base_currency():
        """Change the reporting currency; all analytics re-convert instantly."""
        uid = _uid()
        if not uid:
            return jsonify({"error": "not authorized"}), 401
        d = request.get_json(silent=True) or {}
        try:
            code = logic.set_base_currency(uid, d.get("base_currency"))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"ok": True, "base_currency": code,
                        "base_symbol": logic.symbol(code)})

    # ================== TRANSACTIONS ====================================== #
    @app.get("/api/transactions")
    def transactions():
        uid = _uid()
        if not uid:
            return jsonify({"error": "not authorized"}), 401
        month = request.args.get("month")
        return jsonify(logic.transactions_view(uid, month=month))

    @app.post("/api/transactions")
    def add_transaction():
        uid = _uid()
        if not uid:
            return jsonify({"error": "not authorized"}), 401
        d = request.get_json(silent=True) or {}
        try:
            tid = logic.add_transaction(
                uid, d.get("date", datetime.now().strftime("%Y-%m-%d")),
                d.get("description"), d.get("amount"), d.get("type"),
                d.get("category"), d.get("currency"),
            )
            return jsonify({"id": tid}), 201
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

    @app.delete("/api/transactions/<int:tid>")
    def delete_transaction(tid):
        try:
            logic.delete_transaction(tid)
            return jsonify({"ok": True})
        except ValidationError as e:
            return jsonify({"error": str(e)}), 404

    # ================== BUDGETS & ANALYTICS ============================== #
    @app.get("/api/summary")
    def summary():
        uid = _uid()
        if not uid:
            return jsonify({"error": "not authorized"}), 401
        month = request.args.get("month") or datetime.now().strftime("%Y-%m")
        return jsonify(logic.to_summary_json(uid, month))

    @app.post("/api/budgets")
    def set_budget():
        uid = _uid()
        if not uid:
            return jsonify({"error": "not authorized"}), 401
        d = request.get_json(silent=True) or {}
        try:
            logic.set_budget(uid, d.get("category"), d.get("month"),
                             d.get("amount"), d.get("currency"))
            return jsonify({"ok": True}), 201
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

    # ================== CSV ============================================== #
    @app.get("/api/export")
    def export_csv():
        uid = _uid()
        if not uid:
            return jsonify({"error": "not authorized"}), 401
        csv_text = logic.export_csv(uid, request.args.get("month"))
        return app.response_class(csv_text, mimetype="text/csv",
                                  headers={"Content-Disposition":
                                           "attachment; filename=expenses.csv"})

    @app.post("/api/import")
    def import_csv():
        uid = _uid()
        if not uid:
            return jsonify({"error": "not authorized"}), 401
        d = request.get_json(silent=True) or {}
        try:
            n = logic.import_csv(uid, d.get("csv", ""))
            return jsonify({"imported": n})
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

    return app


def main():
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


if __name__ == "__main__":
    main()
