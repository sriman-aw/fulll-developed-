import uvicorn
import os
import sys

# Ensure current directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import init_db

if __name__ == "__main__":
    print("=" * 60)
    print(" Starting Confluence Collaboration Portal...")
    print(" Initializing SQLite database...")
    init_db()
    print(" Database initialized and verified.")
    print(" Serving application at: http://127.0.0.1:8000")
    print(" API Documentation at:   http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
