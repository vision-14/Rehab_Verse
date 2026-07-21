"""
Session Data
--------------
Real MongoDB-backed reads for everything the dashboard shows about the
logged-in user: current/best streak, this week's activity, total and
per-game session counts, and session history for the progress charts.

Every function here takes user_id and queries the real `sessions`
collection - nothing in this file is a placeholder anymore. If user_id is
missing/falsy, functions return the "empty" shape (0, all-False, etc.)
rather than raising, since that's the state before anyone's logged in.
"""

import random
from datetime import date, datetime, timedelta

from db import sessions
# FIX: was importing TOTAL_STAR_COUNT, which is now just a backward-compat
# alias for PAGE_1_TOTAL alone (see cosmic_weaver_scene.py) - clamping
# against it silently capped every player's progress at Page 1's capacity
# forever, since CosmicWeaverPager can actually hold PAGE_1_TOTAL +
# PAGE_2_TOTAL stars combined. Importing both page totals directly here
# (plain module-level constants, no QWidget needed) and summing them.
from cosmic_weaver_scene import PAGE_1_TOTAL, PAGE_2_TOTAL

DAY_LETTERS = ["M", "T", "W", "T", "F", "S", "S"]

MOTIVATION_QUOTES = [
    "Every small movement today creates a stronger tomorrow.",
    "Progress isn't always visible, but it's always happening.",
    "One gentle stretch at a time - you're doing great.",
]

GAME_INFO = {
    "bloom_forest": {
        "display_name": "Bloom Forest",
        "game_field_pattern": r"^\s*vines\s*$",
    },
    "cosmic_weaver": {
        "display_name": "Cosmic Weaver",
        "game_field_pattern": r"^\s*(cosmic[_ ]?weaver|neuro)\s*$",
    },
}


def get_game_display_name(game_id):
    return GAME_INFO.get(game_id, {}).get("display_name", game_id)


def _user_session_dates(user_id):
    try:
        docs = sessions.find({"user_id": user_id}, {"date": 1})
        return {d["date"].date() for d in docs if d.get("date")}
    except Exception as exc:
        print(f"[session_data] Couldn't fetch session dates: {exc}")
        return set()


def get_current_streak(user_id=None):
    if not user_id:
        return 0
    session_dates = _user_session_dates(user_id)
    if not session_dates:
        return 0

    cursor = date.today()
    if cursor not in session_dates:
        cursor -= timedelta(days=1)

    streak = 0
    while cursor in session_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def get_best_streak(user_id=None):
    if not user_id:
        return 0
    session_dates = sorted(_user_session_dates(user_id))
    if not session_dates:
        return 0

    best = current = 1
    for prev_day, this_day in zip(session_dates, session_dates[1:]):
        gap = (this_day - prev_day).days
        if gap == 1:
            current += 1
            best = max(best, current)
        elif gap > 1:
            current = 1
    return best


def get_today_index():
    return date.today().weekday()


def get_weekly_session_days(user_id=None):
    if not user_id:
        return [False] * 7

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    start = datetime.combine(monday, datetime.min.time())
    end = datetime.combine(monday + timedelta(days=6), datetime.max.time())

    try:
        docs = sessions.find(
            {"user_id": user_id, "date": {"$gte": start, "$lte": end}},
            {"date": 1},
        )
    except Exception as exc:
        print(f"[session_data] Couldn't fetch weekly activity: {exc}")
        return [False] * 7

    result = [False] * 7
    for doc in docs:
        doc_date = doc.get("date")
        if doc_date:
            result[doc_date.weekday()] = True
    return result


def get_total_sessions(user_id=None):
    if not user_id:
        return 0
    try:
        return sessions.count_documents({"user_id": user_id})
    except Exception as exc:
        print(f"[session_data] Couldn't count total sessions: {exc}")
        return 0


def get_game_session_counts(user_id=None):
    counts = {}
    for game_id, info in GAME_INFO.items():
        if not user_id:
            counts[game_id] = 0
            continue
        try:
            counts[game_id] = sessions.count_documents({
                "user_id": user_id,
                "game": {"$regex": info["game_field_pattern"], "$options": "i"},
            })
        except Exception as exc:
            print(f"[session_data] Couldn't count sessions for {game_id}: {exc}")
            counts[game_id] = 0
    return counts


def get_session_history(user_id, game_id=None, limit=7):
    if not user_id:
        return []

    query = {"user_id": user_id}
    if game_id:
        info = GAME_INFO.get(game_id)
        if not info:
            return []
        query["game"] = {"$regex": info["game_field_pattern"], "$options": "i"}

    try:
        docs = list(
            sessions.find(query).sort("date", -1).limit(limit)
        )
    except Exception as exc:
        print(f"[session_data] Couldn't fetch session history: {exc}")
        return []

    docs.reverse()

    history = []
    for doc in docs:
        metrics = doc.get("metrics", {})
        history.append({
            "date": doc.get("date"),
            "completion_rate": metrics.get("completion_rate"),
            "accuracy": metrics.get("accuracy"),
            "rom": metrics.get("rom"),
            "flexion_rom": metrics.get("flexion_rom"),
            "extension_rom": metrics.get("extension_rom"),
            "best_hold": metrics.get("best_hold"),
            "avg_stability": metrics.get("avg_stability"),
            "score": metrics.get("score"),
            "best_streak": metrics.get("best_streak"),
            "stars_deposited": metrics.get("stars_deposited"),
            "stars_dropped": metrics.get("stars_dropped"),
            "wrong_hand_attempts": metrics.get("wrong_hand_attempts"),
            "nebula_collected": metrics.get("nebula_collected"),
        })
    return history


def get_random_quote(exclude=None):
    choices = [q for q in MOTIVATION_QUOTES if q != exclude] or MOTIVATION_QUOTES
    return random.choice(choices)


def get_latest_session(user_id, game_id):
    info = GAME_INFO.get(game_id)
    if not info or not user_id:
        return None
    query = {
        "user_id": user_id,
        "game": {"$regex": info["game_field_pattern"], "$options": "i"},
    }
    try:
        return sessions.find_one(query, sort=[("date", -1)])
    except Exception as exc:
        print(f"[session_data] Couldn't fetch latest session: {exc}")
        return None


def get_latest_session_summary(user_id, game_id):
    doc = get_latest_session(user_id, game_id)
    if not doc:
        return None

    metrics = doc.get("metrics", {})
    summary = {
        "game_name": get_game_display_name(game_id),
        "date": doc.get("date"),
        "accuracy": metrics.get("accuracy"),
        "completion_rate": metrics.get("completion_rate"),
        "session_duration": doc.get("session_duration"),
    }

    if game_id == "cosmic_weaver":
        summary.update({
            "score": metrics.get("score"),
            "best_streak": metrics.get("best_streak"),
            "stars_deposited": metrics.get("stars_deposited"),
            "stars_dropped": metrics.get("stars_dropped"),
            "wrong_hand_attempts": metrics.get("wrong_hand_attempts"),
            "nebula_collected": metrics.get("nebula_collected"),
        })
    else:
        summary.update({
            "rom": metrics.get("rom"),
            "flexion_rom": metrics.get("flexion_rom"),
            "extension_rom": metrics.get("extension_rom"),
            "best_hold": metrics.get("best_hold"),
            "avg_reach_time": metrics.get("avg_reach_time"),
            "flowers": metrics.get("flowers"),
            "buds": metrics.get("buds"),
            "leaves": metrics.get("leaves"),
        })

    return summary


# ----------------------------------------------------------------------
# Cosmic Weaver constellation-scene progress (cumulative "lit stars")
# ----------------------------------------------------------------------

def get_cosmic_weaver_total_score(user_id):
    """Sums metrics.score across EVERY cosmic_weaver session this user has
    ever saved. Computed fresh from Mongo each call rather than stored as
    a separate running counter - the sessions collection is already the
    source of truth, so there's nothing extra to keep in sync."""
    if not user_id:
        return 0
    info = GAME_INFO["cosmic_weaver"]
    try:
        docs = sessions.find(
            {
                "user_id": user_id,
                "game": {"$regex": info["game_field_pattern"], "$options": "i"},
            },
            {"metrics.score": 1},
        )
        return sum((d.get("metrics", {}).get("score") or 0) for d in docs)
    except Exception as exc:
        print(f"[session_data] Couldn't sum cosmic_weaver scores: {exc}")
        return 0


STARS_PER_SCORE_POINT = 4  # every 4 score points = 1 lit star (score // 4)

# FIX: combined capacity across BOTH pages now, not just Page 1. This is
# what CosmicWeaverPager.total_star_count() computes internally too -
# kept as a plain constant here (rather than instantiating a QWidget just
# to read a number) since PAGE_1_TOTAL/PAGE_2_TOTAL are already plain
# module-level constants in cosmic_weaver_scene.py.
TOTAL_STARS_ACROSS_PAGES = PAGE_1_TOTAL + PAGE_2_TOTAL


def get_cosmic_weaver_star_count(user_id):
    """Cumulative lit-star count: floor(total_score / 4), CLAMPED to the
    combined capacity across both constellation pages. score is unbounded
    (it keeps growing session after session with no ceiling), so without
    this clamp the raw division can exceed the number of stars that
    actually exist across both pages - which used to make the reveal skip
    straight to "full sky" instead of animating, since a previous_stars
    value already past capacity meant there was nothing left to animate
    toward."""
    total_score = get_cosmic_weaver_total_score(user_id)
    return min(total_score // STARS_PER_SCORE_POINT, TOTAL_STARS_ACROSS_PAGES)


def get_cosmic_weaver_star_progress(user_id):
    """Returns (previous_stars, gained_stars, new_stars) for the
    star-reveal animation shown right after a Cosmic Weaver session ends -
    all in STAR counts (score already divided by 4 AND clamped to the
    combined capacity across both pages), not raw score. Call this AFTER
    the session has been saved to Mongo (the controller script always
    saves before exiting, so this is safe to call the moment the game
    process finishes).

    previous_stars and new_stars are both clamped to
    TOTAL_STARS_ACROSS_PAGES here - previously only the reveal page's own
    target_count was clamped, but previous_stars itself (unclamped) could
    already exceed capacity once cumulative score grew large enough,
    which skipped the fill animation entirely and just showed a full sky
    instantly. Once the sky is genuinely full, gained_stars correctly
    comes out to 0 (both values pinned at the same cap) instead of
    misleadingly implying more room to grow."""
    if not user_id:
        return 0, 0, 0

    new_total_score = get_cosmic_weaver_total_score(user_id)
    latest = get_latest_session(user_id, "cosmic_weaver")
    session_gain_score = 0
    if latest:
        session_gain_score = latest.get("metrics", {}).get("score") or 0
    previous_total_score = max(0, new_total_score - session_gain_score)

    previous_stars = min(previous_total_score // STARS_PER_SCORE_POINT, TOTAL_STARS_ACROSS_PAGES)
    new_stars = min(new_total_score // STARS_PER_SCORE_POINT, TOTAL_STARS_ACROSS_PAGES)
    gained_stars = new_stars - previous_stars  # 0 once the sky is already full
    return previous_stars, gained_stars, new_stars