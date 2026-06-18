import cv2
import random
import mediapipe as mp
import math
import time

# ---------------- Utils ---------------- #

def dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

# ---------------- Improved Fist Detection ---------------- #

fist_history_left = []
fist_history_right = []

def is_fist(hand_landmarks, history):
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]

    folded = 0
    for tip, pip in zip(tips, pips):
        if hand_landmarks.landmark[tip].y > hand_landmarks.landmark[pip].y:
            folded += 1

    state = folded >= 4  # stricter threshold

    history.append(state)
    if len(history) > 5:
        history.pop(0)

    return sum(history) >= 3  # debounce


#-----Grip Strenth----#
def grip_strength(hand_landmarks):

    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]

    total_curl = 0

    for tip, pip in zip(tips, pips):

        tip_y = hand_landmarks.landmark[tip].y
        pip_y = hand_landmarks.landmark[pip].y

        curl = (tip_y - pip_y) * 8

        curl = max(0, min(curl, 1))

        total_curl += curl

    strength = (total_curl / 4) * 100

    return int(strength)



# ---------------- Camera ---------------- #

cap = cv2.VideoCapture(0)

#-------Time-----#
session_start = time.time()
session_duration = 60  

# ---------------- Game State ---------------- #

score = 0
state="IDLE"
collected = False
hand = None
required_hand = random.choice([0, 1])
oops_timer = 0
message_timer=0
depositing=False
deposit_buffer=0
streak = 0
combo_ready = False
streak_count=0
max_streak=0
drop=0
wrong_hand=0
total=1

#grip items
left_grip_raw = 0
right_grip_raw = 0
grip_smooth=0
active_grip=0
alpha_grip = 0.2   # smoothing factor

# smoothing factor
alpha = 0.7

# positions
left_x, left_y = -1000, -1000
right_x, right_y = -1000, -1000
target_x = random.randint(100, 540)
target_y = random.randint(100, 300)

# locks (prevents repeated triggers)
left_locked = False
right_locked = False

# ---------------- Mediapipe ---------------- #

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2,
                       min_detection_confidence=0.5,
                       min_tracking_confidence=0.5)

# ---------------- Main Loop ---------------- #

while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    hand_results = hands.process(rgb)

    # ---------------- Chest detection ---------------- #

    chest_x, chest_y = w // 2, h // 2

    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark

        ls = lm[mp_pose.PoseLandmark.LEFT_SHOULDER]
        rs = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]

        ls_x, ls_y = int(ls.x * w), int(ls.y * h)
        rs_x, rs_y = int(rs.x * w), int(rs.y * h)

        chest_x = (ls_x + rs_x) // 2
        chest_y = (ls_y + rs_y) // 2 + 40

    # ---------------- UI ---------------- #

    text = "LEFT HAND" if required_hand == 0 else "RIGHT HAND"
    cv2.putText(frame, text, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.circle(frame, (target_x, target_y), 15, (0, 255, 255), -1)
    cv2.circle(frame, (chest_x, chest_y), 25, (0, 0, 255), -1)

    # ---------------- Hand Tracking ---------------- #

    left_fist = False
    right_fist = False

    if hand_results.multi_hand_landmarks:

        for hand_landmarks, handedness in zip(
            hand_results.multi_hand_landmarks,
            hand_results.multi_handedness
        ):

            label = handedness.classification[0].label

            wrist = hand_landmarks.landmark[0]
            index = hand_landmarks.landmark[8]

            if label == "Left":
                left_grip_raw = grip_strength(hand_landmarks)
            if label == "Right":
                right_grip_raw = grip_strength(hand_landmarks)
            
            grab_x = int((wrist.x + index.x) / 2 * w)
            grab_y = int((wrist.y + index.y) / 2 * h)

            fist = is_fist(
                hand_landmarks,
                fist_history_left if label == "Left" else fist_history_right
            )

            if label == "Left":
                left_fist = fist

                # smoothing
                left_x = int(alpha * left_x + (1 - alpha) * grab_x)
                left_y = int(alpha * left_y + (1 - alpha) * grab_y)

            else:
                right_fist = fist

                right_x = int(alpha * right_x + (1 - alpha) * grab_x)
                right_y = int(alpha * right_y + (1 - alpha) * grab_y)

    # ---------------- Grasp / Release ---------------- #

    left_grasp = left_fist and not left_locked
    right_grasp = right_fist and not right_locked

    left_release = not left_fist
    right_release = not right_fist

    grab_zone = 55

    # ---------------- Pick Object ---------------- #

    if not collected:

        if abs(left_x - target_x) < grab_zone and abs(left_y - target_y) < grab_zone and left_grasp:
            if required_hand == 0:
                collected = True
                hand = 0
                left_locked = True
                state="HELD"
            else:
                streak = 0
                combo_ready = False 
                wrong_hand+=1  #wrong hand to streak lost 
                oops_timer = 30

        if abs(right_x - target_x) < grab_zone and abs(right_y - target_y) < grab_zone and right_grasp:
            if required_hand == 1:
                collected = True
                hand = 1
                right_locked = True
                state="HELD"
            else:
                streak = 0
                combo_ready = False
                wrong_hand+=1
                oops_timer = 30

    if state == "HELD":
        if dist(target_x, target_y, chest_x, chest_y) < 60:
            depositing = True
            deposit_buffer=20
        else:
            depositing=False

    if state=="HELD":
        if hand==0:
            active_grip=left_grip_raw
        elif hand ==1:
            active_grip=right_grip_raw
        else:
            active_grip=0
        grip_smooth = alpha_grip * grip_smooth + (1 - alpha_grip) * active_grip

    # ---------------- OOPS MESSAGE ---------------- #

    if oops_timer > 0:
        cv2.putText(frame,
                    "OOPS! USE DIFFERENT HAND",
                    (max(10, w // 6)+10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2)
        oops_timer -= 1

        #-------DROP GRIP------#
    if message_timer > 0:
         cv2.putText(frame,
                "OOPS!TRY AGAIN",
                (max(10, w // 6)+100, 60),
                 cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2)
         message_timer -= 1

    # ---------------- Carry Object ---------------- #

    if collected:
        if hand == 0:
            target_x, target_y = left_x, left_y
        else:
            target_x, target_y = right_x, right_y
    if collected:
       grip_value = grip_smooth
    else:
       grip_value = 0

    if state == "HELD":
        if deposit_buffer>0:
            deposit_buffer-=1
        elif grip_smooth < 50 and (not depositing):
            state = "IDLE"
            hand = None
            grip_smooth = 0
            drop+=1
            message_timer = 20
            collected=False
            left_locked = False
            right_locked = False


    # ---------------- Drop Mechanic ---------------- #

    if collected:
        released = (left_release if hand == 0 else right_release)

        if dist(target_x, target_y, chest_x, chest_y) < 60 and released:
            
            streak += 1

            if streak >= 3:
                combo_ready = True
                streak_count=streak//3
                max_streak=max(max_streak,streak_count)
            
            if combo_ready:
                score += 2**streak_count
            else:
                score += 1

            collected = False
            hand = None
            state="IDLE"
            left_locked = False
            right_locked = False

            target_x = random.randint(100, 540)
            target_y = random.randint(100, 380)
            total+=1
            required_hand = random.choice([0, 1])


            #----Time----#
    elapsed = time.time() - session_start
    time_left = max(0, int(session_duration - elapsed))

    # ---------------- UI ELEMENTS ---------------- #

    cv2.putText(frame, f"Score: {score}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1,
                (255, 255, 255), 2)
    cv2.putText(frame,
            f"Time Left: {time_left}s",
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2)
    bar_w, bar_h = 200, 20

    bar_x = w - bar_w - 20   # RIGHT SIDE with padding
    bar_y = 40               # top margin

    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (255,255,255), 2)

    fill = int((grip_value / 100) * bar_w)

    cv2.rectangle(frame,
              (bar_x, bar_y),
              (bar_x + fill, bar_y + bar_h),
              (0, 255, 0),
              -1)

    cv2.putText(frame,
            f"Grip: {int(grip_value)}%",
            (bar_x, bar_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0,0,0),
            2)
    if combo_ready:
        cv2.putText(frame,
                f"Combo x{ 2**streak_count}",
                (20, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2)
        
    cv2.imshow("Rehabverse Camera", frame)

    if cv2.waitKey(1) == 27:
        break
    if time_left <= 0:
        break

cap.release()
cv2.destroyAllWindows()

print(score)
print(drop)
print(wrong_hand)
print(total)
print(max_streak)