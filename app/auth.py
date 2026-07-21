"""
Auth
------
Non-blocking versions of the login/registration logic from the game
backend's login() function. Same rules, same collection, same document
shape (including the exact stats keys the games expect) - this just
returns values / raises AuthError instead of using input() and exit(),
so the GUI can call it directly instead of blocking on a console prompt.
"""

from datetime import datetime
from db import users


class AuthError(Exception):
    """reason is one of: 'no_such_user', 'wrong_password', 'user_exists'."""
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def login(user_id, password):
    """Matches an existing account. Returns the user document on success."""
    user_id = user_id.strip().upper()
    user = users.find_one({"user_id": user_id})
    if not user:
        raise AuthError("no_such_user")
    if user["password"] != password:
        raise AuthError("wrong_password")
    return user


def register(user_id, name, password):
    """Creates a new account. Mirrors the backend's auto-register shape
    exactly (same fields, same stats keys) so game sessions still write
    against the schema the games already expect."""
    user_id = user_id.strip().upper()
    if users.find_one({"user_id": user_id}):
        raise AuthError("user_exists")

    new_user = {
        "user_id": user_id,
        "name": name,
        "password": password,
        "created_at": datetime.now(),
        "stats": {
        "vines_sessions": 0,
         "cosmic_weaver_sessions": 0,
},
    }
    users.insert_one(new_user)
    return new_user