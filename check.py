import cv2
import time 
import random
import mediapipe as mp 
import math 

def dist(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)


def is_fist(hand_landmarks):

    tips = [8,12,16,20]
    pips = [6,10,14,18]

    folded = 0

    for tip,pip in zip(tips,pips):
        if hand_landmarks.landmark[tip].y > hand_landmarks.landmark[pip].y:
            folded += 1

    return folded >= 3





cap = cv2.VideoCapture(0)

collected = False
score = 0
state="IDLE"
release_timer=0
near_chest = False
hand=None # 0:left 1:right 
prev_left_fist = False
prev_right_fist = False
required_hand=random.choice([0,1])
oops_timer=0
left_x, left_y = -1000, -1000
right_x, right_y = -1000, -1000
grab_x,grab_y=-1000,-1000

target_x=random.randint(50,590)
target_y=random.randint(50,430)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

mp_hands=mp.solutions.hands
hands=mp_hands.Hands( max_num_hands=2,
                     min_detection_confidence=0.5,
                     min_tracking_confidence=0.5)

while True:
    success,frame=cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape   # for default 
    chest_x, chest_y = w//2, h//2 

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    hand_results = hands.process(rgb)

    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark

        left_shoulder = lm[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]


        ls_x, ls_y = int(left_shoulder.x * w), int(left_shoulder.y * h)
        rs_x, rs_y = int(right_shoulder.x * w), int(right_shoulder.y * h)

        chest_x = (ls_x + rs_x) // 2
        chest_y = (ls_y + rs_y) // 2 +40

    text = "LEFT HAND" if required_hand == 0 else "RIGHT HAND"

    cv2.putText( frame, text, (200,40),
    cv2.FONT_HERSHEY_SIMPLEX, 1,(0,255,0),2)
   
    cv2.circle(frame, (target_x, target_y), 15, (0, 255, 255), -1)
    cv2.circle(frame, (chest_x, chest_y), 25, (0, 0, 255), -1)
    cv2.circle(frame, (chest_x, chest_y), 40, (0, 0, 255), 2)

    left_fist = False
    right_fist = False

    if hand_results.multi_hand_landmarks:

        for hand_landmarks, handedness in zip(
            hand_results.multi_hand_landmarks,
        hand_results.multi_handedness
        ):

            label = handedness.classification[0].label

            index = hand_landmarks.landmark[8]
            middle = hand_landmarks.landmark[12]

            grab_x = int((index.x + middle.x)/2 * w)
            grab_y = int((index.y + middle.y)/2 * h)

            fist = is_fist(hand_landmarks)

            if label == "Left":
                left_fist = fist
                left_x = grab_x
                left_y = grab_y  
            else:
                right_fist = fist
                right_x=grab_x
                right_y=grab_y

    left_release = prev_left_fist and not left_fist
    right_release = prev_right_fist and not right_fist 

    
    left_grasp = (not prev_left_fist) and left_fist
    right_grasp = (not prev_right_fist) and right_fist     
    
    if not collected:
        if dist(left_x, left_y, target_x, target_y) < 40 and left_grasp :
            if required_hand==0:
                collected = True
                hand=0
            else:
                oops_timer=30
        if dist (right_x, right_y, target_x, target_y)<40 and right_grasp :
             if required_hand==1:
                collected=True
                hand=1
             else:
                oops_timer=30

    #ERROR MESSAGE     
    if oops_timer > 0:

        cv2.putText(frame,"OOPS! TRY USING DIFFERENT HAND!!",(80,100),cv2.FONT_HERSHEY_SIMPLEX,1,
        (0,0,255),3)

        oops_timer -= 1

    if collected :
        if hand==0:
            target_x, target_y = left_x, left_y
        else:
            target_x, target_y = right_x, right_y

    
    if collected:
        released = False
        if hand==0:
            released = left_release
        elif hand ==1:
            released = right_release

        if dist(target_x, target_y, chest_x, chest_y) < 50 and released:
            score += 1
            collected = False
            target_x = random.randint(50, 590)
            target_y = random.randint(50, 430)
            hand=None
            required_hand = random.choice([0,1])


    prev_left_fist = left_fist
    prev_right_fist = right_fist       

    cv2.putText(frame, f"Score: {score}", (20, 40),
    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    cv2.imshow("Rehabverse Camera",frame)


    if(cv2.waitKey(1)==27):
        break

cap.release()
cv2.destroyAllWindows()