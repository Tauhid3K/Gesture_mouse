# Gesture detection and mouse control logic for hand mouse

import ctypes
import time
import pyautogui
from utils import fingertip_touch, dist

# Enable this for scroll debugging: change False → True to see console output
DEBUG_SCROLL = False

from config import (
    THUMB_TIP, INDEX_TIP, MIDDLE_TIP, PINKY_TIP, WRIST, INDEX_PIP, MIDDLE_MCP,
    MIDDLE_PIP, RING_PIP, RING_TIP, PINKY_PIP, THUMB_IP, INDEX_MCP, PINKY_MCP,
    THUMB_MCP, RING_MCP,
    TRACKPAD_DEADZONE, TRACKPAD_SMOOTH_ALPHA, TRACKPAD_SPEED_X, TRACKPAD_SPEED_Y,
    SCROLL_DEADZONE, SCROLL_VERTICAL_GAIN, SCROLL_HORIZONTAL_GAIN, SCROLL_MAX_STEP,
    SCROLL_ACCEL_POWER, SCROLL_SMOOTH_ALPHA,
)

THREE_FINGER_THRESHOLD = 0.25 # Reliable for pinch
SELECT_HOLD_SECONDS = 0.24
SELECT_RELEASE_GRACE_SECONDS = 0.15
DRAG_SMOOTH_ALPHA = 0.18
DRAG_SPEED_SCALE = 0.65
CLICK_HOLD_SECONDS = 0.03

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
INPUT_MOUSE = 0

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]

def _send_mouse_flag(flag):
    """Send a low-level mouse flag via SendInput."""
    user32 = ctypes.windll.user32
    input_obj = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(
            mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flag, time=0, dwExtraInfo=0)
        ),
    )
    sent = user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))
    if sent != 1:
        user32.mouse_event(flag, 0, 0, 0, 0)

def send_mouse_button(button="left", is_down=True):
    """Send native Windows mouse button down/up events."""
    if button == "left":
        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    else:
        down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    _send_mouse_flag(down_flag if is_down else up_flag)

def send_mouse_click(button="left"):
    """Send a native Windows click with a tiny hold."""
    send_mouse_button(button=button, is_down=True)
    time.sleep(CLICK_HOLD_SECONDS)
    send_mouse_button(button=button, is_down=False)

def is_fist_gesture(lm, min_folded=3):
    """Detect a closed fist by checking whether most non-thumb fingertips are folded."""
    wrist = lm[WRIST]
    folded_count = 0
    for tip, pip in [(INDEX_TIP, INDEX_PIP), (MIDDLE_TIP, MIDDLE_PIP), 
                     (RING_TIP, RING_PIP), (PINKY_TIP, PINKY_PIP)]:
        if dist(lm[tip], wrist) < dist(lm[pip], wrist):
            folded_count += 1
    return folded_count >= min_folded

def is_proper_fist(lm):
    """A stricter fist check: all non-thumb fingers must be folded and thumb must be tucked."""
    # 1. All 4 main fingers must be folded
    if not is_fist_gesture(lm, min_folded=4):
        return False
    # 2. Thumb tip should be close to the palm/knuckles, not extended
    wrist = lm[WRIST]
    scale = dist(lm[WRIST], lm[MIDDLE_MCP])
    thumb_to_wrist = dist(lm[THUMB_TIP], wrist)
    # In a proper fist, the thumb is usually tucked over fingers or palm.
    # Its distance to wrist is much smaller than when extended.
    if thumb_to_wrist > (scale * 1.5):
        return False
    return True

def is_thumbs_up(lm):
    """Detect Thumbs Up: Strict vertical check with palm clearance."""
    # 1. All non-thumb fingers must be tightly folded
    wrist = lm[WRIST]
    for tip, pip in [(INDEX_TIP, INDEX_PIP), (MIDDLE_TIP, MIDDLE_PIP), 
                     (RING_TIP, RING_PIP), (PINKY_TIP, PINKY_PIP)]:
        if dist(lm[tip], wrist) > dist(lm[pip], wrist):
            return False
    # 2. Strict vertical extension
    if not (lm[THUMB_TIP].y < lm[THUMB_IP].y < lm[THUMB_MCP].y):
        return False
    # 3. Palm clearance
    palm_y = (lm[INDEX_MCP].y + lm[MIDDLE_MCP].y + lm[RING_MCP].y + lm[PINKY_MCP].y) / 4.0
    return lm[THUMB_TIP].y < palm_y - 0.08

def is_thumbs_down(lm):
    """Detect Thumbs Down: Strict vertical check with palm clearance."""
    # 1. All non-thumb fingers must be tightly folded
    wrist = lm[WRIST]
    for tip, pip in [(INDEX_TIP, INDEX_PIP), (MIDDLE_TIP, MIDDLE_PIP), 
                     (RING_TIP, RING_PIP), (PINKY_TIP, PINKY_PIP)]:
        if dist(lm[tip], wrist) > dist(lm[pip], wrist):
            return False
    # 2. Strict vertical extension
    if not (lm[THUMB_TIP].y > lm[THUMB_IP].y > lm[THUMB_MCP].y):
        return False
    # 3. Palm clearance
    palm_y = (lm[INDEX_MCP].y + lm[MIDDLE_MCP].y + lm[RING_MCP].y + lm[PINKY_MCP].y) / 4.0
    return lm[THUMB_TIP].y > palm_y + 0.08

def get_palm_center(lm):
    """Return a palm-base anchor that is insensitive to finger articulation."""
    wrist = lm[WRIST]
    index_mcp = lm[INDEX_MCP]
    pinky_mcp = lm[PINKY_MCP]

    # Use wrist + side MCPs only, so moving fingers does not shift cursor anchor.
    palm_x = (wrist.x + index_mcp.x + pinky_mcp.x) / 3.0
    palm_y = (wrist.y + index_mcp.y + pinky_mcp.y) / 3.0
    return palm_x, palm_y

def is_two_finger_scroll_gesture(lm):
    """Detect index and middle up while ring and pinky stay folded."""
    index_up = lm[INDEX_TIP].y < lm[INDEX_PIP].y
    middle_up = lm[MIDDLE_TIP].y < lm[MIDDLE_PIP].y
    wrist = lm[WRIST]
    ring_down = dist(lm[RING_TIP], wrist) < dist(lm[RING_PIP], wrist)
    pinky_down = dist(lm[PINKY_TIP], wrist) < dist(lm[PINKY_PIP], wrist)
    return index_up and middle_up and (ring_down or pinky_down)

def apply_horizontal_scroll(amount):
    if amount == 0: return
    if hasattr(pyautogui, "hscroll"):
        pyautogui.hscroll(amount)
    else:
        pyautogui.keyDown("shift")
        try: pyautogui.scroll(amount)
        finally: pyautogui.keyUp("shift")

def offset_to_scroll_step(offset, gain, deadzone=SCROLL_DEADZONE):
    magnitude = abs(offset)
    if magnitude <= deadzone: return 0
    effective = magnitude - deadzone
    step = int(round((effective * gain) ** SCROLL_ACCEL_POWER))
    step = max(1, min(SCROLL_MAX_STEP, step))
    return step if offset > 0 else -step

class GestureState:
    def __init__(self, cursor_x, cursor_y, dpi, scroll_multiplier):
        self.cursor_x = float(cursor_x)
        self.cursor_y = float(cursor_y)
        self.dpi = float(dpi)
        self.scroll_multiplier = float(scroll_multiplier)
        self.prev_mid_x = None
        self.prev_mid_y = None
        self.filtered_dx = 0.0
        self.filtered_dy = 0.0
        self.pinch_start_time = None
        self.select_last_seen_time = None
        self.is_dragging = False
        self.last_left_click = 0.0
        self.last_right_click = 0.0
        self.last_volume_step = 0.0
        self.right_touch_prev = False
        self.scroll_active = False
        self.prev_scroll_x = None
        self.prev_scroll_y = None
        self.filtered_scroll_offset_x = 0.0
        self.filtered_scroll_offset_y = 0.0

    def reset_movement(self):
        if self.is_dragging:
            pyautogui.mouseUp(button="left")
            self.is_dragging = False
        self.prev_mid_x = None
        self.prev_mid_y = None
        self.filtered_dx = 0.0
        self.filtered_dy = 0.0
        self.pinch_start_time = None
        self.select_last_seen_time = None
        self.scroll_active = False
        self.prev_scroll_x = None
        self.prev_scroll_y = None
        self.filtered_scroll_offset_x = 0.0
        self.filtered_scroll_offset_y = 0.0
        self.right_touch_prev = False

def process_scroll_motion(mid_x, mid_y, state: GestureState):
    if not state.scroll_active:
        state.scroll_active = True
        state.prev_scroll_x = mid_x
        state.prev_scroll_y = mid_y
        state.filtered_scroll_offset_x = 0.0
        state.filtered_scroll_offset_y = 0.0
    else:
        raw_offset_y = mid_y - state.prev_scroll_y
        state.filtered_scroll_offset_y += (raw_offset_y - state.filtered_scroll_offset_y) * SCROLL_SMOOTH_ALPHA
        scroll_offset_y = state.filtered_scroll_offset_y
        if raw_offset_y != 0.0 and (scroll_offset_y * raw_offset_y) < 0.0:
            scroll_offset_y = raw_offset_y

        base_scroll_amount = offset_to_scroll_step(-scroll_offset_y, SCROLL_VERTICAL_GAIN)
        scroll_amount = int(round(base_scroll_amount * state.scroll_multiplier))
        if scroll_amount != 0:
            pyautogui.scroll(scroll_amount)

        raw_offset_x = mid_x - state.prev_scroll_x
        state.filtered_scroll_offset_x += (raw_offset_x - state.filtered_scroll_offset_x) * SCROLL_SMOOTH_ALPHA
        hscroll_amount = offset_to_scroll_step(state.filtered_scroll_offset_x, SCROLL_HORIZONTAL_GAIN)
        if hscroll_amount != 0:
            apply_horizontal_scroll(hscroll_amount)

def is_three_finger_touch(lm, hand_scale):
    """Thumb, Index, and Middle fingertips touching (standard robust check)."""
    thumb_tip = lm[THUMB_TIP]
    index_tip = lm[INDEX_TIP]
    middle_tip = lm[MIDDLE_TIP]
    d1 = dist(thumb_tip, index_tip)
    d2 = dist(thumb_tip, middle_tip)
    threshold = THREE_FINGER_THRESHOLD * hand_scale
    return d1 < threshold and d2 < threshold

def is_any_finger_folded(lm):
    """Check if any of the four main fingers are folded toward the wrist."""
    wrist = lm[WRIST]
    for tip, pip in [(INDEX_TIP, INDEX_PIP), (MIDDLE_TIP, MIDDLE_PIP), 
                     (RING_TIP, RING_PIP), (PINKY_TIP, PINKY_PIP)]:
        if dist(lm[tip], wrist) < dist(lm[pip], wrist):
            return True
    return False

def is_select_gesture(lm, hand_scale):
    """Detect the gesture used for click/select and drag. Returns False if hand is a fist or open."""
    # 1. Require at least ONE of the main fingers (Index, Middle, Ring, Pinky) to be folded.
    # This prevents an open hand from accidentally triggering a "select" if tips look close.
    if not is_any_finger_folded(lm):
        return False

    # 2. Check for pinch gestures (tighter ratio for precision)
    pinch = (fingertip_touch(lm, THUMB_TIP, INDEX_TIP, hand_scale, ratio=0.25) or 
             fingertip_touch(lm, THUMB_TIP, MIDDLE_TIP, hand_scale, ratio=0.25) or 
             is_three_finger_touch(lm, hand_scale))
    
    if not pinch:
        return False

    # 3. Finally, ensure it's not a full fist (which often puts thumb near tips)
    if is_proper_fist(lm):
        return False
        
    return True

def is_thumb_pinky_touch(lm, hand_scale):
    """Check for thumb-pinky touch, used for right clicks."""
    return fingertip_touch(lm, THUMB_TIP, PINKY_TIP, hand_scale, ratio=0.30)

def update_select_drag_state(select_touch, keep_dragging, state: GestureState, now):
    """Convert a select gesture into click or drag behavior. 
    If dragging, persists until keep_dragging is False (hand fully open)."""
    if select_touch:
        state.select_last_seen_time = now
        if state.pinch_start_time is None:
            state.pinch_start_time = now
        elif not state.is_dragging and (now - state.pinch_start_time) >= SELECT_HOLD_SECONDS:
            pyautogui.mouseDown(button="left")
            state.is_dragging = True
    elif state.is_dragging and keep_dragging:
        # Lenient Drag: Even if pinch is lost, keep the mouse down as long as some fingers are folded.
        state.select_last_seen_time = now # Refresh grace period
        return
    else:
        # Tolerate short tracking dropouts while pinching to prevent accidental drag release.
        if state.select_last_seen_time is not None and (now - state.select_last_seen_time) <= SELECT_RELEASE_GRACE_SECONDS:
            return
        if state.is_dragging:
            pyautogui.mouseUp(button="left")
            state.is_dragging = False
        elif state.pinch_start_time is not None:
            send_mouse_click(button="left")
        state.pinch_start_time = None
        state.select_last_seen_time = None

def process_right_hand_gestures(lm, virtual_left, virtual_top, screen_w, screen_h, state: GestureState, now):
    hand_scale = max(dist(lm[WRIST], lm[MIDDLE_MCP]), 1e-6)
    mid_x, mid_y = get_palm_center(lm)
    
    select_touch = is_select_gesture(lm, hand_scale)
    keep_dragging = is_any_finger_folded(lm)
    right_touch = fingertip_touch(lm, THUMB_TIP, PINKY_TIP, hand_scale, ratio=0.30)
    
    # Check for volume gestures to suppress other actions
    vol_gesture = is_thumbs_up(lm) or is_thumbs_down(lm)

    if select_touch or right_touch or vol_gesture:
        scroll_gesture = False
    else:
        scroll_gesture = is_two_finger_scroll_gesture(lm)

    if state.prev_mid_x is None:
        state.prev_mid_x, state.prev_mid_y = mid_x, mid_y
    else:
        raw_dx = mid_x - state.prev_mid_x
        raw_dy = mid_y - state.prev_mid_y
        state.prev_mid_x, state.prev_mid_y = mid_x, mid_y

        if abs(raw_dx) < TRACKPAD_DEADZONE: raw_dx = 0.0
        if abs(raw_dy) < TRACKPAD_DEADZONE: raw_dy = 0.0

        smooth_alpha = DRAG_SMOOTH_ALPHA if state.is_dragging else TRACKPAD_SMOOTH_ALPHA
        speed_scale = DRAG_SPEED_SCALE if state.is_dragging else 1.0
        state.filtered_dx += (raw_dx - state.filtered_dx) * smooth_alpha
        state.filtered_dy += (raw_dy - state.filtered_dy) * smooth_alpha

        # Allow movement if dragging or if no click gesture is held.
        movement_blocked = scroll_gesture or (select_touch and not state.is_dragging and (now - (state.pinch_start_time or now)) < 0.05) or right_touch or vol_gesture
        if not movement_blocked:
            state.cursor_x += state.filtered_dx * screen_w * TRACKPAD_SPEED_X * state.dpi * speed_scale
            state.cursor_y += state.filtered_dy * screen_h * TRACKPAD_SPEED_Y * state.dpi * speed_scale
            state.cursor_x = max(float(virtual_left), min(float(virtual_left + screen_w - 1), state.cursor_x))
            state.cursor_y = max(float(virtual_top), min(float(virtual_top + screen_h - 1), state.cursor_y))
            pyautogui.moveTo(state.cursor_x, state.cursor_y)

    if scroll_gesture:
        process_scroll_motion(mid_x, mid_y, state)
    else:
        state.scroll_active = False
