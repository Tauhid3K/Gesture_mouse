import ctypes
import json
import math
import os
import subprocess
import time

import cv2
import pyautogui

from config import (
	DISPLAY_SCALE,
	DPI_MAX,
	DPI_MIN,
	HAND_MODEL_FILE,
	MOUSE_DPI,
	SCROLL_SPEED_MULTIPLIER_DEFAULT,
	SCROLL_SPEED_MULTIPLIER_MAX,
	SCROLL_SPEED_MULTIPLIER_MIN,
	SCROLL_VERTICAL_GAIN,
	TRACKPAD_DEADZONE,
	TRACKPAD_SMOOTH_ALPHA,
	TRACKPAD_SPEED_X,
	TRACKPAD_SPEED_Y,
	UI_BUTTON_H,
	UI_BUTTON_W,
	UI_GAP,
	UI_MARGIN,
)
from gestures import is_fist_gesture, process_right_hand_gestures
from model import create_hand_landmarker, ensure_hand_model
from ui import (
	draw_status_and_dpi,
	draw_ui_buttons,
	handle_ui_requests,
	manage_settings_window,
	position_window,
	setup_ui,
)
from utils import set_arrow_cursor
from mediapipe.tasks.python.vision.core.image import Image, ImageFormat


def get_virtual_screen_bounds():
	"""Return the full desktop bounds so the cursor can move across all monitors."""
	user32 = ctypes.windll.user32
	virtual_left = int(user32.GetSystemMetrics(76))
	virtual_top = int(user32.GetSystemMetrics(77))
	virtual_width = int(user32.GetSystemMetrics(78))
	virtual_height = int(user32.GetSystemMetrics(79))
	return virtual_left, virtual_top, virtual_width, virtual_height


def load_user_settings(settings_path):
	"""Load persisted settings from disk and return safe defaults on failure."""
	settings = {
		"dpi": float(MOUSE_DPI),
		"scroll_multiplier": float(SCROLL_SPEED_MULTIPLIER_DEFAULT),
	}

	if not os.path.exists(settings_path):
		return settings

	try:
		with open(settings_path, "r", encoding="utf-8") as settings_file:
			loaded = json.load(settings_file)
		settings["dpi"] = float(loaded.get("dpi", settings["dpi"]))
		settings["scroll_multiplier"] = float(
			loaded.get("scroll_multiplier", settings["scroll_multiplier"])
		)
	except (OSError, ValueError, TypeError, json.JSONDecodeError):
		pass

	settings["dpi"] = max(DPI_MIN, min(DPI_MAX, settings["dpi"]))
	settings["scroll_multiplier"] = max(
		SCROLL_SPEED_MULTIPLIER_MIN,
		min(SCROLL_SPEED_MULTIPLIER_MAX, settings["scroll_multiplier"]),
	)
	return settings


def save_user_settings(settings_path, dpi, scroll_multiplier):
	"""Persist user settings to disk for the next launch."""
	settings = {
		"dpi": float(dpi),
		"scroll_multiplier": float(scroll_multiplier),
	}
	with open(settings_path, "w", encoding="utf-8") as settings_file:
		json.dump(settings, settings_file, indent=2)


def open_on_screen_keyboard():
	"""Launch Windows on-screen keyboard."""
	try:
		os.startfile("osk.exe")  # type: ignore[attr-defined]
		return
	except OSError:
		pass

	try:
		subprocess.Popen(["osk"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		return
	except OSError:
		pass

	# Fallback absolute path for environments where PATH lookup fails.
	try:
		subprocess.Popen(
			[r"C:\Windows\System32\osk.exe"],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
		)
	except OSError:
		pass


def is_compact_fist(hand_landmarks):
	"""Fallback closed-hand check for cases where strict fingertip-vs-PIP fails."""
	wrist = hand_landmarks[0]
	middle_mcp = hand_landmarks[9]
	hand_scale = max(math.hypot(wrist.x - middle_mcp.x, wrist.y - middle_mcp.y), 1e-6)

	# A closed hand keeps all fingertip points relatively close to the wrist.
	max_tip_dist = 0.0
	for tip_idx in (4, 8, 12, 16, 20):
		tip = hand_landmarks[tip_idx]
		d = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
		if d > max_tip_dist:
			max_tip_dist = d

	return max_tip_dist < (hand_scale * 1.65)


def main():
	# Disable PyAutoGUI safety delays so cursor movement feels immediate.
	pyautogui.FAILSAFE = False
	pyautogui.PAUSE = 0.0

	# Read the full virtual desktop size for cursor travel across monitors.
	virtual_left, virtual_top, screen_w, screen_h = get_virtual_screen_bounds()

	# Keep the camera preview pinned to the laptop/primary display.
	primary_screen_w, primary_screen_h = pyautogui.size()

	# Resolve and load the MediaPipe hand landmark model before starting capture.
	model_path = os.path.join(os.path.dirname(__file__), HAND_MODEL_FILE)
	settings_path = os.path.join(os.path.dirname(__file__), "handmouse_settings.json")
	user_settings = load_user_settings(settings_path)
	ensure_hand_model(model_path)
	hand_landmarker = create_hand_landmarker(model_path)

	# Open the default webcam that provides frames for hand tracking.
	cap = cv2.VideoCapture(0)
	if not cap.isOpened():
		print("Could not open webcam.")
		return

	window_name = "Hand Mouse Control"
	window_margin = 10
	cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

	# Shared UI state used by button callbacks and the main loop.
	ui_state = {
		"tracking_enabled": True,
		"request": None,
		"buttons": {},
		"settings_open": False,
	}
	settings_window_name = "Mouse Settings"
	dpi_trackbar_name = "DPI x100"
	scroll_trackbar_name = "Scroll Speed"

	# Handle clicks on custom OpenCV-drawn buttons.
	def on_mouse(event, x, y, flags, param):
		_ = (flags, param)
		set_arrow_cursor()
		if event != cv2.EVENT_LBUTTONDOWN:
			return
		for action, (x1, y1, x2, y2) in ui_state["buttons"].items():
			if x1 <= x <= x2 and y1 <= y <= y2:
				ui_state["request"] = action
				return

	setup_ui(window_name, on_mouse)

	# Runtime control variables for cursor smoothing, gesture timing, and click state.
	cursor_pos = pyautogui.position()
	cursor_x, cursor_y = float(cursor_pos.x), float(cursor_pos.y)
	current_dpi = float(user_settings["dpi"])
	current_speed_x = float(TRACKPAD_SPEED_X)
	current_speed_y = float(TRACKPAD_SPEED_Y)
	current_deadzone = float(TRACKPAD_DEADZONE)
	current_smooth = float(TRACKPAD_SMOOTH_ALPHA)
	current_scroll_multiplier = float(user_settings["scroll_multiplier"])
	prev_mid_x = None
	prev_mid_y = None
	filtered_dx = 0.0
	filtered_dy = 0.0

	pinch_start_time = None
	is_dragging = False
	last_left_click = 0.0

	scroll_active = False
	prev_scroll_x = None
	prev_scroll_y = None

	right_touch_prev = False
	last_right_click = 0.0
	last_fist_click = 0.0
	last_three_finger_click = 0.0
	fist_prev = False
	left_fist_prev = False
	last_osk_open = 0.0
	filtered_scroll_offset_x = 0.0
	filtered_scroll_offset_y = 0.0

	try:
		# Main application loop: read webcam frames, detect gestures, and update the UI.
		while True:
			ok, frame = cap.read()
			if not ok:
				break

			request = ui_state["request"]
			if request == "close":
				ui_state["request"] = None
				break

			# Apply button-triggered UI actions such as pause/resume, settings, or exit.
			(
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
				fist_prev,
			) = handle_ui_requests(
				ui_state,
				request,
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
				fist_prev,
			)

			# Keep settings window state in sync for both open and close transitions.
			current_dpi, current_scroll_multiplier = manage_settings_window(
				ui_state,
				settings_window_name,
				dpi_trackbar_name,
				scroll_trackbar_name,
				current_dpi,
				current_scroll_multiplier,
			)

			# Mirror the preview for natural interaction and scale it for display.
			frame = cv2.flip(frame, 1)
			frame = cv2.resize(
				frame,
				None,
				fx=DISPLAY_SCALE,
				fy=DISPLAY_SCALE,
				interpolation=cv2.INTER_AREA,
			)
			frame_h, frame_w = frame.shape[:2]

			# Run hand detection only when tracking is enabled.
			if ui_state["tracking_enabled"]:
				rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
				mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
				timestamp_ms = int(time.time() * 1000)
				result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)
			else:
				result = None

			# Store mirrored-hand landmarks: detected Left->user right, detected Right->user left.
			right_lm = None
			left_lm = None
			if result is not None:
				for hand_landmarks, handedness in zip(result.hand_landmarks, result.handedness):
					label = handedness[0].category_name

					for point in hand_landmarks:
						cv2.circle(
							frame,
							(int(point.x * frame_w), int(point.y * frame_h)),
							2,
							(80, 180, 255),
							-1,
						)

					# Frame is mirrored for natural control, so handedness appears swapped.
					if label == "Left":
						right_lm = hand_landmarks
					elif label == "Right":
						left_lm = hand_landmarks

			now = time.time()

			# Left-hand fist opens the on-screen keyboard once per gesture.
			if ui_state["tracking_enabled"] and left_lm is not None:
				left_fist_now = is_fist_gesture(left_lm) or is_compact_fist(left_lm)
				if left_fist_now and not left_fist_prev and (now - last_osk_open) > 1.0:
					open_on_screen_keyboard()
					last_osk_open = now
				left_fist_prev = left_fist_now
			else:
				left_fist_prev = False

			# Convert the detected hand landmarks into cursor movement and mouse actions.
			if ui_state["tracking_enabled"] and right_lm is not None:
				(
					cursor_x,
					cursor_y,
					prev_mid_x,
					prev_mid_y,
					filtered_dx,
					filtered_dy,
					pinch_start_time,
					is_dragging,
					last_left_click,
					scroll_active,
					prev_scroll_x,
					prev_scroll_y,
					right_touch_prev,
					last_right_click,
					last_fist_click,
					last_three_finger_click,
					fist_prev,
					filtered_scroll_offset_x,
					filtered_scroll_offset_y,
				) = process_right_hand_gestures(
					right_lm,
					virtual_left,
					virtual_top,
					screen_w,
					screen_h,
					cursor_x,
					cursor_y,
					current_dpi,
					current_speed_x,
					current_speed_y,
					current_deadzone,
					current_smooth,
					current_scroll_multiplier,
					prev_mid_x,
					prev_mid_y,
					filtered_dx,
					filtered_dy,
					pinch_start_time,
					is_dragging,
					last_left_click,
					scroll_active,
					prev_scroll_x,
					prev_scroll_y,
					right_touch_prev,
					last_right_click,
					last_fist_click,
					last_three_finger_click,
					fist_prev,
					now,
					filtered_scroll_offset_x,
					filtered_scroll_offset_y,
				)
			else:
				# If tracking is unavailable, reset gesture state and release any active drag.
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
				last_fist_click = 0.0
				last_three_finger_click = 0.0
				fist_prev = False

			# Draw the overlay controls and current tracking status on top of the preview.
			button_h = UI_BUTTON_H
			button_w = UI_BUTTON_W
			gap = UI_GAP
			base_x = UI_MARGIN
			base_y = UI_MARGIN
			draw_ui_buttons(frame, ui_state, button_h, button_w, gap, base_x, base_y)
			draw_status_and_dpi(frame, ui_state, current_dpi, button_h, base_x, base_y)

			position_window(
				primary_screen_w,
				primary_screen_h,
				frame_w,
				frame_h,
				window_name,
				window_margin,
			)

			set_arrow_cursor()
			cv2.imshow(window_name, frame)

			# Allow quick exit from the keyboard in addition to the on-screen close button.
			if cv2.waitKey(1) & 0xFF == ord("q"):
				break
	except KeyboardInterrupt:
		print("Hand mouse interrupted by user. Shutting down gracefully...")


	finally:
		try:
			save_user_settings(settings_path, current_dpi, current_scroll_multiplier)
		except OSError as exc:
			print(f"Warning: could not save settings: {exc}")

		# Cleanup: mouse, OpenCV windows, MediaPipe, settings
		if 'is_dragging' in locals() and is_dragging:
			pyautogui.mouseUp(button="left")
		cap.release()
		cv2.destroyAllWindows()
		try:
			if 'settings_window_name' in locals():
				cv2.destroyWindow(settings_window_name)
		except cv2.error:
			pass
		try:
			hand_landmarker.close()
		except:
			pass  # Ignore close errors on shutdown


if __name__ == "__main__":
	main()
