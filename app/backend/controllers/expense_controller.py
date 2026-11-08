"""
Routes: /api/transactions (GET, POST), /api/transactions/<id> (DELETE),
        /api/categories, /api/export, /api/import

Feature 1 - Add Expense:
    POST /api/transactions -> ExpenseController.add_transaction
                           -> ExpenseService.add_expense
                           -> ExpenseRepository.add -> PostgreSQL
"""

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required

from ..utils.errors import ValidationError
from ._request import current_user_id, json_body, require_fields


def create_expense_blueprint(expense_service):
    bp = Blueprint("expenses", __name__, url_prefix="/api")

    @bp.get("/categories")
    def categories():
        return jsonify(expense_service.list_categories())

    @bp.get("/transactions")
    @jwt_required()
    def list_transactions():
        return jsonify(expense_service.list_expenses(
            current_user_id(), month=request.args.get("month") or None,
            type=request.args.get("type") or None))

    @bp.post("/transactions")
    @jwt_required()
    def add_transaction():
        data = json_body()
        require_fields(data, "date", "amount", "type")
        tx_id, alert = expense_service.add_expense(
            current_user_id(),
            date=data.get("date"),
            description=data.get("description"),
            amount=data.get("amount"),
            type=data.get("type"),
            category=data.get("category"),
            currency=data.get("currency"),
        )
        return jsonify({"status": "success", "id": tx_id, "alert": alert}), 201

    @bp.delete("/transactions/<int:transaction_id>")
    @jwt_required()
    def delete_transaction(transaction_id):
        expense_service.delete_expense(current_user_id(), transaction_id)
        return jsonify({"ok": True})

    @bp.get("/export")
    @jwt_required()
    def export_csv():
        csv_text = expense_service.export_csv(current_user_id(), request.args.get("month") or None)
        return Response(csv_text, mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=expenses.csv"})

    @bp.post("/import")
    @jwt_required()
    def import_csv():
        csv_text = json_body().get("csv", "")
        if not isinstance(csv_text, str):
            raise ValidationError("'csv' must be the CSV file contents as text.")
        imported, skipped = expense_service.import_csv(current_user_id(), csv_text)
        return jsonify({"imported": imported, "skipped": skipped})

    return bp
