import cv2
import mediapipe as mp
import time
import math
import platform
import sys
from threading import Thread
from typing import Dict, Optional, Tuple

# --- Configuration & Tuning ---
class Config:
    APP_TITLE = "NFS:MW Gesture Controller"
    SHOW_CAMERA = True
    
    # 0 = Lite (Fastest), 1 = Full
    MODEL_COMPLEXITY = 0 
    # Process at lower res to reduce latency (VGA)
    PROCESS_RES = (640, 480) 
    
    CAMERA_ID = 0
    MIN_DETECT_CONF = 0.5
    MIN_TRACK_CONF = 0.5

# --- Input Abstraction (Cross-Platform) ---
class InputController:
    def __init__(self):
        self.system = platform.system()
        self.pressed_keys = set()
        
        if self.system == "Windows":
            try:
                import pydirectinput
                self._engine = pydirectinput
                self._engine.FAILSAFE = False 
            except ImportError:
                print("❌ Missing 'pydirectinput'. pip install pydirectinput")
                sys.exit(1)
        elif self.system == "Linux":
            try:
                from pynput.keyboard import Key, Controller
                self._engine = Controller()
            except ImportError:
                print("❌ Missing 'pynput'. pip install pynput")
                sys.exit(1)
        else:
            print(f"❌ Unsupported OS: {self.system}")
            sys.exit(1)
            
        print(f"✅ Input Engine initialized for: {self.system}")

    def press(self, key: str):
        if key in self.pressed_keys: return
        if self.system == "Windows": self._engine.keyDown(key)
        elif self.system == "Linux": self._engine.press(key)
        self.pressed_keys.add(key)

    def release(self, key: str):
        if key not in self.pressed_keys: return
        if self.system == "Windows": self._engine.keyUp(key)
        elif self.system == "Linux": self._engine.release(key)
        self.pressed_keys.remove(key)

    def release_all(self):
        for key in list(self.pressed_keys):
            self.release(key)

# --- Threaded Camera (Zero-Copy Latency) ---
class CameraStream:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        # Force MJPG for higher FPS on USB cams
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1280) 
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.stream.release()

# --- Logic Core ---
class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands=2,
            model_complexity=Config.MODEL_COMPLEXITY, 
            min_detection_confidence=Config.MIN_DETECT_CONF,
            min_tracking_confidence=Config.MIN_TRACK_CONF
        )

    def process(self, frame) -> Tuple[dict, object]:
        # Latency Hack: Resize BEFORE processing
        small_frame = cv2.resize(frame, Config.PROCESS_RES)
        img_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)
        
        hand_data = {}
        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                label = results.multi_handedness[idx].classification[0].label
                state = self._classify_gesture(hand_landmarks)
                hand_data[label] = state
                if Config.SHOW_CAMERA:
                    self.mp_draw.draw_landmarks(small_frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
        return hand_data, small_frame

    def _classify_gesture(self, landmarks) -> str:
        lm = landmarks.landmark
        
        # Check if specific fingers are extended (Tip above PIP joint)
        index_up = lm[8].y < lm[6].y
        middle_up = lm[12].y < lm[10].y
        ring_up = lm[16].y < lm[14].y
        pinky_up = lm[20].y < lm[18].y
        
        count = sum([index_up, middle_up, ring_up, pinky_up])
        
        # Exact logic from easy_version.py
        if count == 1 and index_up: return 'ONE_FINGER'
        if count == 2 and index_up and middle_up: return 'TWO_FINGERS'
        if count == 3 and index_up and middle_up and ring_up: return 'THREE_FINGERS'
        
        return 'NEUTRAL'

class GameLoop:
    def __init__(self):
        self.input = InputController()
        self.cam = CameraStream(Config.CAMERA_ID).start()
        self.tracker = HandTracker()
        
        # Mapping Logic
        self.key_map = {
            'accelerate': ['w'], 
            'accel_left': ['w', 'a'], 
            'accel_right': ['w', 'd'],
            'nitro': ['x', 'w'],
            'coast_left': ['a'], 
            'coast_right': ['d'],
            'reverse_straight': ['s'],
            'reverse_left': ['s', 'a'], 
            'reverse_right': ['s', 'd']
        }
        
    def run(self):
        print(f"🚀 {Config.APP_TITLE} Started")
        print("Press 'q' to quit.")
        try:
            while True:
                frame = self.cam.read()
                if frame is None: continue
                frame = cv2.flip(frame, 1) # Mirror
                
                gestures, debug_frame = self.tracker.process(frame)
                self._handle_input(gestures)
                
                if Config.SHOW_CAMERA:
                    self._draw_overlay(debug_frame, gestures)
                    cv2.imshow(Config.APP_TITLE, debug_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'): break
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.input.release_all()
            self.cam.stop()
            cv2.destroyAllWindows()
            print("\n🛑 Stopped safely.")

    def _handle_input(self, gestures):
        left = gestures.get('Left', None)
        right = gestures.get('Right', None)
        target_keys = set()
        
        # --- PRIORITY LOGIC (from windows optimized version) ---
        
        # 1. Reverse Straight (Both 3 fingers)
        if left == 'THREE_FINGERS' and right == 'THREE_FINGERS':
            target_keys.update(self.key_map['reverse_straight'])
            
        # 2. Nitro (Both 2 fingers)
        elif left == 'TWO_FINGERS' and right == 'TWO_FINGERS':
            target_keys.update(self.key_map['nitro'])
            
        # 3. Driving (Combined Hands)
        elif left and right:
            if left == 'ONE_FINGER' and right == 'ONE_FINGER':
                target_keys.update(self.key_map['accelerate'])
            elif left == 'TWO_FINGERS' and right == 'ONE_FINGER':
                target_keys.update(self.key_map['accel_left'])
            elif left == 'ONE_FINGER' and right == 'TWO_FINGERS':
                target_keys.update(self.key_map['accel_right'])
                
        # 4. Single Hand Actions
        # Only check these if no two-handed action triggered
        if not target_keys:
            if left == 'TWO_FINGERS': target_keys.update(self.key_map['coast_left'])
            if left == 'THREE_FINGERS': target_keys.update(self.key_map['reverse_left'])
            if right == 'TWO_FINGERS': target_keys.update(self.key_map['coast_right'])
            if right == 'THREE_FINGERS': target_keys.update(self.key_map['reverse_right'])

        # Apply Input
        for key in target_keys:
            self.input.press(key)
        for key in list(self.input.pressed_keys):
            if key not in target_keys:
                self.input.release(key)

    def _draw_overlay(self, img, gestures):
        keys = " ".join(sorted(list(self.input.pressed_keys))).upper()
        cv2.putText(img, f"KEYS: {keys}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(img, f"L: {gestures.get('Left','-')} | R: {gestures.get('Right','-')}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

if __name__ == "__main__":
    GameLoop().run()
