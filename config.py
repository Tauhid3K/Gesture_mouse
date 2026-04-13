# Configuration constants for hand mouse control

# Windows arrow cursor handle (global)
import ctypes
user32 = ctypes.windll.user32
ARROW_CURSOR = user32.LoadCursorW(None, 32512)  # IDC_ARROW

# Hand model
HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
HAND_MODEL_FILE = "hand_landmarker.task"

# Hand landmark indices
THUMB_TIP = 4
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_PIP = 14
RING_TIP = 16
PINKY_PIP = 18
PINKY_TIP = 20
WRIST = 0

# Mouse/trackpad settings
MOUSE_DPI = 1.0
DPI_STEP = 0.1
DPI_MIN = 0.3
DPI_MAX = 3.0

TRACKPAD_SPEED_X = 2.6
TRACKPAD_SPEED_Y = 2.6
TRACKPAD_DEADZONE = 0.0018
TRACKPAD_SMOOTH_ALPHA = 0.45

# Scroll gesture tuning (wheel-like two-axis scrolling)
SCROLL_DEADZONE = 0.003
SCROLL_VERTICAL_GAIN = 800
SCROLL_SPEED_MULTIPLIER_MIN = 1
SCROLL_SPEED_MULTIPLIER_MAX = 6
SCROLL_SPEED_MULTIPLIER_DEFAULT = 1
SCROLL_HORIZONTAL_GAIN = 900
SCROLL_MAX_STEP = 18
SCROLL_ACCEL_POWER = 1.0
SCROLL_SMOOTH_ALPHA = 0.30

# Display/UI
DISPLAY_SCALE = 0.62
WINDOW_BOTTOM_OFFSET = 70
WINDOW_MARGIN = 10

UI_MARGIN = 10
UI_BUTTON_W = 88
UI_BUTTON_H = 32
UI_GAP = 8
SETTINGS_WINDOW_W = 360
SETTINGS_WINDOW_H = 180
