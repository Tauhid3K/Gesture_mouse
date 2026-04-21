import sys
import os
from unittest.mock import MagicMock

os.environ['GLOG_minloglevel'] = '2'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

sys.modules["matplotlib"] = MagicMock()
sys.modules["matplotlib.pyplot"] = MagicMock()
sys.modules["matplotlib.style"] = MagicMock()

import ctypes
import json
import logging
import math
import subprocess
import time

import cv2
import pyautogui

from config import (
	DISPLAY_SCALE, DPI_MAX, DPI_MIN, HAND_MODEL_FILE, MOUSE_DPI,
	SCROLL_SPEED_MULTIPLIER_DEFAULT, SCROLL_SPEED_MULTIPLIER_MAX,
	SCROLL_SPEED_MULTIPLIER_MIN, WRIST, MIDDLE_MCP
)
from gestures import (
	GestureState, is_proper_fist, process_right_hand_gestures,
	is_select_gesture, is_thumb_pinky_touch, send_mouse_click,
	update_select_drag_state,
	is_thumbs_up, is_thumbs_down, is_any_finger_folded
)

from model import create_hand_landmarker, ensure_hand_model
from ui import (
	draw_status_and_dpi, draw_ui_buttons, handle_ui_requests,
	manage_settings_window, position_window, setup_ui
)
from utils import set_arrow_cursor, dist
from mediapipe.tasks.python.vision.core.image import Image, ImageFormat

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

def get_virtual_screen_bounds():
	user32 = ctypes.windll.user32
	return (int(user32.GetSystemMetrics(76)), int(user32.GetSystemMetrics(77)),
			int(user32.GetSystemMetrics(78)), int(user32.GetSystemMetrics(79)))

def load_user_settings(settings_path):
	settings = {"dpi": float(MOUSE_DPI), "scroll_multiplier": float(SCROLL_SPEED_MULTIPLIER_DEFAULT)}
	if not os.path.exists(settings_path): return settings
	try:
		with open(settings_path, "r", encoding="utf-8") as f:
			loaded = json.load(f)
		settings["dpi"] = float(loaded.get("dpi", settings["dpi"]))
		settings["scroll_multiplier"] = float(loaded.get("scroll_multiplier", settings["scroll_multiplier"]))
	except: pass
	settings["dpi"] = max(DPI_MIN, min(DPI_MAX, settings["dpi"]))
	settings["scroll_multiplier"] = max(SCROLL_SPEED_MULTIPLIER_MIN, min(SCROLL_SPEED_MULTIPLIER_MAX, settings["scroll_multiplier"]))
	return settings

def save_user_settings(settings_path, dpi, scroll_multiplier):
	settings = {"dpi": float(dpi), "scroll_multiplier": float(scroll_multiplier)}
	with open(settings_path, "w", encoding="utf-8") as f:
		json.dump(settings, f, indent=2)

def open_on_screen_keyboard():
	for cmd in ["osk.exe", "osk", r"C:\Windows\System32\osk.exe"]:
		try:
			if cmd.endswith(".exe") and hasattr(os, "startfile"):
				os.startfile(cmd)
			else:
				subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
			return
		except: pass

def is_compact_fist(lm):
	wrist, middle_mcp = lm[0], lm[9]
	scale = max(math.hypot(wrist.x - middle_mcp.x, wrist.y - middle_mcp.y), 1e-6)
	max_tip_dist = max(math.hypot(lm[i].x - wrist.x, lm[i].y - wrist.y) for i in (4, 8, 12, 16, 20))
	return max_tip_dist < (scale * 1.65)

def main():
	pyautogui.FAILSAFE, pyautogui.PAUSE = False, 0.0
	v_left, v_top, screen_w, screen_h = get_virtual_screen_bounds()
	primary_w, primary_h = pyautogui.size()

	model_path = os.path.join(os.path.dirname(__file__), HAND_MODEL_FILE)
	settings_path = os.path.join(os.path.dirname(__file__), "handmouse_settings.json")
	user_settings = load_user_settings(settings_path)
	ensure_hand_model(model_path)
	hand_landmarker = create_hand_landmarker(model_path)

	cap = cv2.VideoCapture(0)
	if not cap.isOpened():
		logger.error("Could not open webcam.")
		return

	window_name = "Hand Mouse Control"
	cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
	ui_state = {
		"tracking_enabled": True, 
		"request": None, 
		"buttons": {}, 
		"settings_open": False,
		"dragging": False,
		"drag_start_mouse_x": 0,
		"drag_start_mouse_y": 0,
		"drag_start_win_x": 0,
		"drag_start_win_y": 0,
		"window_x": None,
		"window_y": None,
		"moved_by_user": False
	}
	
	gesture_state = GestureState(pyautogui.position().x, pyautogui.position().y, user_settings["dpi"], user_settings["scroll_multiplier"])

	def on_mouse(event, x, y, flags, param):
		set_arrow_cursor()
		if event == cv2.EVENT_LBUTTONDOWN:
			# Check buttons first
			for action, (x1, y1, x2, y2) in ui_state["buttons"].items():
				if x1 <= x <= x2 and y1 <= y <= y2:
					ui_state["request"] = action
					return
			# If not a button, start dragging the window
			ui_state["dragging"] = True
			curr_mx, curr_my = pyautogui.position()
			ui_state["drag_start_mouse_x"] = curr_mx
			ui_state["drag_start_mouse_y"] = curr_my
			ui_state["drag_start_win_x"] = ui_state["window_x"] if ui_state["window_x"] is not None else 0
			ui_state["drag_start_win_y"] = ui_state["window_y"] if ui_state["window_y"] is not None else 0
		
		elif event == cv2.EVENT_LBUTTONUP:
			ui_state["dragging"] = False
		
		elif event == cv2.EVENT_MOUSEMOVE:
			if ui_state["dragging"]:
				curr_mx, curr_my = pyautogui.position()
				dx = curr_mx - ui_state["drag_start_mouse_x"]
				dy = curr_my - ui_state["drag_start_mouse_y"]
				ui_state["window_x"] = ui_state["drag_start_win_x"] + dx
				ui_state["window_y"] = ui_state["drag_start_win_y"] + dy
				ui_state["moved_by_user"] = True

	setup_ui(window_name, on_mouse)
	left_fist_prev, last_osk_open = False, 0.0

	try:
		while True:
			ok, frame = cap.read()
			if not ok: break
			
			request = ui_state["request"]
			if request == "close": break
			
			handle_ui_requests(ui_state, request, gesture_state)
			manage_settings_window(ui_state, "Mouse Settings", "DPI x100", "Scroll Speed", gesture_state)

			frame = cv2.flip(frame, 1)
			frame = cv2.resize(frame, None, fx=DISPLAY_SCALE, fy=DISPLAY_SCALE, interpolation=cv2.INTER_AREA)
			fh, fw = frame.shape[:2]

			if ui_state["tracking_enabled"]:
				rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
				mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
				result = hand_landmarker.detect_for_video(mp_image, int(time.time() * 1000))
			else: result = None

			# --- HAND DETECTION AND GESTURE PROCESSING ---
			# Identity which hand is Left and which is Right (result is from MediaPipe)
			right_lm, left_lm = None, None
			if result:
				for landmarks, handedness in zip(result.hand_landmarks, result.handedness):
					# Draw small circles on detected hand joints
					for p in landmarks: cv2.circle(frame, (int(p.x * fw), int(p.y * fh)), 2, (255, 0, 0), -1)
					if handedness[0].category_name == "Left": right_lm = landmarks # "Left" label = Right hand due to mirror
					else: left_lm = landmarks

			now = time.time()
			if ui_state["tracking_enabled"]:
				# Process the primary mouse movement using the Right Hand
				if right_lm: process_right_hand_gestures(right_lm, v_left, v_top, screen_w, screen_h, gesture_state, now)
				
				# Track separate flags for left-click, right-click, and "is a finger folded"
				l_select, r_select = False, False
				l_keep, r_keep = False, False
				l_right, r_right = False, False
				
				# --- LEFT HAND UTILITY LOGIC ---
				if left_lm:
					scale_l = max(dist(left_lm[WRIST], left_lm[MIDDLE_MCP]), 1e-6)
					l_select = is_select_gesture(left_lm, scale_l)
					l_keep = is_any_finger_folded(left_lm)
					l_right = is_thumb_pinky_touch(left_lm, scale_l)
					
					# If not trying to click, check for OSK and Volume controls
					if not l_select:
						# Open On-Screen Keyboard (OSK) if a tight fist is detected
						fist_now = is_proper_fist(left_lm)
						if fist_now and not left_fist_prev and (now - last_osk_open) > 1.5:
							open_on_screen_keyboard()
							last_osk_open = now
						left_fist_prev = fist_now

						# Handle Thumbs Up/Down for Volume
						if is_thumbs_up(left_lm):
							if (now - gesture_state.last_volume_step) > 0.3:
								pyautogui.press("volumeup")
								gesture_state.last_volume_step = now
						elif is_thumbs_down(left_lm):
							if (now - gesture_state.last_volume_step) > 0.3:
								pyautogui.press("volumedown")
								gesture_state.last_volume_step = now
					else:
						left_fist_prev = True # Suppress OSK while clicking
				else:
					left_fist_prev = False

				# --- RIGHT HAND CLICK LOGIC ---
				if right_lm:
					scale_r = max(dist(right_lm[WRIST], right_lm[MIDDLE_MCP]), 1e-6)
					r_select = is_select_gesture(right_lm, scale_r)
					r_keep = is_any_finger_folded(right_lm)
					r_right = is_thumb_pinky_touch(right_lm, scale_r)

					# Right hand can also control volume when not clicking
					if not r_select:
						if is_thumbs_up(right_lm):
							if (now - gesture_state.last_volume_step) > 0.3:
								pyautogui.press("volumeup")
								gesture_state.last_volume_step = now
						elif is_thumbs_down(right_lm):
							if (now - gesture_state.last_volume_step) > 0.3:
								pyautogui.press("volumedown")
								gesture_state.last_volume_step = now

				# --- COMBINE AND UPDATE STATE ---
				# If EITHER hand pinches, trigger the global select (click/drag) state
				select_touch = r_select or l_select
				keep_dragging = r_keep or l_keep
				r_click_touch = r_right or l_right

				# Update the sophisticated click-vs-drag state machine
				update_select_drag_state(select_touch, keep_dragging, gesture_state, now)

				# Perform the native right-click if the gesture just started
				if r_click_touch:
					if not gesture_state.right_touch_prev:
						send_mouse_click(button="right")
				gesture_state.right_touch_prev = r_click_touch

			else:
				# Ensure mouse buttons are released if tracking pauses while dragging
				gesture_state.reset_movement()

			# --- RENDER UI AND UPDATE WINDOW ---
			draw_ui_buttons(frame, ui_state, 32, 88, 8, 10, 10)
			draw_status_and_dpi(frame, ui_state, gesture_state.dpi, 32, 10, 10)
			position_window(primary_w, primary_h, fw, fh, window_name, 10, ui_state)
			set_arrow_cursor()
			cv2.imshow(window_name, frame)
			if cv2.waitKey(1) & 0xFF == ord("q"): break
	except KeyboardInterrupt: logger.info("Interrupted by user.")
	finally:
		try: save_user_settings(settings_path, gesture_state.dpi, gesture_state.scroll_multiplier)
		except: pass
		if 'gesture_state' in locals() and gesture_state.is_dragging: pyautogui.mouseUp(button="left")
		cap.release()
		cv2.destroyAllWindows()
		try: hand_landmarker.close()
		except: pass

if __name__ == "__main__": main()
