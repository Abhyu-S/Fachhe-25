import cv2
import mediapipe as mp
import pydirectinput
import time
import math
import win32gui
import win32con
from threading import Thread

# --- Configuration ---
SHOW_CAMERA_FEED = True
CAMERA_FEED_TITLE = "NFS:MW Keyboard Controller"
RESIZE_FACTOR = 2

# --- Threaded Camera Class ---
class CameraStream:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.grabbed, self.frame = self.stream.read()
        self.stopped = False
    def start(self):
        Thread(target=self.update, args=()).start()
        return self
    def update(self):
        while not self.stopped:
            self.grabbed, self.frame = self.stream.read()
    def read(self):
        return self.frame
    def stop(self):
        self.stopped = True
        self.stream.release()

# --- Class Definitions ---
class HandTracker:
    def __init__(self, max_hands=2, detection_confidence=0.6, tracking_confidence=0.7): # Lowered confidence for better tracking
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=max_hands, min_detection_confidence=detection_confidence, min_tracking_confidence=tracking_confidence)
        self.mp_draw = mp.solutions.drawing_utils
        self.hand_data = {}

    def _get_hand_state(self, hand_landmarks):
        landmarks = hand_landmarks.landmark
        def is_finger_extended(tip_idx, pip_idx): return landmarks[tip_idx].y < landmarks[pip_idx].y
        thumb_up, index_up, middle_up, ring_up, pinky_up = is_finger_extended(4, 3), is_finger_extended(8, 6), is_finger_extended(12, 10), is_finger_extended(16, 14), is_finger_extended(20, 18)
        fingers_up_count = sum([index_up, middle_up, ring_up, pinky_up])
        thumb_tip, index_tip = landmarks[self.mp_hands.HandLandmark.THUMB_TIP], landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        if math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y) < 0.1: return 'OK_SIGN'
        if thumb_up and fingers_up_count == 0: return 'THUMBS_UP'
        if fingers_up_count >= 4: return 'OPEN'
        if fingers_up_count == 0: return 'FIST'
        return 'NEUTRAL'

    def process_frame(self, image):
        if image is None: return None
        self.hand_data = {}
        image_flipped = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image_flipped, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image_rgb)
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                hand_label = handedness.classification[0].label
                state = self._get_hand_state(hand_landmarks)
                self.hand_data[hand_label] = state
                if SHOW_CAMERA_FEED: self.mp_draw.draw_landmarks(image_bgr, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        return image_bgr

    def get_gestures(self):
        return self.hand_data.get('Left'), self.hand_data.get('Right')

class KeyController:
    def __init__(self):
        self.key_map = {
            'accelerate': {'w'}, 'brake': {'s'},
            'steer_left': {'w', 'a'}, 'steer_right': {'w', 'd'},
            'coast_steer_left': {'a'}, 'coast_steer_right': {'d'}, # New coasting keys
            'nitro': {'x', 'w'}, 'reverse_left': {'s', 'a'}, 'reverse_right': {'s', 'd'}
        }
        self.currently_pressed = set()
        print("Hybrid keyboard controller initialized.")

    def update(self, left_hand_state, right_hand_state):
        target_keys = set()
        
        # --- GESTURE LOGIC HIERARCHY ---
        # Priority 1: Special moves (OK Sign)
        if left_hand_state == 'OK_SIGN' and right_hand_state == 'OK_SIGN':
            target_keys.update(self.key_map['nitro'])
        elif left_hand_state == 'OK_SIGN':
            target_keys.update(self.key_map['reverse_left'])
        elif right_hand_state == 'OK_SIGN':
            target_keys.update(self.key_map['reverse_right'])
            
        # Priority 2: Two-Handed Driving
        elif left_hand_state and right_hand_state:
            if left_hand_state == 'OPEN' and (right_hand_state in ['FIST', 'THUMBS_UP']):
                target_keys.update(self.key_map['steer_right'])
            elif right_hand_state == 'OPEN' and (left_hand_state in ['FIST', 'THUMBS_UP']):
                target_keys.update(self.key_map['steer_left'])
            elif left_hand_state == 'OPEN' and right_hand_state == 'OPEN':
                target_keys.update(self.key_map['accelerate'])
            elif left_hand_state == 'FIST' and right_hand_state == 'FIST':
                target_keys.update(self.key_map['brake'])
        
        # Priority 3: NEW Single-Handed "Coasting" Steer
        elif left_hand_state == 'FIST' and not right_hand_state:
            target_keys.update(self.key_map['coast_steer_left'])
        elif right_hand_state == 'FIST' and not left_hand_state:
            target_keys.update(self.key_map['coast_steer_right'])

        keys_to_press = target_keys - self.currently_pressed
        for key in keys_to_press: pydirectinput.keyDown(key)
        keys_to_release = self.currently_pressed - target_keys
        for key in keys_to_release: pydirectinput.keyUp(key)
        self.currently_pressed = target_keys

    def release_all_keys(self):
        for key in self.currently_pressed: pydirectinput.keyUp(key)
        self.currently_pressed.clear()
        print("All keys released.")

# --- Main Application Logic ---
def main():
    CAMERA_SOURCE = 0
    controller = KeyController()
    print(f"Attempting to connect to camera source: {CAMERA_SOURCE}")
    camera_stream = CameraStream(src=CAMERA_SOURCE).start()
    time.sleep(1.0)
    if camera_stream.read() is None:
        print("Error: Could not open camera source."); return
    print("Camera connection successful.")
    tracker = HandTracker()
    is_overlay_set = False
    
    while True:
        image = camera_stream.read()
        processed_image = tracker.process_frame(image)
        if processed_image is None: continue
        left_hand, right_hand = tracker.get_gestures()
        controller.update(left_hand, right_hand)
        
        if SHOW_CAMERA_FEED:
            action_text = "Coasting"
            if left_hand == 'OK_SIGN' and right_hand == 'OK_SIGN': action_text = "Nitro Boost"
            elif left_hand == 'OK_SIGN': action_text = "Reverse Left"
            elif right_hand == 'OK_SIGN': action_text = "Reverse Right"
            elif left_hand and right_hand:
                if left_hand == 'OPEN' and (right_hand in ['FIST', 'THUMBS_UP']): action_text = "Accel & Steer Right"
                elif right_hand == 'OPEN' and (left_hand in ['FIST', 'THUMBS_UP']): action_text = "Accel & Steer Left"
                elif left_hand == 'OPEN' and right_hand == 'OPEN': action_text = "Accelerate"
                elif left_hand == 'FIST' and right_hand == 'FIST': action_text = "Brake"
            elif left_hand == 'FIST' and not right_hand: action_text = "Coasting Steer Left"
            elif right_hand == 'FIST' and not left_hand: action_text = "Coasting Steer Right"   
            
            resized_image = cv2.resize(processed_image, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
            cv2.putText(resized_image, f"Action: {action_text}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(resized_image, f"L: {left_hand} | R: {right_hand}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow(CAMERA_FEED_TITLE, resized_image)

            if not is_overlay_set:
                try:
                    hwnd = win32gui.FindWindow(None, CAMERA_FEED_TITLE)
                    if hwnd: win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,0,0,0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE); is_overlay_set = True
                except Exception: pass

        if cv2.waitKey(1) & 0xFF == ord('q'): break
        
    controller.release_all_keys()
    camera_stream.stop()
    cv2.destroyAllWindows()
    print("Controller stopped.")

if __name__ == "__main__":
    main()
