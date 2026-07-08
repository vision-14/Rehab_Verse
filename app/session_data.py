"""
Session Data (stub)
----------------------
Placeholder read layer for everything the dashboard needs from MongoDB:
current streak, which days this week had a logged session, and the
motivation quote pool. Every function here is a stand-in - swap the body
for a real query once the backend is back up. The shapes returned are the
contract the UI already expects, so nothing above this layer should need
to change when you wire in real data.
"""

import random
from datetime import date

DAY_LETTERS = ["M", "T", "W", "T", "F", "S", "S"]

MOTIVATION_QUOTES = [
    "Every small movement today creates a stronger tomorrow.",
    "Progress isn't always visible, but it's always happening.",
    "One gentle stretch at a time - you're doing great.",
]


def get_current_streak(user_id=None):
    """TODO: replace with a real Mongo query, e.g. count consecutive days
    up to today that have at least one completed session document for
    this user."""
    return 5


def get_today_index():
    """0 = Monday ... 6 = Sunday, matching DAY_LETTERS order."""
    return date.today().weekday()


def get_weekly_session_days(user_id=None):
    """Returns 7 booleans (Mon..Sun of the CURRENT week) - True where a
    session was logged that day.

    TODO: replace with something like:
        start_of_week = <most recent Monday>
        docs = db.sessions.find({
            "user_id": user_id,
            "date": {"$gte": start_of_week, "$lte": start_of_week + 6 days}
        })
        result = [False] * 7
        for doc in docs:
            result[doc["date"].weekday()] = True
        return result
    """
    # Placeholder pattern so the UI has something real to render before
    # Mongo is wired up. Days after today are always False.
    placeholder = [True, True, False, True, False, False, False]
    today_idx = get_today_index()
    return [v if i <= today_idx else False for i, v in enumerate(placeholder)]


def get_random_quote(exclude=None):
    """Picks one motivation line at random, avoiding immediate repeats."""
    choices = [q for q in MOTIVATION_QUOTES if q != exclude] or MOTIVATION_QUOTES
    return random.choice(choices)