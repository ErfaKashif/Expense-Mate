"""
Unit tests - controllers with MOCKED services (no database).

Shows that controllers only translate HTTP <-> service calls: they extract
input, perform basic checks and map errors to status codes.
"""
from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from app.backend.controllers.budget_controller import create_budget_blueprint
from app.backend.controllers.error_handlers import register_error_handlers
from app.backend.controllers.expense_controller import create_expense_blueprint
from app.backend.database import DatabaseUnavailableError
from app.backend.utils.errors import NotFoundError, ValidationError


@pytest.fixture
def services():
    return MagicMock(), MagicMock()


@pytest.fixture
def client(services):
    expense_service, budget_service = services
    app = Flask(__name__)
    app.config.update(JWT_SECRET_KEY="k" * 32, TESTING=True)
    JWTManager(app)
    app.register_blueprint(create_expense_blueprint(expense_service))
    app.register_blueprint(create_budget_blueprint(budget_service))
    register_error_handlers(app)
    with app.app_context():
        token = create_access_token(identity="7")
    c = app.test_client()
    c.headers = {"Authorization": f"Bearer {token}"}
    return c


def test_add_expense_passes_input_to_service(client, services):
    expense_service, _ = services
    expense_service.add_expense.return_value = (11, None)
    body = {"date": "2026-09-01", "description": "lunch", "amount": 60, "type": "expense",
            "category": "Food", "currency": "USD"}
    r = client.post("/api/transactions", json=body, headers=client.headers)
    assert r.status_code == 201 and r.get_json() == {"status": "success", "id": 11, "alert": None}
    expense_service.add_expense.assert_called_once_with(
        7, date="2026-09-01", description="lunch", amount=60, type="expense",
        category="Food", currency="USD")


def test_missing_fields_rejected_before_service(client, services):
    expense_service, _ = services
    r = client.post("/api/transactions", json={"description": "x"}, headers=client.headers)
    assert r.status_code == 400 and "date" in r.get_json()["error"]
    expense_service.add_expense.assert_not_called()


def test_non_object_json_rejected(client):
    r = client.post("/api/transactions", json=[1, 2], headers=client.headers)
    assert r.status_code == 400


@pytest.mark.parametrize("error, status", [
    (ValidationError("bad"), 400), (NotFoundError("nope"), 404),
    (DatabaseUnavailableError("down"), 503),
])
def test_service_errors_become_status_codes(client, services, error, status):
    expense_service, _ = services
    expense_service.add_expense.side_effect = error
    r = client.post("/api/transactions", headers=client.headers,
                    json={"date": "2026-09-01", "amount": 1, "type": "expense"})
    assert r.status_code == status and "error" in r.get_json()


def test_requires_jwt(client):
    assert client.get("/api/transactions").status_code == 401


def test_summary_defaults_and_validates_month(client, services):
    _, budget_service = services
    budget_service.monthly_summary.return_value = {"ok": True}
    assert client.get("/api/summary?month=2026-09", headers=client.headers).get_json() == {"ok": True}
    budget_service.monthly_summary.assert_called_once_with(7, "2026-09")
    assert client.get("/api/summary?month=bad", headers=client.headers).status_code == 400


def test_set_budget_requires_category(client, services):
    _, budget_service = services
    r = client.post("/api/budgets", json={"month": "2026-09", "amount": 5}, headers=client.headers)
    assert r.status_code == 400
    budget_service.set_budget.assert_not_called()


def test_delete_budget_not_found(client, services):
    _, budget_service = services
    budget_service.delete_budget.return_value = False
    r = client.delete("/api/budgets/by-category", json={"category": "Food", "month": "2026-09"},
                      headers=client.headers)
    assert r.status_code == 404
