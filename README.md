# Fachhe-25: Gesture Control Hub

Welcome to **Fachhe-25**, a repository dedicated to computer vision-based gesture control systems. This project explores low-latency interaction for gaming using **Python**, **OpenCV**, and **MediaPipe**.

The repository contains two main projects:
1.  **NFS:MW Gesture Controller**: A universal input injector designed for racing games like *Need for Speed: Most Wanted*.
2.  **The Car Game**: A custom-built Pygame racing experience designed specifically for hand tracking.

---

## Project 1: NFS:MW Gesture Controller

A robust, low-latency computer vision controller designed to replace your keyboard while driving. It maps specific hand configurations to key presses using `pydirectinput` (Windows) or `pynput` (Linux).

### Features
-   **Cross-Platform**: Automatically detects OS and selects the correct input engine.
-   **Zero-Copy Latency**: Uses threaded camera capture and input downscaling to minimize delay.
-   **Resource Efficient**: Runs on MediaPipe "Lite" model complexity for maximum FPS on integrated graphics.
-   **Priority Logic**: Intelligent input handling (e.g., "Nitro" overrides standard acceleration).

### 🎮 Controls (Finger Counting)

| Left Hand | Right Hand | Action | Keys Mapped |
| :---: | :---: | :--- | :--- |
| ☝️ **1 Finger** | ☝️ **1 Finger** | **Accelerate** | `W` |
| ✌️ **2 Fingers** | ☝️ **1 Finger** | **Turn Left + Gas** | `W` + `A` |
| ☝️ **1 Finger** | ✌️ **2 Fingers** | **Turn Right + Gas** | `W` + `D` |
| ✌️ **2 Fingers** | ✌️ **2 Fingers** | **🔥 NITRO BOOST** | `W` + `X` |
| 🤟 **3 Fingers** | 🤟 **3 Fingers** | **Brake / Reverse** | `S` |

**Single Hand Actions (When the other hand is not detected):**
| Hand Used | Gesture | Action | Keys Mapped |
| :--- | :--- | :--- | :--- |
| **Left** | ✌️ **2 Fingers** | Coast Left | `A` |
| **Right** | ✌️ **2 Fingers** | Coast Right | `D` |
| **Left** | 🤟 **3 Fingers** | Reverse Left | `S` + `A` |
| **Right** | 🤟 **3 Fingers** | Reverse Right | `S` + `D` |

### Usage
1.  Navigate to the `NSF_MW` directory.
2.  Run the optimized script:
    ```bash
    python optimized_for_any_os.py
    ```
3.  Keep the camera window in view and focus on your game window.

---

## Project 2: The Car Game (Pygame)

A standalone vertical scrolling racing game built with **Pygame**. It features an integrated hand-tracking thread that controls a car to dodge traffic and collect scores.

### Features
-   **Gesture-Based Drifting**: Uses "OK Signs" for rapid lateral movement (dodging).
-   **Dynamic Difficulty**: Traffic speed and spawn rates increase as your score goes up.
-   **Calibration Mode**: Ensures the game doesn't start until you are ready.
-   **High Score System**: Persists your best runs locally.

### Controls (Palm & Fist Logic)

| Left Hand | Right Hand | Action | Description |
| :---: | :---: | :--- | :--- |
| ✋ **Open Palm** | ✋ **Open Palm** | **Accelerate** | Moves the car forward. |
| 👌 **OK Sign** | *(Any)* | **Left Dodge** | Rapidly shifts car to the Left. |
| *(Any)* | 👌 **OK Sign** | **Right Dodge** | Rapidly shifts car to the Right. |
| ✋ **Open Palm** | ✊ **Fist** | **Turn Left** | Standard steering to the Left. |
| ✊ **Fist** | ✋ **Open Palm** | **Turn Right** | Standard steering to the Right. |
| ✊ **Fist** | ✊ **Fist** | **Brake / Calibrate** | Slows down or starts calibration. |

### Usage
1.  Navigate to the `The Car Game` directory.
2.  Ensure the `assets` folder contains the required images (`car.png`, `road_X.png`, `traffic_car_X.png`).
3.  Run the game script (or the Jupyter Notebook):
    ```bash
    python controlled_with_keyboard.py  # For keyboard testing
    # OR open "Hand_controlled.ipynb" to run the gesture version
    ```

---

## Installation & Setup

### Prerequisites
You need **Python 3.10+** installed.

### Dependencies
Install the required libraries.

**For Windows:**
```bash
pip install opencv-python mediapipe pydirectinput pygame
```
**For Linux (Arch/Debian/Fedora etc.)**
```bash
pip install opencv-python mediapipe pynput pygame
```
**Configurations:**
You can tweak performance settings in `optimized_for_any_os.py` inside the `Config` class:
```Python
class Config:
    SHOW_CAMERA = True          # Toggle debug overlay
    MODEL_COMPLEXITY = 0        # 0 = Fast (Lite), 1 = Accurate (Full)
    PROCESS_RES = (640, 480)    # Lower resolution = Lower latency
```
*Note: Ensure you have good lighting for the best hand-tracking performance.*
