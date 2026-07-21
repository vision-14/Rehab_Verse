"""
MongoDB Connection
---------------------
Single shared Mongo connection for the desktop app's login/registration.
Uses the exact same connection string and collections as the game backend
scripts (e.g. the Bloom Forest controller), so the app and the games all
read/write the same `users` and `sessions` data.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# NEW: connection string now comes from .env instead of being hardcoded -
# searches upward from this file's location for a .env file, so it works
# whether this file sits at app/db.py or games/common/db.py.


def _find_and_load_env(max_levels_up=6):
    current = Path(__file__).resolve().parent
    for _ in range(max_levels_up):
        candidate = current / ".env"
        if candidate.exists():
            load_dotenv(dotenv_path=candidate)
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


_env_path = _find_and_load_env()
uri = os.getenv("MONGO_URI")

if not uri:
    raise RuntimeError(
        "MONGO_URI not found. Checked for a .env file starting from "
        f"{Path(__file__).resolve().parent} and searching upward "
        f"({'found ' + str(_env_path) if _env_path else 'no .env file found'}). "
        "Make sure a .env file with MONGO_URI=... exists at the project root."
    )

client = MongoClient(uri)
db = client["RehabVerse"]
users = db["users"]
sessions = db["sessions"]