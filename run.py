import os
import sys

# Get absolute path to Expense-Mate root
project_root = os.path.dirname(os.path.abspath(__file__))

# Ensure current project folder takes absolute priority in Python's search path
if project_root in sys.path:
    sys.path.remove(project_root)
sys.path.insert(0, project_root)

# Import create_app cleanly
from app.backend.server import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)