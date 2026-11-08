"""
Routes: /api/budgets (GET, POST), /api/budgets/by-category (DELETE), /api/summary

Feature 2 - Monthly Budget Summary:
    GET /api/summary?month=YYYY-MM -> BudgetController.summary
                                   -> BudgetService.monthly_summary
                                   -> BudgetRepository.list_for_month -> PostgreSQL
"""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..utils.errors import NotFoundError
from ..utils.validators import validate_month
from ._request import current_user_id, json_body, require_fields


def _requested_month():
    """?month=YYYY-MM, defaulting to the current month."""
    return validate_month(request.args.get("month") or datetime.now().strftime("%Y-%m"))


def create_budget_blueprint(budget_service):
    bp = Blueprint("budgets", __name__, url_prefix="/api")

    @bp.get("/summary")
    @jwt_required()
    def summary():
        return jsonify(budget_service.monthly_summary(current_user_id(), _requested_month()))

    @bp.get("/budgets")
    @jwt_required()
    def budget_status():
        return jsonify(budget_service.budget_status(current_user_id(), _requested_month()))

    @bp.post("/budgets")
    @jwt_required()
    def set_budget():
        data = json_body()
        require_fields(data, "category", "month", "amount")
        budget_service.set_budget(current_user_id(), data["category"], data["month"],
                                  data["amount"], data.get("currency"))
        return jsonify({"ok": True}), 201

    @bp.delete("/budgets/by-category")
    @jwt_required()
    def delete_budget_by_category():
        data = json_body()
        if not data.get("category") or not data.get("month"):
            return jsonify({"error": "Missing parameters"}), 400
        if not budget_service.delete_budget(current_user_id(), data["month"], data["category"]):
            raise NotFoundError("Budget record not found.")
        return jsonify({"status": "success", "message": "Budget deleted successfully."}), 200

    return bp
