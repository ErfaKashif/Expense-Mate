import os

from app.backend.server import create_app

if os.environ.get("EXPENSEMATE_DB"):
    DB_PATH = os.environ["EXPENSEMATE_DB"]
else:
    DB_PATH = None          # -> app/data/expensemate.db (local development)

app = create_app(db_path=DB_PATH)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
