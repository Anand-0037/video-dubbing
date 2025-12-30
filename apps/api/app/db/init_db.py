"""Database initialization script."""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.database import init_db


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization complete!")
