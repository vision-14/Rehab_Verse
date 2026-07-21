import cv2
import mediapipe as mp
import math
import time
import sys
import threading
import socket

# FIX (same issue as Vines hit): Windows consoles default to a legacy
# codepage that can't encode characters like the checkmark used below in
# "Session saved" - crashing with UnicodeEncodeError right after the
# session was already saved to Mongo, so it looks worse than it is.
# Reconfiguring stdout/stderr to UTF-8 up front fixes this for every
# print in the script.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from datetime import datetime

# db.py and game_login.py live in games/common/, same as Vines.
sys.path.append(str(Path(__file__).resolve().parent.parent / "common"))

from db import users, sessions
from game_login import login

# ---------------- Display ---------------- #

SHOW_CAMERA_WINDOW = False  # set True to bring back the debug preview window

# NEW: global keyboard hook for ESC-to-quit, same pattern Vines uses.
# With no cv2 window shown, cv2.waitKey() has nothing to read keys from -
# it only receives input when its own window has focus. This listens
# system-wide instead, so ESC still works with no window on screen at all.
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    print("[cosmic_weaver] 'keyboard' package not installed - with "
          "SHOW_CAMERA_WINDOW=False there is no way to manually quit "
          "this script (ESC has nothing to focus). Run: pip install "
          "keyboard - or rely on Unity's SESSION_END / the duration "
          "fallback to end the session.")

_quit_requested = False


def _on_global_key(event):
    global _quit_requested
    if event.event_type == "down" and event.name == "esc":
        _quit_requested = True


if HAS_KEYBOARD:
    keyboard.hook(_on_global_key)

# ---------------- UDP setup ---------------- #

UDP_IP = "127.0.0.1"
UDP_PORT = 5052
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Unity -> Python events, all on one port: periodic checkpoints during
# play and one final report on session end. Fire-and-forget in both
# directions - Python never blocks waiting for a Unity reply, and Unity
# never blocks waiting for a Python reply. This is the ONLY channel
# carrying data back from Unity; everything else is one-way Python->Unity.
GAME_EVENTS_PORT = 5054

# latest report received from Unity - GameManager owns score/streak/drop/
# etc. locally now (colliders, thresholds, all of it), Python just needs
# the numbers at the end to save to Mongo.
_report_lock = threading.Lock()
latest_report = {
    "score": 0, "streak": 0, "best_streak": 0,
    "stars_deposited": 0, "stars_dropped": 0,
    "wrong_hand_attempts": 0, "nebula_collected": 0,
}
session_end_requested = False


def _game_events_listener():
    global session_end_requested
    esock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    esock.bind(("127.0.0.1", GAME_EVENTS_PORT))
    while True:
        try:
            data, _ = esock.recvfrom(1024)
            text = data.decode().strip()

            if text.startswith("REPORT:") or text.startswith("SESSION_END:"):
                is_final = text.startswith("SESSION_END:")
                payload = text.split(":", 1)[1]
                parts = payload.split(",")
                if len(parts) == 7:
                    with _report_lock:
                        latest_report["score"] = int(parts[0])
                        latest_report["streak"] = int(parts[1])
                        latest_report["best_streak"] = int(parts[2])
                        latest_report["stars_deposited"] = int(parts[3])
                        latest_report["stars_dropped"] = int(parts[4])
                        latest_report["wrong_hand_attempts"] = int(parts[5])
                        latest_report["nebula_collected"] = int(parts[6])
                if is_final:
                    session_end_requested = True
        except Exception as e:
            print(f"[game_events_listener] error: {e}")


threading.Thread(target=_game_events_listener, daemon=True).start()

# ---------------- Login ---------------- #
# sys.argv[1] = user_id, sys.argv[2] (optional) = hand preference chosen
# in the RehabVerse launcher UI before Unity opens: "left", "right", or
# "both" (default). Falls back to interactive login if run standalone.
#
# NOTE (launch difference vs Vines): Vines' launcher only ever passes
# argv[1] (user_id). This game ALSO expects argv[2] (hand preference) -
# confirm the RehabVerse launcher is actually passing that second arg
# for Cosmic Weaver specifically, otherwise hand_pref_arg silently falls
# back to "both" below even if the user picked left/right in the UI.
if len(sys.argv) > 1:
    user_id = sys.argv[1].strip().upper()
    print(f"Continuing as {user_id} (signed in via RehabVerse)")
    if not users.find_one({"user_id": user_id}):
        print("Unexpected: user not found in DB, falling back to manual login.")
        user_id = login()
else:
    user_id = login()

hand_pref_arg = sys.argv[2].strip().lower() if len(sys.argv) > 2 else "both"
# 0 = left only, 1 = right only, 2 = both/either - sent to Unity so its
# local required-hand picker respects this instead of choosing freely.
ALLOWED_HAND = {"left": 0, "right": 1}.get(hand_pref_arg, 2)
print(f"Hand preference: {hand_pref_arg} (code {ALLOWED_HAND})")

# ---------------- Constants ---------------- #

SMOOTH_ALPHA = 0.7          # position smoothing
GRIP_SMOOTH_ALPHA = 0.2     # grip strength smoothing
# Distance-ratio curl detection (orientation-invariant): compares each
# fingertip's distance from the wrist to its MCP knuckle's distance from
# the wrist, instead of comparing Y-coordinates. A Y-only comparison only
# works if fingers point roughly straight up/down in frame - tilt or
# rotate the hand and a genuinely open hand can still read as "folded"
# for some fingers, which was causing drop to fail even with the hand
# clearly opened. Distance ratios don't care which way the hand is
# rotated within the camera view.
RATIO_OPEN = 1.8    # tip-to-wrist / mcp-to-wrist ratio for a fully extended finger
RATIO_CLOSED = 1.0  # ...for a fully curled finger
FOLD_RATIO_THRESHOLD = 1.3  # below this ratio, a finger counts as "folded" this frame
FIST_HISTORY_LEN = 5
FIST_HISTORY_MIN = 3        # frames-out-of-5 needed to confirm a fist
FIST_FOLDED_THRESHOLD = 4   # fingers folded needed to count as "fisted" this frame

TRACKING_LOST_GRACE = 8     # frames a hand can vanish from mediapipe before we treat it as "released"

GRIP_DROP_THRESHOLD_DEFAULT = 50   # grip% below which Unity should consider the object dropped
STAR_TIME_LIMIT_DEFAULT = 12       # seconds Unity should allow to deposit a star before it counts as missed

# this is also sent to Unity (see the outgoing message below), not just
# used locally as Python's fallback. Unity seeds its own local countdown
# from this ONCE and manages the actual session-end timing itself from
# then on - Python doesn't keep "pushing" the clock, it just tells Unity
# the target once. Python's own SESSION_DURATION fallback below still
# exists too, but only as a safety net in case Unity crashes or never
# sends SESSION_END - not as a second authoritative timer.
SESSION_DURATION = 120      # fallback safety net - Unity is expected to send SESSION_END itself when its own session ends

# ---- performance ---- #
CAM_WIDTH = 640
CAM_HEIGHT = 480
MODEL_COMPLEXITY = 0

# ---- chest (deposit target) ---- #
# Fixed screen position instead of tracked from Pose landmarks - a stable,
# reliable spot to reach toward beats a jittery body-tracked one, and it
# means Pose doesn't need to run at all anymore (see below).
# (x_fraction, y_fraction) of the webcam frame - tune to taste.
CHEST_POSITION_FRACTION = (0.5, 0.85)

# ---------------- Adaptive difficulty ---------------- #
# Same idea as Vines: load this user's last session for THIS game and
# nudge difficulty based on how they did. These values are sent to Unity
# as config for ITS local thresholds - Python doesn't enforce them itself
# anymore, Unity does (it's the one with the actual collider/game logic).

GRIP_DROP_THRESHOLD = GRIP_DROP_THRESHOLD_DEFAULT
STAR_TIME_LIMIT = STAR_TIME_LIMIT_DEFAULT

last_session = sessions.find_one(
    {"user_id": user_id, "game": "cosmic_weaver"},
    sort=[("date", -1)]
)

if last_session:
    print("==================================================")
    print("ADAPTIVE DIFFICULTY - based on last session")
    print("==================================================")

    prev_grip = last_session["difficulty"]["grip_threshold"]
    prev_time_limit = last_session["difficulty"]["star_time_limit"]
    GRIP_DROP_THRESHOLD = prev_grip
    STAR_TIME_LIMIT = prev_time_limit

    prev_accuracy = last_session["metrics"]["accuracy"]
    prev_completion = last_session["metrics"]["completion_rate"]
    print(f"Previous accuracy: {prev_accuracy}% | completion: {prev_completion}%")

    if prev_completion > 90 and prev_accuracy > 90:
        STAR_TIME_LIMIT -= 1
        print(f"[Star Time] doing well -> decreasing {prev_time_limit}s -> {STAR_TIME_LIMIT}s")
    elif prev_completion < 60 or prev_accuracy < 60:
        STAR_TIME_LIMIT += 1
        print(f"[Star Time] struggling -> increasing {prev_time_limit}s -> {STAR_TIME_LIMIT}s")
    else:
        print(f"[Star Time] unchanged at {STAR_TIME_LIMIT}s")
    STAR_TIME_LIMIT = min(max(STAR_TIME_LIMIT, 5), 20)

    if prev_accuracy > 90:
        GRIP_DROP_THRESHOLD += 3
        print(f"[Grip Threshold] doing well -> increasing {prev_grip}% -> {GRIP_DROP_THRESHOLD}%")
    elif prev_accuracy < 60:
        GRIP_DROP_THRESHOLD -= 3
        print(f"[Grip Threshold] struggling -> decreasing {prev_grip}% -> {GRIP_DROP_THRESHOLD}%")
    else:
        print(f"[Grip Threshold] unchanged at {GRIP_DROP_THRESHOLD}%")
    GRIP_DROP_THRESHOLD = min(max(GRIP_DROP_THRESHOLD, 30), 90)
    print("==================================================")
else:
    print("No previous session found - starting at default difficulty.")

print(f"Grip Threshold : {GRIP_DROP_THRESHOLD}%")
print(f"Star Time Limit : {STAR_TIME_LIMIT}s")
print(f"Session Duration : {SESSION_DURATION}s (sent to Unity)")

# ---------------- Fist Detection ---------------- #

class FistTracker:
    """
    Tracks fist state with debounce AND grip strength together, so the two
    signals can never disagree about whether a hand is "closed enough to hold".
    Always runs for BOTH hands regardless of hand preference or game state -
    the per-hand curl math is negligible next to mediapipe's own inference
    cost, so there's no real performance reason to skip either hand.
    """

    def __init__(self):
        self.history = []
        self.confirmed_fist = False
        self.grip_raw = 0
        self.grip_smooth = 0
        self.frames_since_seen = TRACKING_LOST_GRACE + 1

    def update_from_landmarks(self, hand_landmarks):
        self.frames_since_seen = 0

        wrist = hand_landmarks.landmark[0]
        tips = [8, 12, 16, 20]
        mcps = [5, 9, 13, 17]  # knuckle at the base of each finger - stable reference point regardless of curl

        folded = 0
        total_curl = 0
        for tip_idx, mcp_idx in zip(tips, mcps):
            tip = hand_landmarks.landmark[tip_idx]
            mcp = hand_landmarks.landmark[mcp_idx]

            dist_tip = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
            dist_mcp = math.hypot(mcp.x - wrist.x, mcp.y - wrist.y)

            # avoid divide-by-zero if landmarks land exactly on the wrist
            # (shouldn't normally happen, but mediapipe jitter is possible)
            ratio = dist_tip / dist_mcp if dist_mcp > 1e-6 else RATIO_CLOSED

            if ratio < FOLD_RATIO_THRESHOLD:
                folded += 1

            # curl 0 (open, ratio >= RATIO_OPEN) -> 1 (closed, ratio <= RATIO_CLOSED)
            curl = (RATIO_OPEN - ratio) / (RATIO_OPEN - RATIO_CLOSED)
            curl = max(0.0, min(curl, 1.0))
            total_curl += curl

        frame_state = folded >= FIST_FOLDED_THRESHOLD

        self.history.append(frame_state)
        if len(self.history) > FIST_HISTORY_LEN:
            self.history.pop(0)
        self.confirmed_fist = sum(self.history) >= FIST_HISTORY_MIN

        self.grip_raw = int((total_curl / 4) * 100)
        self.grip_smooth = (GRIP_SMOOTH_ALPHA * self.grip_smooth
                             + (1 - GRIP_SMOOTH_ALPHA) * self.grip_raw)

    def tick_no_landmarks(self):
        self.frames_since_seen += 1
        self.grip_smooth = GRIP_SMOOTH_ALPHA * self.grip_smooth

    @property
    def is_tracked(self):
        return self.frames_since_seen <= TRACKING_LOST_GRACE

    @property
    def is_open(self):
        if not self.is_tracked:
            return True
        return not self.confirmed_fist


# ---------------- Camera ---------------- #

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ---------------- State ---------------- #

session_start = time.time()

left_tracker = FistTracker()
right_tracker = FistTracker()

left_x, left_y = -1000, -1000
right_x, right_y = -1000, -1000

# ---------------- Mediapipe ---------------- #
# NOTE: Pose model removed - the chest deposit target is now a fixed
# screen position (see CHEST_POSITION_FRACTION below) instead of being
# tracked from actual shoulder landmarks, so we no longer need Pose
# running at all. This also saves real compute - Pose was the heaviest
# model in this pipeline, previously only throttled to every 3rd frame,
# now dropped entirely.

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2,
                        model_complexity=MODEL_COMPLEXITY,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5)

# ---------------- Main loop ---------------- #

frame_count = 0
chest_x, chest_y = 0, 0
_prev_seen_left, _prev_seen_right = None, None

while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    if frame_count == 0:
        chest_x, chest_y = int(CHEST_POSITION_FRACTION[0] * w), int(CHEST_POSITION_FRACTION[1] * h)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    hand_results = hands.process(rgb)

    # chest position is fixed (CHEST_POSITION_FRACTION), not tracked from
    # body pose - recomputed each frame purely to stay correct if the
    # camera's actual capture resolution ever differs from CAM_WIDTH/HEIGHT
    chest_x, chest_y = int(CHEST_POSITION_FRACTION[0] * w), int(CHEST_POSITION_FRACTION[1] * h)

    frame_count += 1

    if SHOW_CAMERA_WINDOW:
        cv2.circle(frame, (chest_x, chest_y), 25, (0, 0, 255), -1)

    # ---------------- Hand tracking ---------------- #

    seen_left = False
    seen_right = False

    if hand_results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(
            hand_results.multi_hand_landmarks,
            hand_results.multi_handedness
        ):
            label = handedness.classification[0].label

            wrist = hand_landmarks.landmark[0]
            index = hand_landmarks.landmark[8]

            grab_x = int((wrist.x + index.x) / 2 * w)
            grab_y = int((wrist.y + index.y) / 2 * h)

            if label == "Left":
                seen_left = True
                left_tracker.update_from_landmarks(hand_landmarks)
                left_x = int(SMOOTH_ALPHA * left_x + (1 - SMOOTH_ALPHA) * grab_x)
                left_y = int(SMOOTH_ALPHA * left_y + (1 - SMOOTH_ALPHA) * grab_y)
            else:
                seen_right = True
                right_tracker.update_from_landmarks(hand_landmarks)
                right_x = int(SMOOTH_ALPHA * right_x + (1 - SMOOTH_ALPHA) * grab_x)
                right_y = int(SMOOTH_ALPHA * right_y + (1 - SMOOTH_ALPHA) * grab_y)

    if not seen_left:
        left_tracker.tick_no_landmarks()
    if not seen_right:
        right_tracker.tick_no_landmarks()

    # change-only print (not every frame) - lets you verify mediapipe is
    # actually detecting your right hand at all, and that its Left/Right
    # LABEL matches the physical hand you're raising. Mediapipe's
    # handedness classification can get confused by a horizontally-flipped
    # frame (which this script does, for the natural "mirror" feel) - if
    # you raise ONLY your right hand and this prints "left detected"
    # instead of "right detected", that's a mediapipe label-swap, not a
    # detection failure, and needs a different fix (swapping the label
    # when assigning left_tracker/right_tracker above).
    if (seen_left, seen_right) != (_prev_seen_left, _prev_seen_right):
        print(f"[hand detection] left={seen_left} right={seen_right}")
    _prev_seen_left, _prev_seen_right = seen_left, seen_right

    left_fist = left_tracker.confirmed_fist and left_tracker.is_tracked
    right_fist = right_tracker.confirmed_fist and right_tracker.is_tracked

    # ---------------- Debug UI (this window is just a tracking preview now - Unity is the actual game) ---------------- #

    elapsed = time.time() - session_start
    time_left = max(0, int(SESSION_DURATION - elapsed))

    if SHOW_CAMERA_WINDOW:
        cv2.putText(frame, f"Time: {time_left}s", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        with _report_lock:
            r = dict(latest_report)
        cv2.putText(frame, f"Score: {r['score']}  Streak: {r['streak']}", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        def draw_grip_bar(x, label, grip_val, fist):
            cv2.rectangle(frame, (x, 100), (x + 100, 120), (255, 255, 255), 2)
            fill = int((grip_val / 100) * 100)
            color = (0, 255, 0) if fist else (0, 165, 255)
            cv2.rectangle(frame, (x, 100), (x + fill, 120), color, -1)
            cv2.putText(frame, label, (x, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        draw_grip_bar(20, "L", left_tracker.grip_smooth, left_fist)
        draw_grip_bar(140, "R", right_tracker.grip_smooth, right_fist)

    # ---------------- Unity message ---------------- #
    # Python is a sensor + config broadcaster now - Unity owns all star
    # game logic (spawn, pickup, deposit, drop, required-hand, score,
    # streak) locally. Positions sent as 0-1 fractions of the webcam
    # frame so Unity can scale correctly regardless of its own screen
    # resolution.
    #
    # SESSION_DURATION is the 16th field. Unity's HandReceiver picks this
    # up and GameManager seeds its own LOCAL countdown from it exactly
    # once - it does NOT keep resyncing every frame just because this
    # value keeps arriving (it's constant here anyway, riding along with
    # the rest of the regular tracking stream). This avoids running two
    # independently-ticking clocks that could ever disagree.

    norm_left_x, norm_left_y = left_x / w, left_y / h
    norm_right_x, norm_right_y = right_x / w, right_y / h
    norm_chest_x, norm_chest_y = chest_x / w, chest_y / h

    message = (
        f"{norm_left_x:.4f},{norm_left_y:.4f},"
        f"{norm_right_x:.4f},{norm_right_y:.4f},"
        f"{int(left_fist)},{int(right_fist)},"
        f"{left_tracker.grip_raw},{right_tracker.grip_raw},"
        f"{int(left_tracker.is_tracked)},{int(right_tracker.is_tracked)},"
        f"{norm_chest_x:.4f},{norm_chest_y:.4f},"
        f"{ALLOWED_HAND},"
        f"{GRIP_DROP_THRESHOLD},{STAR_TIME_LIMIT},"
        f"{SESSION_DURATION}"
    )

    sock.sendto(message.encode(), (UDP_IP, UDP_PORT))

    if SHOW_CAMERA_WINDOW:
        cv2.imshow("Cosmic Weaver - Tracking", frame)
        # cv2.waitKey() only reads keys while ITS OWN window has focus, so
        # this still works fine when the window is visible. When hidden,
        # this branch never runs at all - the global keyboard hook above
        # is what catches ESC instead.
        if cv2.waitKey(1) == 27:
            _quit_requested = True

    if _quit_requested:
        print("Quit requested (ESC).")
        break
    if session_end_requested:
        print("Unity reported session end.")
        break
    if time_left <= 0:
        print("Session duration fallback reached (Unity never sent SESSION_END).")
        break


cap.release()
cv2.destroyAllWindows()

session_duration_actual = round(time.time() - session_start, 2)

with _report_lock:
    final = dict(latest_report)

# ---------------- Metrics ---------------- #
# Sourced entirely from Unity's own report now, since Unity is the one
# with the real collider-based pickup/deposit/drop decisions.

hand_attempts = final["stars_deposited"] + final["wrong_hand_attempts"]
accuracy = round((final["stars_deposited"] / hand_attempts) * 100, 2) if hand_attempts > 0 else 0

completion_denom = final["stars_deposited"] + final["stars_dropped"]
completion_rate = round((final["stars_deposited"] / completion_denom) * 100, 2) if completion_denom > 0 else 0
# defensive clamp, same spirit as the Vines fix - keep this honest even
# if some future edge case in Unity's counting slips through
completion_rate = max(0, min(completion_rate, 100))

print("------------------")
print("Score:", final["score"])
print("Streak:", final["streak"])
print("Best Streak:", final["best_streak"])
print("------------------")
print("Stars Deposited:", final["stars_deposited"])
print("Stars Dropped:", final["stars_dropped"])
print("Wrong Hand Attempts:", final["wrong_hand_attempts"])
print("Nebula Collected:", final["nebula_collected"])
print("------------------")
print(f"Accuracy: {accuracy}%")
print(f"Completion Rate: {completion_rate}%")
print("Session Duration:", session_duration_actual, "s")
print("------------------")

session_data = {
    "user_id": user_id,
    "game": "cosmic_weaver",
    "date": datetime.now(),

    "metrics": {
        "score": final["score"],
        "best_streak": final["best_streak"],
        "accuracy": accuracy,
        "completion_rate": completion_rate,
        "stars_deposited": final["stars_deposited"],
        "stars_dropped": final["stars_dropped"],
        "wrong_hand_attempts": final["wrong_hand_attempts"],
        "nebula_collected": final["nebula_collected"],
    },

    "session_duration": session_duration_actual,

    "difficulty": {
        "grip_threshold": GRIP_DROP_THRESHOLD,
        "star_time_limit": STAR_TIME_LIMIT,
        "hand_preference": hand_pref_arg,
    }
}

result = sessions.insert_one(session_data)

print("Session saved \u2714")
print("Session ID:", result.inserted_id)

users.update_one(
    {"user_id": user_id},
    {"$inc": {"stats.cosmic_weaver_sessions": 1}}
)