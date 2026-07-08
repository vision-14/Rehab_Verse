import cv2
import mediapipe as mp
import numpy as np
import time
import socket
import sys
from pathlib import Path
from datetime import datetime

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
        msg = f"{vine_index},{target_angle:.2f},{smoothed_angle:.2f},{normalized_height:.2f},{flower_state},{vine_complete}"
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
    
    

    cv2.imshow("Wrist Rehab Game", frame)

    # ---------------- KEYS ---------------- #
   
    key = cv2.waitKey(1) & 0xFF

    if key == ord('c'):
        neutral_angle = current_angle
        print("Calibrated")
        vine_start_time = time.time()
        start=time.time()


    if key == 27:
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