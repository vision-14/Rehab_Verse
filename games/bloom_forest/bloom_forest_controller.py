import cv2
import mediapipe as mp
import numpy as np
import time
import socket
import sys
from pathlib import Path
from datetime import datetime

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("[vines_backend] pywin32 not installed - camera window won't be "
          "pinned on top of Unity. Run: pip install pywin32")

# NEW: global keyboard hook, so 'c' (calibrate) and ESC (quit) work even
# while the Unity window has focus - cv2.waitKey() only receives keys
# when the OpenCV window itself is focused, which isn't reliable once
# Unity is sitting visually on top of it. This listens system-wide
# instead of depending on window focus at all.
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    print("[vines_backend] 'keyboard' package not installed - C/ESC will "
          "only work while the camera window itself has focus. Run: "
          "pip install keyboard")

_calibrate_requested = False
_quit_requested = False


def _on_global_key(event):
    global _calibrate_requested, _quit_requested
    if event.event_type != "down":
        return
    if event.name == "c":
        _calibrate_requested = True
    elif event.name == "esc":
        _quit_requested = True


if HAS_KEYBOARD:
    keyboard.hook(_on_global_key)

# db.py and game_login.py live in games/common/, shared by every game
# backend (not just this one) - this just tells Python where to find them.
sys.path.append(str(Path(__file__).resolve().parent.parent / "common"))

from db import users, sessions
from game_login import login

# ---------------- UDP SETUP ---------------- #

UDP_IP = "127.0.0.1"
UDP_PORT = 5052
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# -----------------LOGIN/REGISTER-------------#
# If the app already authenticated this person (passed as a command-line
# argument when launching this script), reuse that account instead of
# prompting again in this console. Otherwise, fall back to the original
# interactive login - e.g. when this script is run standalone for testing.
if len(sys.argv) > 1:
    user_id = sys.argv[1].strip().upper()
    print(f"Continuing as {user_id} (signed in via RehabVerse)")
    if not users.find_one({"user_id": user_id}):
        print("Unexpected: user not found in DB, falling back to manual login.")
        user_id = login()
else:
    user_id = login()

# ---------------- CALIBRATION ---------------- #
neutral_angle = None
hold_time_required = 5
max_down = 45      # flexion targetar
max_up = 30        # extension target

last_session = sessions.find_one(
    {
        "user_id": user_id,
        "game": "Vines"
    },
    sort=[("date", -1)]
)

if last_session:

    # Load previous difficulty
    hold_time_required = last_session["difficulty"]["hold_time"]
    max_down = last_session["difficulty"]["flexion_target"]
    max_up = last_session["difficulty"]["extension_target"]

    completion = last_session["metrics"]["completion_rate"]

    # ---------- Adaptive Hold Time ----------
    if completion > 90:
        hold_time_required += 1
    elif completion < 70:
        hold_time_required -= 1

    hold_time_required = min(max(hold_time_required, 3), 8)

    # ---------- Adaptive Flexion Target ----------
    prev_flexion = last_session["metrics"]["flexion_rom"]

    if prev_flexion >= 0.95 * max_down:
        max_down += 5
    elif prev_flexion < 0.7 * max_down:
        max_down -= 5

    # ---------- Adaptive Extension Target ----------
    prev_extension = last_session["metrics"]["extension_rom"]

    if prev_extension >= 0.95 * max_up:
        max_up += 5
    elif prev_extension < 0.7 * max_up:
        max_up -= 5

    # Safety limits
    max_down = min(max(max_down, 20), 80)
    max_up = min(max(max_up, 20), 70)

print(f"Hold Time : {hold_time_required}s")
print(f"Flexion Target : {max_down}°")
print(f"Extension Target : {max_up}°")

# ---------------- GAME STATE ---------------- #
vine_index = 0
total_vines = 4

flower_state = 0
vine_complete = 0
hand_label=None
try_angle=0

vine_start_time = 0
max_vine_time = 20   # seconds
failed_vines = 0

flowers = 0
buds = 0
leaves = 0

stable_frames = 0
total_frames = 0


max_rom = -999

repetitions = 0

best_hold = 0
# ---------------- SMOOTHING ---------------- #
alpha = 0.2
smoothed_angle = 0
first_frame = True

# ---------------- HOLD ---------------- #
settle_time_required=3
settling=False

hold_started = False
hold_start_time = 0
max_drop = 0
hold_angles = []
previous_value = 0
hold_ui_text = ""
hold_ui_time = 0
hold_ui_duration = 5# how long message stays after update



#-------Metrics------#
max_flexion=80
max_extension=70
flexion_percent=0
extension_percent=0
extension_rom=0
flexion_rom=0


accuracy_errors = []
stability_values = []


reach_time=[]

# ---------------- CAMERA WINDOW POSITIONING ---------------- #
# NEW: the camera preview is centered inside the empty green placeholder
# area of the Unity scene, borderless (no title bar / minimize / close
# buttons), and kept focused so keyboard input (C / ESC) keeps reaching
# it even while Unity is visually underneath it.
#
# Position/size are computed from Unity's ACTUAL client area at runtime
# (via GetClientRect + ClientToScreen), not hardcoded pixels - so this
# keeps working correctly regardless of where Unity's window is on
# screen, or if its size differs slightly from the expected build res.

WINDOW_NAME = "Wrist Rehab Game"
UNITY_WINDOW_TITLE = "wristrehab"   # must match the Unity build's title bar text

# The green placeholder's size as a fraction of Unity's client area,
# measured from the actual running build. Adjust these two if the green
# zone's proportions ever change in the Unity scene.
GREEN_AREA_W_FRAC = 0.42
GREEN_AREA_H_FRAC = 0.86

# Camera window size: a fraction of the green area's width, keeping the
# same landscape aspect ratio as before (320/480), so it sits centered
# with a bit of margin instead of filling the green zone edge-to-edge.
CAM_SIZE_FRAC = 0.9
CAM_ASPECT_HW = 320 / 480  # height/width ratio

# Fallback size/position used only if Unity's window can't be found yet
# (e.g. pywin32 missing, or Unity hasn't opened) - keeps the camera
# visible somewhere reasonable instead of failing silently.
FALLBACK_W, FALLBACK_H = 420, 280
FALLBACK_X, FALLBACK_Y = 900, 50

_last_pin_time = 0
PIN_INTERVAL = 1.0    # seconds - re-pin periodically so the camera
                       # window can't quietly fall behind Unity later.
_borderless_applied = False

# NEW: tracks whether Unity's window has ever been seen, so we can tell
# "Unity closed" (was seen, now gone) apart from "Unity hasn't opened
# yet" (never seen) - only the former should trigger auto-quit.
_unity_ever_seen = False


def get_unity_client_rect_on_screen():
    """Returns (screen_x, screen_y, width, height) of Unity's CLIENT
    area (i.e. excluding its title bar/border), or None if the window
    can't be found yet."""
    if not HAS_WIN32:
        return None
    hwnd = win32gui.FindWindow(None, UNITY_WINDOW_TITLE)
    if not hwnd:
        return None
    _, _, width, height = win32gui.GetClientRect(hwnd)
    screen_x, screen_y = win32gui.ClientToScreen(hwnd, (0, 0))
    return screen_x, screen_y, width, height


def unity_window_closed():
    """Returns True only if Unity's window was previously confirmed open
    and can no longer be found - meaning the person closed the Unity
    game window, so this script should shut down too instead of running
    on with no game to talk to."""
    global _unity_ever_seen
    if not HAS_WIN32:
        return False

    hwnd = win32gui.FindWindow(None, UNITY_WINDOW_TITLE)
    if hwnd:
        _unity_ever_seen = True
        return False

    return _unity_ever_seen


def make_camera_window_borderless(hwnd):
    """Strips the title bar text, close/minimize/maximize buttons and
    resize border from the OpenCV window, leaving just the raw feed."""
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~win32con.WS_CAPTION
    style &= ~win32con.WS_THICKFRAME
    style &= ~win32con.WS_MINIMIZEBOX
    style &= ~win32con.WS_MAXIMIZEBOX
    style &= ~win32con.WS_SYSMENU
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)


def pin_camera_window_on_top():
    """Centers the OpenCV window inside Unity's green placeholder area
    and keeps it borderless + topmost. No-op if pywin32 isn't installed;
    falls back to a fixed position/size if Unity's window can't be found
    yet. (Keyboard focus is handled separately via a global hook, not by
    forcing window focus here - that was unreliable.)"""
    if not HAS_WIN32:
        return False

    cam_hwnd = win32gui.FindWindow(None, WINDOW_NAME)
    if not cam_hwnd:
        return False

    global _borderless_applied
    if not _borderless_applied:
        make_camera_window_borderless(cam_hwnd)
        _borderless_applied = True

    unity_rect = get_unity_client_rect_on_screen()
    if unity_rect:
        ux, uy, uw, uh = unity_rect
        green_w = uw * GREEN_AREA_W_FRAC
        green_h = uh * GREEN_AREA_H_FRAC

        cam_w = max(int(green_w * CAM_SIZE_FRAC), 160)
        cam_h = max(int(cam_w * CAM_ASPECT_HW), 120)

        pos_x = int(ux + (green_w - cam_w) / 2)
        pos_y = int(uy + (green_h - cam_h) / 2)
    else:
        cam_w, cam_h = FALLBACK_W, FALLBACK_H
        pos_x, pos_y = FALLBACK_X, FALLBACK_Y

    win32gui.SetWindowPos(
        cam_hwnd, win32con.HWND_TOPMOST,
        pos_x, pos_y, cam_w, cam_h,
        win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED
    )

    return True


# ---------------- MEDIAPIPE ---------------- #
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(0)
start=time.time()

# NEW: just create the window here - pin_camera_window_on_top() computes
# the correct size/position from Unity's actual client area and applies
# it (plus borderless + topmost + focus) the first time it's shown below.
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)


# ---------------- TARGET SYSTEM ---------------- #
def get_target_right(i):
    if i == 0:
        return 0.3 * max_up+10, "DOWN"
    elif i == 1:
        return 0.4 * max_up+10, "DOWN"
    elif i == 2:
        return -0.3 * max_down-10, "UP"
    else:
        return -0.4 * max_down-10, "UP"
    
def get_target_left(i):
    if i == 0:
        return 0.3 * max_up+10, "UP"
    elif i == 1:
        return 0.4 * max_up+10, "UP"
    elif i == 2:
        return -0.3 * max_down-10, "DOWN"
    else:
        return -0.4 * max_down-10, "DOWN"


target_angle, direction = get_target_left(vine_index)

normalized_height = 0

# ---------------- LOOP ---------------- #
while True:
    ret, frame = cap.read()
    if not ret:
        break
    

    frame = cv2.flip(frame, 1)
   
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    vine_complete = 0

    # NEW: when a vine times out (fails), we need to send its "frozen at
    # 0.2 height" state using the OLD vine_index, in the SAME frame that
    # vine_index gets incremented - otherwise the fail message ends up
    # tagged to the wrong (new) vine, and the actually-failed vine never
    # gets told to settle at 0.2, so it visually stays wherever it last
    # grew to. This override, if set below, is sent instead of the
    # normal end-of-loop message for this one frame.
    pending_udp_override = None

    if results.multi_hand_landmarks:

        hand = results.multi_hand_landmarks[0]
        hand_label = results.multi_handedness[0].classification[0].label
        lm = hand.landmark

        if(hand_label=="Left"):
            target_angle, direction = get_target_left(vine_index)
        else:
            target_angle, direction = get_target_right(vine_index)

        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

        wrist = lm[0]
        middle_mcp = lm[9]

        dx = middle_mcp.x - wrist.x
        dy = middle_mcp.y - wrist.y

        current_angle = np.degrees(np.arctan2(-dy, dx))

        # ---------------- CALIBRATION ---------------- #
        if neutral_angle is not None:
            rehab_angle = current_angle - neutral_angle
            if rehab_angle > 180:
                rehab_angle -= 360
            elif rehab_angle < -180:
                rehab_angle += 360

            max_rom = max(max_rom, abs(rehab_angle))
            if hand_label == "Right":
                extension_sign = -1
                flexion_sign = 1
            else:  # Left
                extension_sign = 1
                flexion_sign = -1
            
            if np.sign(rehab_angle) == extension_sign:
                extension_rom = max(extension_rom,
                            abs(rehab_angle))

            elif np.sign(rehab_angle) == flexion_sign:
                flexion_rom = max(flexion_rom,
                          abs(rehab_angle))
                
                

            # ---------------- SMOOTHING ---------------- #
            if first_frame:
                smoothed_angle = rehab_angle
                first_frame = False
            else:
                smoothed_angle = (
                    alpha * rehab_angle +
                    (1 - alpha) * smoothed_angle
                )

            # ---------------- DEAD ZONE ---------------- #
            if abs(smoothed_angle) < 2:
                smoothed_angle = 0
            total_frames += 1

            # ---------------- NORMALIZE ---------------- #
            normalized_height = abs(smoothed_angle) / max(max_up, 1)
            normalized_height = np.clip(normalized_height, 0, 1)

            # ---------------- TARGET CHECK ---------------- #

            if time.time() - vine_start_time > max_vine_time:

                flower_state = 0          # leaves

                vine_complete = 1

                normalized_height = 0.2

                leaves += 1
                failed_vines+= 1

                # NEW: build the fail message for the OLD (failed) vine's
                # index BEFORE incrementing - this is what makes Unity
                # actually freeze that vine at 0.2 height instead of it
                # staying wherever it last grew to.
                calibrated_now = 1 if neutral_angle is not None else 0
                pending_udp_override = (
                    f"{vine_index},{target_angle:.2f},{smoothed_angle:.2f},"
                    f"0.20,{flower_state},{vine_complete},"
                    f"{calibrated_now},{direction},Time's up!"
                )

                vine_index += 1

                vine_start_time = time.time()

                hold_started = False
                settling = False
            
            if abs(smoothed_angle - target_angle) < 5:
                stable_frames += 1
                if not settling and not hold_started:

                   settling = True
                   settle_start_time = time.time()

                   hold_ui_text = "Stabilize..."
                   hold_ui_time = time.time()
    

                elif settling and  not hold_started:
                    if time.time() - settle_start_time >= settle_time_required:
                        hold_started = True
                        hold_start_time = time.time()
                        hold_angles = []
                        previous_value=normalized_height
                        hold_ui_text = "Hold steady..."

                elif hold_started:

                    hold_angles.append(smoothed_angle)
                    error = abs(smoothed_angle - target_angle)
                    accuracy_errors.append(error)
                    elapsed = time.time() - hold_start_time
                    best_hold = max(best_hold, elapsed)

                

                    if elapsed >= hold_time_required:
                        reach_time.append(time.time()-vine_start_time)
                        vine_complete = 1

                    # FLOWER LOGIC
                        stability = np.std(hold_angles)
                        stability_values.append(stability)

                        if stability < 1.5:
                           flower_state = 2
                           flowers+=1
                        elif stability < 3:
                           flower_state = 1
                           buds+=1
                        else:
                           flower_state = 0
                           leaves+=1

                        print(flower_state)
                        print(stability)

                    # MOVE TO NEXT VINE
                        vine_index += 1
                        vine_start_time=time.time()

                        if vine_index < total_vines:
                            if(hand_label=="Left"):
                                 target_angle, direction = get_target_left(vine_index)
                            else:
                                target_angle, direction = get_target_right(vine_index)
                            hold_started = False
                            max_drop = 0
                            previous_value = 0
                            settling=False
                            print("Next vine:", vine_index)
                        else:
                            print("ALL VINES COMPLETE")
                            
            
            else:
                hold_started = False
                previous_value = normalized_height
                hold_ui_text = "Keep moving..."
                

        # ---------------- UDP SEND ---------------- #
        if pending_udp_override is not None:
            # NEW: a vine just timed out this frame - send its frozen
            # 0.2-height fail message (built above, tagged to the OLD
            # vine index) instead of the normal live-height message.
            msg = pending_udp_override
        else:
            calibrated = 1 if neutral_angle is not None else 0
            status_text = hold_ui_text if hold_ui_text else "Move to Calibrate" if not calibrated else ""

            msg = (
                f"{vine_index},{target_angle:.2f},{smoothed_angle:.2f},"
                f"{normalized_height:.2f},{flower_state},{vine_complete},"
                f"{calibrated},{direction},{status_text}"
            )

        sock.sendto(msg.encode(), (UDP_IP, UDP_PORT))
        if(vine_index==5):
            break


    # ---------------- UI ---------------- #
    overlay = frame.copy()

    cv2.rectangle(
    overlay,
    (10, 10),      # top-left
    (300, 220),    # bottom-right
    (100, 100, 100),  # color (BGR)
    -1             # filled rectangle
    )
    a = 0.5  # transparency (0 = invisible, 1 = solid)

    cv2.addWeighted(
    overlay,
    a,
    frame,
    1 - alpha,
    0,
    frame
)
    
    cv2.rectangle(
        frame,
         (10, 10),
    (300, 220),
    (255, 255, 255),  # white border
    2                 # thickness

    )


    cv2.putText(frame, f"Vine {vine_index+1}/4", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

    cv2.putText(frame, f"Target: {abs(target_angle):.1f} ({direction})", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)

    cv2.putText(frame, f"Angle: {(smoothed_angle):.1f}", (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
    
    # Right side message (temporary UI)
    if hold_ui_text != "":

        cv2.putText(
        frame,
        hold_ui_text,
        (450, 100),  # RIGHT SIDE POSITION (adjust if needed)
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )

    cv2.putText(frame, f"Height: {normalized_height:.2f}", (20, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

    cv2.putText(frame, f"Flower: {flower_state}", (20, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)
    

    cv2.putText(frame, "C: calibrate | ESC: quit", (20, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 2)
    

    # NEW: since the OS window chrome is stripped (borderless), draw a
    # decorative frame border directly on the image - deep green outer
    # line + a thin gold accent line inside it, matching the vines/nature
    # theme, so the camera preview still reads as a deliberate framed UI
    # element rather than a bare floating video.
    fh, fw = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (fw - 1, fh - 1), (20, 90, 20), 10)
    cv2.rectangle(frame, (12, 12), (fw - 13, fh - 13), (50, 205, 255), 3)

    cv2.imshow(WINDOW_NAME, frame)

    # NEW: pin/position the window against Unity periodically, and check
    # whether Unity's window has closed - if it has (and we'd previously
    # seen it open), quit this script too instead of running with no
    # game to talk to.
    if time.time() - _last_pin_time > PIN_INTERVAL:
        pin_camera_window_on_top()
        if unity_window_closed():
            print("Unity window closed - shutting down controller too.")
            _quit_requested = True
        _last_pin_time = time.time()

    # ---------------- KEYS ---------------- #
    # NEW: 'c'/ESC can come from either cv2.waitKey (works when the
    # camera window itself has focus) OR the global keyboard hook (works
    # even while Unity's window has focus) OR Unity having closed on its
    # own (handled above as a forced quit).
    key = cv2.waitKey(1) & 0xFF

    calibrate_now = (key == ord('c')) or _calibrate_requested
    quit_now = (key == 27) or _quit_requested

    if calibrate_now:
        neutral_angle = current_angle
        print("Calibrated")
        vine_start_time = time.time()
        start=time.time()
        _calibrate_requested = False

    if quit_now:
        break

cap.release()
cv2.destroyAllWindows()
session =time.time()-start


avg_stability = np.mean(stability_values)


best_hold=round(best_hold,2)
session=round(session,2)
session = round(session, 2)

#--------Mobility metrics------#

rom=max_rom
rom = round(rom, 2)

flexion_rom=round(flexion_rom,2)
extension_rom=round(extension_rom,2)


flexion_rom=min(flexion_rom,max_flexion)
extension_rom=min(extension_rom,max_extension)

flexion_percent = (flexion_rom / max_flexion) * 100
extension_percent = (extension_rom / max_extension) * 100

flexion_percent = min(flexion_percent, 100)
extension_percent = min(extension_percent, 100)

flexion_percent=round(flexion_percent,2)
extension_percent=round(extension_percent,2)

#-------Control------#
avg_stability = np.mean(stability_values)
avg_stability=round(avg_stability,2)
if len(accuracy_errors) > 0:
    avg_error = np.mean(accuracy_errors)
else:
    avg_error = 0
accuracy_score = max(0, 100 - avg_error * 5)
accuracy_score = round(accuracy_score, 2)

#----Performance-----#
if len(reach_time) > 0:
    avg_reach_time = round(np.mean(reach_time), 2)
    best_reach_time = round(min(reach_time), 2)
else:
    avg_reach_time = 0
    best_reach_time = 0
if(vine_index!=0):
    completion_rate=((vine_index-failed_vines)/vine_index) * 100
else:
    completion_rate=0



print("------------------")
print("Flowers:", flowers)
print("Buds:", buds)
print("Leaves:", leaves)
print("Session:", session)
print("------------------")
print("Average Hold Stability:", avg_stability)
print("Accuracy:", accuracy_score, "%")
print("------------------")
print("ROM:", rom)
print("Flexion Rom : ",flexion_rom,"/",max_flexion)
print("Extension rom: ",extension_rom,"/",max_extension)
print(f"Flexion Recovery: {flexion_percent}%")
print(f"Extension Recovery: {extension_percent}%")
print("------------------")
print(f"Average Reach Time: {avg_reach_time} s")
print(f"Best Reach Time: {best_reach_time} s")
print("Best Hold:", best_hold)
print(
    f"Completion Rate: {completion_rate}"
)
print("------------------")
print(hand_label)

#---------Passing data----------#
session_data = {
    "user_id": user_id,
    "game": "vines",
    "date": datetime.now(),

    "metrics": {
        "rom": max_rom,
        "flexion_rom": flexion_rom,
        "extension_rom": extension_rom,
        "accuracy":accuracy_score,
        "completion_rate": completion_rate,
        "best_hold": best_hold,
        "avg_reach_time": avg_reach_time
    },

    "session_duration": session,


    "difficulty": {
    "hold_time": hold_time_required,
    "flexion_target": max_down,
    "extension_target": max_up
}
}

result = sessions.insert_one(session_data)

print("Session saved ✔")
print("Session ID:", result.inserted_id)

users.update_one(
    {"user_id": user_id},
    {"$inc": {"stats.vines_sessions": 1}}
)

for doc in sessions.find({"user_id": user_id}):
    print(doc)