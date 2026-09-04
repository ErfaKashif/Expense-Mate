"""
ExpenseMate — entry point.

Run:   python run.py
Then open: http://localhost:5000
"""
from app.backend.server import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
