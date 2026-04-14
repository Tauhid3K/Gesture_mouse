import unittest
from collections import namedtuple
from gestures import offset_to_scroll_step, is_fist_gesture, GestureState

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

    def test_gesture_state_init(self):
        state = GestureState(100, 200, 1.0, 2.0)
        self.assertEqual(state.cursor_x, 100.0)
        self.assertEqual(state.cursor_y, 200.0)
        self.assertEqual(state.dpi, 1.0)
        self.assertEqual(state.scroll_multiplier, 2.0)
        self.assertFalse(state.is_dragging)

if __name__ == '__main__':
    unittest.main()
