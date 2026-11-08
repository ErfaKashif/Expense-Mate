"""
ExpenseMate application factory (composition root).

This is the only place where the layers are wired together:

    Controllers  ->  Services  ->  Repositories  ->  Database (PostgreSQL)

Each object receives the objects it depends on through its constructor
(dependency injection), so every layer can be tested on its own by passing
in mocks instead of the real dependencies.
"""

import os
import secrets

from flask import Flask, send_from_directory
from flask_jwt_extended import JWTManager

from .controllers.auth_controller import create_auth_blueprint
from .controllers.budget_controller import create_budget_blueprint
from .controllers.currency_controller import create_currency_blueprint
from .controllers.error_handlers import register_error_handlers
from .controllers.expense_controller import create_expense_blueprint
from .database import Database, apply_migrations, get_database_url, load_env_file
from .repositories import BudgetRepository, CategoryRepository, ExpenseRepository, UserRepository
from .services.analytics_service import AnalyticsService
from .services.budget_calculator import BudgetCalculator
from .services.budget_service import BudgetService
from .services.csv_importer import CsvImporter
from .services.currency_service import CurrencyService
from .services.expense_service import ExpenseService
from .services.user_service import UserService
from .utils.logger import configure_logging, get_logger
from .utils.validators import ExpenseValidator

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

log = get_logger(__name__)


def build_services(database):
    """Create repositories and services for `database`. Returns a dict of services."""
    users_repo = UserRepository(database)
    categories_repo = CategoryRepository(database)
    expenses_repo = ExpenseRepository(database)
    budgets_repo = BudgetRepository(database)

    currency = CurrencyService()
    users = UserService(users_repo, currency)
    analytics = AnalyticsService(expenses_repo, users, currency)
    budgets = BudgetService(database, budgets_repo, categories_repo, analytics, users,
                            currency, BudgetCalculator())
    expenses = ExpenseService(database, expenses_repo, categories_repo, users, currency,
                              budgets, ExpenseValidator(currency.normalise), CsvImporter())
    return {"currency": currency, "users": users, "analytics": analytics,
            "budgets": budgets, "expenses": expenses}


def _jwt_secret(testing):
    secret = os.environ.get("JWT_SECRET_KEY")
    if secret:
        return secret
    if not testing:
        log.warning("JWT_SECRET_KEY is not set; using a random key (logins reset on restart).")
    return secrets.token_hex(32)


def create_app(database_url=None, testing=False, run_migrations=True):
    """Build the Flask app connected to PostgreSQL.

    database_url   PostgreSQL URL; defaults to the DATABASE_URL env variable.
    testing        Flask testing mode.
    run_migrations Apply pending schema migrations at start-up (idempotent).
    """
    load_env_file()
    configure_logging()

    database = Database(database_url or get_database_url())
    if run_migrations:
        apply_migrations(database)
    services = build_services(database)

    app = Flask(__name__, static_folder=os.path.join(FRONTEND_DIR, "static"),
                template_folder=FRONTEND_DIR, static_url_path="/static")
    app.config["TESTING"] = testing
    app.config["JWT_SECRET_KEY"] = _jwt_secret(testing)
    JWTManager(app)
    app.extensions["expensemate"] = {"database": database, **services}

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    app.register_blueprint(create_auth_blueprint(services["users"], services["currency"]))
    app.register_blueprint(create_currency_blueprint(services["users"], services["currency"]))
    app.register_blueprint(create_expense_blueprint(services["expenses"]))
    app.register_blueprint(create_budget_blueprint(services["budgets"]))
    register_error_handlers(app)
    return app


def main():
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")


if __name__ == "__main__":
    main()
