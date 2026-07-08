"""
db.py
Shared MongoDB access layer for RehabVerse.

Import this from:
  - your PyQt6 login/register screens
  - your PyQt6 dashboard (to show stats, last session, etc.)
  - the game scripts (vines.py, neuro.py) to fetch difficulty / save results

Nothing here uses input() or print() for control flow — every function
returns data/status so the caller (PyQt6 screen or game script) decides
what to show the user.
"""

import string
import random
from datetime import datetime
from pymongo import MongoClient

# ---------------- CONNECTION ---------------- #
_URI = "mongodb+srv://ipsita_db_user:IPdb12345@rehabverse.tlpbjja.mongodb.net/?appName=RehabVerse"

_client = MongoClient(_URI)
db = _client["RehabVerse"]
users = db["users"]
sessions = db["sessions"]


GAME_VINES = "vines"
GAME_NEURO = "neuro"


# ---------------- ID GENERATION ---------------- #
def generate_user_id(name: str) -> str:
    random_part = ''.join(random.choices(string.digits, k=4))
    return name[:3].upper() + random_part


# ---------------- AUTH ---------------- #
def login(user_id: str, password: str):
    """
    Returns a tuple: (status, user_doc_or_None)
    status is one of: "ok", "wrong_password", "not_found"
    """
    user_id = user_id.upper()
    user = users.find_one({"user_id": user_id})

    if not user:
        return "not_found", None

    if user["password"] == password:
        return "ok", user

    return "wrong_password", None


def register(user_id: str, name: str, password: str):
    """
    Creates a new user. Returns the user_id used (uppercased).
    Caller (PyQt6 register screen) is responsible for checking
    login() first to make sure the id doesn't already exist.
    """
    user_id = user_id.upper()

    new_user = {
        "user_id": user_id,
        "name": name,
        "password": password,
        "created_at": datetime.now(),
        "stats": {
            "vines_sessions": 0,
            "neuro_sessions": 0
        }
    }

    users.insert_one(new_user)
    return user_id


def get_user(user_id: str):
    return users.find_one({"user_id": user_id.upper()})


# ---------------- EMAIL-BASED AUTH ---------------- #
# The actual PyQt6 login screen collects a Gmail address + password, not a
# short user_id, so these mirror login()/register() but key off "email".
# Every account still gets a short "user_id" generated on sign-up (e.g.
# "PRI4821") - that's what gets passed into the game scripts as the CLI
# arg and what session documents are linked to, so vines.py/neuro.py don't
# need to know anything about email at all.

def login_with_email(email: str, password: str):
    """
    Returns a tuple: (status, user_doc_or_None)
    status is one of: "ok", "wrong_password", "not_found"
    """
    email = email.strip().lower()
    user = users.find_one({"email": email})

    if not user:
        return "not_found", None

    if user["password"] == password:
        return "ok", user

    return "wrong_password", None


def register_with_email(email: str, password: str, name: str = None):
    """
    Creates a new user keyed by email. Returns the new user doc, or None
    if that email is already registered (caller should show an error).
    """
    email = email.strip().lower()

    if users.find_one({"email": email}):
        return None

    display_name = name or email.split("@")[0].replace(".", " ").title()
    short_id = generate_user_id(display_name)

    new_user = {
        "email": email,
        "user_id": short_id,
        "name": display_name,
        "password": password,
        "created_at": datetime.now(),
        "stats": {
            "vines_sessions": 0,
            "neuro_sessions": 0
        }
    }

    users.insert_one(new_user)
    return new_user


# ---------------- SESSIONS ---------------- #
def get_last_session(user_id: str, game: str):
    """game should be one of GAME_VINES / GAME_NEURO"""
    return sessions.find_one(
        {"user_id": user_id, "game": game},
        sort=[("date", -1)]
    )


def save_session(user_id: str, game: str, metrics: dict,
                  session_duration: float, difficulty: dict):
    """
    Saves one completed session and bumps the user's session counter.
    Returns the inserted session's Mongo _id.
    """
    session_data = {
        "user_id": user_id,
        "game": game,
        "date": datetime.now(),
        "metrics": metrics,
        "session_duration": session_duration,
        "difficulty": difficulty
    }

    result = sessions.insert_one(session_data)

    stat_field = "vines_sessions" if game == GAME_VINES else "neuro_sessions"
    users.update_one({"user_id": user_id}, {"$inc": {f"stats.{stat_field}": 1}})

    return result.inserted_id


def get_all_sessions(user_id: str, game: str = None):
    query = {"user_id": user_id}
    if game:
        query["game"] = game
    return list(sessions.find(query).sort("date", -1))