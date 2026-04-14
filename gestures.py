# Gesture detection and mouse control logic for hand mouse

import ctypes
import time
import pyautogui
from utils import fingertip_touch, dist

# Enable this for scroll debugging: change False → True to see console output
DEBUG_SCROLL = False

from config import (
    THUMB_TIP, INDEX_TIP, MIDDLE_TIP, PINKY_TIP, WRIST, INDEX_PIP, MIDDLE_MCP,
    MIDDLE_PIP, RING_PIP, RING_TIP, PINKY_PIP,
    TRACKPAD_DEADZONE, TRACKPAD_SMOOTH_ALPHA, TRACKPAD_SPEED_X, TRACKPAD_SPEED_Y,
    SCROLL_DEADZONE, SCROLL_VERTICAL_GAIN, SCROLL_HORIZONTAL_GAIN, SCROLL_MAX_STEP,
    SCROLL_ACCEL_POWER, SCROLL_SMOOTH_ALPHA,
)
THREE_FINGER_THRESHOLD = 0.06
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
    """Send a low-level mouse flag via SendInput (more reliable than mouse_event)."""
    user32 = ctypes.windll.user32
    input_obj = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(
            mi=MOUSEINPUT(
                dx=0,
                dy=0,
                mouseData=0,
                dwFlags=flag,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )
    sent = user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))
    if sent != 1:
        # Fallback for environments where SendInput is restricted.
        user32.mouse_event(flag, 0, 0, 0, 0)


def send_mouse_button(button="left", is_down=True):
    """Send native Windows mouse button down/up events."""
    if button == "left":
        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    else:
        down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    _send_mouse_flag(down_flag if is_down else up_flag)


def send_mouse_click(button="left"):
    """Send a native Windows click with a tiny hold for OSK key reliability."""
    send_mouse_button(button=button, is_down=True)
    time.sleep(CLICK_HOLD_SECONDS)
    send_mouse_button(button=button, is_down=False)



def is_fist_gesture(right_lm):
    """Detect a closed fist by checking whether all non-thumb fingertips are folded."""
    return (
        right_lm[INDEX_TIP].y > right_lm[INDEX_PIP].y
        and right_lm[MIDDLE_TIP].y > right_lm[MIDDLE_PIP].y
        and right_lm[RING_TIP].y > right_lm[RING_PIP].y
        and right_lm[PINKY_TIP].y > right_lm[PINKY_PIP].y
    )


def get_palm_center(right_lm):
    """Return a stable palm anchor using palm joints, with slightly steadier vertical tracking."""
    wrist = right_lm[WRIST]
    index_mcp = right_lm[5]
    middle_mcp = right_lm[MIDDLE_MCP]
    ring_mcp = right_lm[13]
    pinky_mcp = right_lm[17]

    palm_x = (wrist.x + index_mcp.x + middle_mcp.x + ring_mcp.x + pinky_mcp.x) / 5.0

    # Vertical motion is more stable when centered around the middle of the palm
    # instead of averaging all joints equally.
    palm_y = (wrist.y + (middle_mcp.y * 2.0) + ring_mcp.y) / 4.0
    return palm_x, palm_y


def is_two_finger_scroll_gesture(right_lm):
    """Detect the hand sign with index and middle up while ring and pinky stay folded."""
    index_up = right_lm[INDEX_TIP].y < right_lm[INDEX_PIP].y
    middle_up = right_lm[MIDDLE_TIP].y < right_lm[MIDDLE_PIP].y
    ring_down = right_lm[RING_TIP].y > right_lm[RING_PIP].y
    pinky_down = right_lm[PINKY_TIP].y > right_lm[PINKY_PIP].y
    
    gesture = index_up and middle_up and ring_down and pinky_down
    
    return gesture


def apply_horizontal_scroll(amount):
    """Send horizontal scroll with a fallback for environments without hscroll support."""
    if amount == 0:
        return
    if hasattr(pyautogui, "hscroll"):
        pyautogui.hscroll(amount)
        return

    # Fallback: Shift + vertical wheel is interpreted as horizontal scroll by many apps.
    pyautogui.keyDown("shift")
    try:
        pyautogui.scroll(amount)
    finally:
        pyautogui.keyUp("shift")


def offset_to_scroll_step(offset, gain, deadzone=SCROLL_DEADZONE):
    """Map anchor distance to wheel step using a non-linear acceleration curve."""
    magnitude = abs(offset)
    if magnitude <= deadzone:
        return 0

    effective = magnitude - deadzone
    step = int(round((effective * gain) ** SCROLL_ACCEL_POWER))
    step = max(1, min(SCROLL_MAX_STEP, step))
    return step if offset > 0 else -step


class GestureState:
    """Holds all persistent state for hand gestures and cursor control."""

    def __init__(self, cursor_x, cursor_y, dpi, scroll_multiplier):
        # Cursor tracking state
        self.cursor_x = float(cursor_x)
        self.cursor_y = float(cursor_y)
        self.dpi = float(dpi)
        self.scroll_multiplier = float(scroll_multiplier)
        self.prev_mid_x = None
        self.prev_mid_y = None
        self.filtered_dx = 0.0
        self.filtered_dy = 0.0

        # Click and drag state
        self.pinch_start_time = None
        self.is_dragging = False
        self.last_left_click = 0.0
        self.last_right_click = 0.0
        self.last_fist_click = 0.0
        self.last_three_finger_click = 0.0
        self.fist_prev = False
        self.right_touch_prev = False

        # Scroll state
        self.scroll_active = False
        self.prev_scroll_x = None
        self.prev_scroll_y = None
        self.filtered_scroll_offset_x = 0.0
        self.filtered_scroll_offset_y = 0.0

    def reset_movement(self):
        """Reset movement-related states (e.g., when tracking pauses or is lost)."""
        if self.is_dragging:
            pyautogui.mouseUp(button="left")
            self.is_dragging = False

        self.prev_mid_x = None
        self.prev_mid_y = None
        self.filtered_dx = 0.0
        self.filtered_dy = 0.0
        self.pinch_start_time = None
        self.scroll_active = False
        self.prev_scroll_x = None
        self.prev_scroll_y = None
        self.filtered_scroll_offset_x = 0.0
        self.filtered_scroll_offset_y = 0.0
        self.right_touch_prev = False
        self.fist_prev = False


def process_scroll_motion(mid_x, mid_y, state: GestureState):
    """Apply shared vertical/horizontal scroll logic using GestureState.
    
    When scroll gesture activates, sets a fixed anchor point. Offsets are calculated
    from this anchor (not from previous position), so scrolling continues as long as
    hand is away from the anchor point.
    """
    if not state.scroll_active:
        # Activate scroll mode - set FIXED anchor point
        state.scroll_active = True
        state.prev_scroll_x = mid_x      # Fixed anchor X
        state.prev_scroll_y = mid_y      # Fixed anchor Y (will NOT be updated while scroll_active)
        state.filtered_scroll_offset_x = 0.0
        state.filtered_scroll_offset_y = 0.0
        if DEBUG_SCROLL:
            print(f"[SCROLL:START] anchor_y={mid_y:.4f}, multiplier={state.scroll_multiplier}")
    else:
        # Calculate offset from FIXED anchor point (prev_scroll_y stays constant while scrolling)
        raw_offset_y = mid_y - state.prev_scroll_y
        state.filtered_scroll_offset_y += (raw_offset_y - state.filtered_scroll_offset_y) * SCROLL_SMOOTH_ALPHA

        # Keep direction tied to the current side of the activation anchor.
        # This avoids temporary reverse scrolling when crossing the anchor.
        scroll_offset_y = state.filtered_scroll_offset_y
        if raw_offset_y != 0.0 and (scroll_offset_y * raw_offset_y) < 0.0:
            scroll_offset_y = raw_offset_y

        base_scroll_amount = offset_to_scroll_step(-scroll_offset_y, SCROLL_VERTICAL_GAIN)
        scroll_amount = int(round(base_scroll_amount * state.scroll_multiplier))
        if scroll_amount != 0:
            pyautogui.scroll(scroll_amount)
            if DEBUG_SCROLL:
                print(f"[SCROLL:V] raw_offset={raw_offset_y:.5f} filt={state.filtered_scroll_offset_y:.5f} base={base_scroll_amount} final={scroll_amount} multiplier={state.scroll_multiplier}")

        # Optional horizontal mode while scrolling: drift hand left/right from anchor.
        raw_offset_x = mid_x - state.prev_scroll_x
        state.filtered_scroll_offset_x += (raw_offset_x - state.filtered_scroll_offset_x) * SCROLL_SMOOTH_ALPHA
        hscroll_amount = offset_to_scroll_step(state.filtered_scroll_offset_x, SCROLL_HORIZONTAL_GAIN)
        if hscroll_amount != 0:
            apply_horizontal_scroll(hscroll_amount)
            if DEBUG_SCROLL:
                print(f"[SCROLL:H] raw_offset={raw_offset_x:.5f} amount={hscroll_amount}")

        # IMPORTANT: Do NOT update state.prev_scroll_x and state.prev_scroll_y!
        # They remain as the fixed anchor point until gesture deactivates.


def is_three_finger_touch(right_lm, hand_scale):
    thumb_tip = right_lm[THUMB_TIP]
    index_tip = right_lm[INDEX_TIP]
    middle_tip = right_lm[MIDDLE_TIP]
    d1 = dist(thumb_tip, index_tip)
    d2 = dist(index_tip, middle_tip)
    return d1 < THREE_FINGER_THRESHOLD * hand_scale and d2 < THREE_FINGER_THRESHOLD * hand_scale


def process_right_hand_gestures(
    right_lm,
    virtual_left,
    virtual_top,
    screen_w,
    screen_h,
    state: GestureState,
    now,
):
    """Process right hand gestures for cursor control, clicks, scroll, right-click."""
    thumb_tip = right_lm[THUMB_TIP]
    index_tip = right_lm[INDEX_TIP]
    middle_tip = right_lm[MIDDLE_TIP]
    hand_scale = max(dist(right_lm[WRIST], right_lm[MIDDLE_MCP]), 1e-6)

    # Cursor tracking uses the palm center so finger motion does not move the cursor.
    mid_x, mid_y = get_palm_center(right_lm)
    scroll_gesture = is_two_finger_scroll_gesture(right_lm)

    if state.prev_mid_x is None:
        state.prev_mid_x, state.prev_mid_y = mid_x, mid_y
    else:
        raw_dx = mid_x - state.prev_mid_x
        raw_dy = mid_y - state.prev_mid_y
        state.prev_mid_x, state.prev_mid_y = mid_x, mid_y

        if abs(raw_dx) < TRACKPAD_DEADZONE:
            raw_dx = 0.0
        if abs(raw_dy) < TRACKPAD_DEADZONE:
            raw_dy = 0.0

        state.filtered_dx += (raw_dx - state.filtered_dx) * TRACKPAD_SMOOTH_ALPHA
        state.filtered_dy += (raw_dy - state.filtered_dy) * TRACKPAD_SMOOTH_ALPHA

        if not scroll_gesture:
            state.cursor_x += state.filtered_dx * screen_w * TRACKPAD_SPEED_X * state.dpi
            state.cursor_y += state.filtered_dy * screen_h * TRACKPAD_SPEED_Y * state.dpi
            state.cursor_x = max(float(virtual_left), min(float(virtual_left + screen_w - 1), state.cursor_x))
            state.cursor_y = max(float(virtual_top), min(float(virtual_top + screen_h - 1), state.cursor_y))
            pyautogui.moveTo(state.cursor_x, state.cursor_y)

    # Left click on fist close.
    fist_now = is_fist_gesture(right_lm)
    if fist_now and not state.fist_prev:
        if (now - state.last_fist_click) > 0.3:
            send_mouse_click(button="left")
            state.last_fist_click = now
    state.fist_prev = fist_now

    # Left click/drag
    left_touch = fingertip_touch(right_lm, INDEX_TIP, THUMB_TIP, hand_scale, ratio=0.35)
    if left_touch:
        if state.pinch_start_time is None:
            state.pinch_start_time = now
        elif not state.is_dragging and (now - state.pinch_start_time) >= 0.5:
            send_mouse_button(button="left", is_down=True)
            state.is_dragging = True
    else:
        if state.pinch_start_time is not None:
            pinch_duration = now - state.pinch_start_time
            if state.is_dragging:
                send_mouse_button(button="left", is_down=False)
                state.is_dragging = False
            elif pinch_duration < 0.5 and (now - state.last_left_click) > 0.12:
                send_mouse_click(button="left")
                state.last_left_click = now
        state.pinch_start_time = None

    # Three finger left click
    three_finger_touch = is_three_finger_touch(right_lm, hand_scale)
    if three_finger_touch and (now - state.last_three_finger_click) > 0.3:
        send_mouse_click(button="left")
        state.last_three_finger_click = now

    # Scroll: show the two-finger sign to enter wheel mode.
    if scroll_gesture:
        if DEBUG_SCROLL:
            print(f"[SCROLL] Gesture detected at palm_y={mid_y:.4f}")
        process_scroll_motion(mid_x, mid_y, state)
    else:
        state.scroll_active = False
        state.prev_scroll_x = None
        state.prev_scroll_y = None
        state.filtered_scroll_offset_x = 0.0
        state.filtered_scroll_offset_y = 0.0

    # Right click: thumb + pinky finger touch
    right_touch = fingertip_touch(right_lm, PINKY_TIP, THUMB_TIP, hand_scale, ratio=0.38)
    if right_touch and not state.right_touch_prev and (now - state.last_right_click) > 0.5:
        send_mouse_click(button="right")
        state.last_right_click = now
    state.right_touch_prev = right_touch

