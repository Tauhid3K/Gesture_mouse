import unittest
from collections import namedtuple
from unittest.mock import patch

from gestures import (
    GestureState,
    is_fist_gesture,
    is_index_thumb_pinch,
    is_select_gesture,
    offset_to_scroll_step,
    update_select_drag_state,
    SELECT_HOLD_SECONDS,
    SELECT_RELEASE_GRACE_SECONDS,
)

# Mock landmark for testing
Landmark = namedtuple('Landmark', ['x', 'y'])

class TestGestureLogic(unittest.TestCase):
    
    def test_offset_to_scroll_step(self):
        # Test deadzone
        self.assertEqual(offset_to_scroll_step(0.001, 1000, deadzone=0.003), 0)
        # Test positive scroll
        self.assertGreater(offset_to_scroll_step(0.01, 1000, deadzone=0.003), 0)
        # Test negative scroll
        self.assertLess(offset_to_scroll_step(-0.01, 1000, deadzone=0.003), 0)

    def test_is_fist_gesture(self):
        # Mock a closed fist (tips below PIPs)
        # In MediaPipe, Y increases downwards, so Tip.y > Pip.y means Tip is lower (folded)
        fist_landmarks = {
            0: Landmark(0, 0.7),  # WRIST
            8: Landmark(0, 0.6),  # INDEX_TIP
            6: Landmark(0, 0.5),  # INDEX_PIP
            12: Landmark(0, 0.6), # MIDDLE_TIP
            10: Landmark(0, 0.5), # MIDDLE_PIP
            16: Landmark(0, 0.6), # RING_TIP
            14: Landmark(0, 0.5), # RING_PIP
            20: Landmark(0, 0.6), # PINKY_TIP
            18: Landmark(0, 0.5), # PINKY_PIP
        }
        self.assertTrue(is_fist_gesture(fist_landmarks))

        # Mock an open hand (tips above PIPs)
        open_landmarks = {
            0: Landmark(0, 0.7),  # WRIST
            8: Landmark(0, 0.4),  # INDEX_TIP
            6: Landmark(0, 0.5),  # INDEX_PIP
            12: Landmark(0, 0.4), # MIDDLE_TIP
            10: Landmark(0, 0.5), # MIDDLE_PIP
            16: Landmark(0, 0.4), # RING_TIP
            14: Landmark(0, 0.5), # RING_PIP
            20: Landmark(0, 0.4), # PINKY_TIP
            18: Landmark(0, 0.5), # PINKY_PIP
        }
        self.assertFalse(is_fist_gesture(open_landmarks))

    def test_select_gesture_prefers_thumb_index_pinch(self):
        pinch_landmarks = {
            4: Landmark(0.40, 0.50),
            8: Landmark(0.43, 0.52),
            9: Landmark(0.10, 0.50),
        }
        self.assertTrue(is_index_thumb_pinch(pinch_landmarks, 1.0))
        self.assertTrue(is_select_gesture(pinch_landmarks, 1.0))

    def test_update_select_drag_state_click_then_drag(self):
        state = GestureState(100, 200, 1.0, 2.0)
        with patch("gestures.pyautogui.mouseDown") as mouse_down, \
             patch("gestures.pyautogui.mouseUp") as mouse_up, \
             patch("gestures.send_mouse_click") as send_click:
            update_select_drag_state(True, state, 10.0)
            self.assertEqual(state.pinch_start_time, 10.0)
            self.assertFalse(state.is_dragging)

            update_select_drag_state(True, state, 10.0 + SELECT_HOLD_SECONDS + 0.01)
            mouse_down.assert_called_once_with(button="left")
            self.assertTrue(state.is_dragging)

            update_select_drag_state(False, state, 10.0 + SELECT_HOLD_SECONDS + 0.01 + (SELECT_RELEASE_GRACE_SECONDS / 2))
            mouse_up.assert_not_called()
            self.assertTrue(state.is_dragging)

            update_select_drag_state(False, state, 10.0 + SELECT_HOLD_SECONDS + SELECT_RELEASE_GRACE_SECONDS + 0.2)
            mouse_up.assert_called_once_with(button="left")
            send_click.assert_not_called()
            self.assertFalse(state.is_dragging)

    def test_update_select_drag_state_quick_select_clicks(self):
        state = GestureState(100, 200, 1.0, 2.0)
        with patch("gestures.send_mouse_click") as send_click:
            update_select_drag_state(True, state, 20.0)
            update_select_drag_state(False, state, 20.0 + SELECT_RELEASE_GRACE_SECONDS + 0.02)
            send_click.assert_called_once_with(button="left")
            self.assertFalse(state.is_dragging)

    def test_gesture_state_init(self):
        state = GestureState(100, 200, 1.0, 2.0)
        self.assertEqual(state.cursor_x, 100.0)
        self.assertEqual(state.cursor_y, 200.0)
        self.assertEqual(state.dpi, 1.0)
        self.assertEqual(state.scroll_multiplier, 2.0)
        self.assertFalse(state.is_dragging)

if __name__ == '__main__':
    unittest.main()
