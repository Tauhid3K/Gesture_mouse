# Utility functions for hand mouse control

import ctypes
from config import ARROW_CURSOR  # Global cursor handle

def set_arrow_cursor():
    """Set Windows cursor to arrow for UI buttons."""
    if ARROW_CURSOR is None:
        return
    try:
        ctypes.windll.user32.SetCursor(ARROW_CURSOR)
    except Exception:
        pass

import math

def dist(lm1, lm2):
    """Calculate Euclidean distance between two landmarks."""
    return math.hypot(lm1.x - lm2.x, lm1.y - lm2.y)

def fingertip_touch(lm, tip_a, tip_b, scale, ratio=0.35):
    """Check if two fingertips are touching based on distance threshold."""
    return dist(lm[tip_a], lm[tip_b]) < (scale * ratio)
