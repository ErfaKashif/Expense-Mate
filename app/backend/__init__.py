"""
ExpenseMate backend.

Layered architecture (Assignment 02):

    controllers/   HTTP routes (Flask blueprints)
    services/      business rules and calculations
    repositories/  all SQL
    database/      PostgreSQL configuration, connections, transactions, schema
    models/        data classes passed between layers
    utils/         validators, errors, logging
"""

from .server import create_app

__all__ = ["create_app"]
