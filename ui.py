# UI management for hand mouse control window and settings

import ctypes

import cv2
import numpy as np
import pyautogui
from config import (
    DPI_MIN,
    DPI_MAX,
    SCROLL_SPEED_MULTIPLIER_MIN,
    SCROLL_SPEED_MULTIPLIER_MAX,
    SETTINGS_WINDOW_W,
    SETTINGS_WINDOW_H,
    WINDOW_BOTTOM_OFFSET,
)

def setup_ui(window_name, on_mouse_callback):
    """Setup main window mouse callback."""
    cv2.setMouseCallback(window_name, on_mouse_callback)

def handle_ui_requests(ui_state, request, is_dragging, prev_mid_x, prev_mid_y, filtered_dx, filtered_dy, pinch_start_time, scroll_active, prev_scroll_x, prev_scroll_y, filtered_scroll_offset_x, filtered_scroll_offset_y, right_touch_prev, last_left_click, last_fist_click, last_three_finger_click, fist_prev):
    """Handle UI button requests (start/pause/settings/close). Reset states on pause."""
    if request == "start":
        ui_state["tracking_enabled"] = True
    elif request == "pause":
        ui_state["tracking_enabled"] = False
        if is_dragging:
            pyautogui.mouseUp(button="left")
            is_dragging = False
        prev_mid_x = None
        prev_mid_y = None
        filtered_dx = 0.0
        filtered_dy = 0.0
        pinch_start_time = None
        scroll_active = False
        prev_scroll_x = None
        prev_scroll_y = None
        filtered_scroll_offset_x = 0.0
        filtered_scroll_offset_y = 0.0
        right_touch_prev = False
        # Preserve click states on pause
    elif request == "settings":
        ui_state["settings_open"] = not ui_state["settings_open"]
    elif request == "close":
        # Will break loop in main
        pass
    ui_state["request"] = None
    return (
        is_dragging,
        prev_mid_x,
        prev_mid_y,
        filtered_dx,
        filtered_dy,
        pinch_start_time,
        scroll_active,
        prev_scroll_x,
        prev_scroll_y,
        filtered_scroll_offset_x,
        filtered_scroll_offset_y,
        right_touch_prev,
        last_left_click,
        last_fist_click,
        last_three_finger_click,
        fist_prev
    )

def draw_ui_buttons(frame, ui_state, button_h, button_w, gap, base_x, base_y):
    """Draw UI buttons and update button rects in ui_state."""
    ui_state["buttons"] = {}
    button_defs = [
        ("start", "START", (50, 170, 60)),
        ("pause", "PAUSE", (40, 150, 220)),
        ("close", "CLOSE", (40, 40, 220)),
        ("settings", "", (70, 70, 70)),
    ]
    for idx, (action, label, color) in enumerate(button_defs):
        x1 = base_x + idx * (button_w + gap)
        y1 = base_y
        x2 = x1 + button_w
        y2 = y1 + button_h
        ui_state["buttons"][action] = (x1, y1, x2, y2)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (240, 240, 240), 1)
        cv2.putText(
            frame,
            label,
            (x1 + 16, y1 + 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )
        if action == "settings":
            # Settings icon (sliders)
            cy = y1 + 9
            for yoff, knob_x in ((0, x1 + 26), (8, x1 + 44), (16, x1 + 34)):
                line_y = cy + yoff
                cv2.line(frame, (x1 + 14, line_y), (x2 - 14, line_y), (230, 230, 230), 2)
                cv2.circle(frame, (knob_x, line_y), 3, (230, 230, 230), -1)

def draw_status_and_dpi(frame, ui_state, current_dpi, button_h, base_x, base_y):
    """Draw status text and DPI display."""
    status_text = "RUNNING" if ui_state["tracking_enabled"] else "PAUSED"
    status_color = (60, 200, 60) if ui_state["tracking_enabled"] else (40, 180, 255)
    cv2.putText(
        frame,
        status_text,
        (base_x, base_y + button_h + 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        status_color,
        2,
    )
    cv2.putText(
        frame,
        f"DPI {current_dpi:.2f}",
        (base_x + 200, base_y + button_h + 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (220, 220, 220),
        2,
    )

def manage_settings_window(ui_state, settings_window_name, dpi_trackbar_name, scroll_trackbar_name, current_dpi, current_scroll_multiplier):
    """Manage settings window sliders and live updates for DPI and scroll multiplier."""
    settings_ui_created = ui_state.get('settings_ui_created', False)
    if ui_state["settings_open"]:
        if settings_ui_created:
            try:
                if cv2.getWindowProperty(settings_window_name, cv2.WND_PROP_VISIBLE) < 1:
                    settings_ui_created = False
                    ui_state["settings_open"] = False
            except cv2.error:
                settings_ui_created = False
                ui_state["settings_open"] = False

        if not settings_ui_created:
            try:
                cv2.namedWindow(settings_window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(settings_window_name, SETTINGS_WINDOW_W, SETTINGS_WINDOW_H)
                cv2.createTrackbar(
                    dpi_trackbar_name,
                    settings_window_name,
                    int(max(DPI_MIN, min(DPI_MAX, current_dpi)) * 100),
                    int(DPI_MAX * 100),
                    lambda value: None,
                )
                cv2.createTrackbar(
                    scroll_trackbar_name,
                    settings_window_name,
                    int(max(SCROLL_SPEED_MULTIPLIER_MIN, min(SCROLL_SPEED_MULTIPLIER_MAX, current_scroll_multiplier))),
                    int(SCROLL_SPEED_MULTIPLIER_MAX),
                    lambda value: None,
                )
                settings_ui_created = True
            except cv2.error:
                ui_state["settings_open"] = False
                settings_ui_created = False

        if settings_ui_created:
            try:
                dpi_from_slider = cv2.getTrackbarPos(dpi_trackbar_name, settings_window_name) / 100.0
                current_dpi = max(DPI_MIN, min(DPI_MAX, dpi_from_slider))
                scroll_from_slider = cv2.getTrackbarPos(scroll_trackbar_name, settings_window_name)
                current_scroll_multiplier = max(
                    SCROLL_SPEED_MULTIPLIER_MIN,
                    min(SCROLL_SPEED_MULTIPLIER_MAX, float(scroll_from_slider)),
                )
            except cv2.error:
                settings_ui_created = False
                ui_state["settings_open"] = False

        if settings_ui_created:
            settings_canvas = np.zeros((SETTINGS_WINDOW_H, SETTINGS_WINDOW_W, 3), dtype=np.uint8)
            cv2.putText(
                settings_canvas,
                "Mouse Settings",
                (14, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (230, 230, 230),
                2,
            )
            cv2.putText(
                settings_canvas,
                f"DPI: {current_dpi:.2f}",
                (14, 72),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (80, 220, 80),
                2,
            )
            cv2.putText(
                settings_canvas,
                f"Scroll Speed: {int(current_scroll_multiplier)}x",
                (14, 112),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                (80, 220, 80),
                2,
            )
            cv2.imshow(settings_window_name, settings_canvas)
        ui_state['settings_ui_created'] = settings_ui_created
    else:
        if ui_state.get('settings_ui_created', False):
            try:
                cv2.destroyWindow(settings_window_name)
            except cv2.error:
                pass
            ui_state['settings_ui_created'] = False
    return current_dpi, current_scroll_multiplier

def position_window(screen_w, screen_h, frame_w, frame_h, window_name, window_margin):
    """Position the preview at the bottom-right corner of the primary display, slightly above the taskbar."""
    window_x = max(0, screen_w - frame_w - window_margin)
    window_y = max(0, screen_h - frame_h - window_margin - WINDOW_BOTTOM_OFFSET)

    # Native Win32 topmost positioning is more reliable than OpenCV's window flag alone.
    hwnd = ctypes.windll.user32.FindWindowW(None, window_name)
    if hwnd:
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        HWND_TOPMOST = -1
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            int(window_x),
            int(window_y),
            0,
            0,
            SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    try:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    except cv2.error:
        pass
    try:
        cv2.moveWindow(window_name, window_x, window_y)
    except cv2.error:
        pass
