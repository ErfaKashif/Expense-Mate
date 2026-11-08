"""
Central logging setup.

Every module obtains its logger with `get_logger(__name__)` so log lines
show where they came from, e.g.
    2026-11-07 12:00:00 INFO  app.backend.database.schema: Applied schema migration ...
"""

import logging
import os

_configured = False


def configure_logging(level=None):
    """Configure the root ExpenseMate logger once (level from LOG_LEVEL env)."""
    global _configured
    if _configured:
        return
    level_name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )
    _configured = True


def get_logger(name):
    return logging.getLogger(name)
