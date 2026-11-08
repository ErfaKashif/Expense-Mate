"""
CONTROLLER layer: Flask blueprints.

Controllers read the HTTP request, do basic input checks, call ONE service
method and turn the result into JSON. They contain no SQL and no business
calculations. Errors raised by services are converted to HTTP responses
centrally in `error_handlers.py`.
"""
