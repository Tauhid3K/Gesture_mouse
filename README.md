# HandMouse

Hand gesture-based mouse control using MediaPipe hand tracking. Control your cursor, click, and scroll using hand gestures instead of a physical mouse.

## Features

- 🖐️ **Palm-Only Cursor Control** - Move your palm/hand base to move the cursor (finger motion is ignored).
- 🖱️ **Left Click** - Pinch index finger and thumb (quick pinch).
- 🖱️ **Right Click** - Touch thumb and pinky finger.
- 🖱️ **Drag & Drop** - Hold pinch for 0.24 seconds then move.
- 🔼 **Scroll** - Two-finger gesture (index & middle UP, ring & pinky DOWN) to scroll.
- 🔊 **Volume Control** - Thumbs Up (Volume Up) and Thumbs Down (Volume Down) gestures on **either hand**.
- ⌨️ **On-Screen Keyboard** - Close your fist with your left hand to open the Windows OSK.
- 🖼️ **Draggable Preview** - The camera preview window can be dragged and placed anywhere on your screen.
- 📍 **Smart Positioning** - Starts at the bottom-left by default, just above the taskbar.
- ⚙️ **Adjustable Settings** - Change DPI and scroll speed in real-time.
- 💾 **Persistent Settings** - Settings are saved automatically for your next session.
- 🎯 **Smooth & Stable** - Advanced filtering for natural movement and precise gesture detection.

## Installation

### Requirements
- Python 3.8 - 3.14
- Webcam
- Windows 10/11

### Setup

1. **Clone/Download the project**
   ```bash
   cd "path\to\handmouse"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   python -m pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python handmouse.py
   ```

The hand landmark model (`hand_landmarker.task`) will be automatically downloaded on first run.

## Building the Executable (.exe)

To create a standalone Windows executable:

1. **Install PyInstaller**
   ```bash
   python -m pip install pyinstaller
   ```

2. **Build the EXE**
   ```bash
   pyinstaller --noconsole --onefile --add-data "hand_landmarker.task;." --add-data ".venv/Lib/site-packages/mediapipe;mediapipe" --hidden-import "mediapipe.tasks.python.core.mediapipe_c_bindings" --name GestureMouse handmouse.py
   ```
   The final file will be in the `dist/` folder as `GestureMouse.exe`.

## Usage

### Gestures

| Gesture | Action | Notes |
|---------|--------|-------|
| **Palm Movement** | Move Cursor | Cursor follows palm base, ignores finger wiggling. |
| **Index + Thumb Pinch** | Left Click / Drag | Quick pinch = click. Hold > 0.24s = drag. |
| **Thumb + Pinky Touch** | Right Click | Brief touch triggers right click. |
| **Index + Middle UP** | Scroll Mode | Ring and pinky must be folded. Move hand Up/Down to scroll. |
| **Thumbs Up** 👍 | Volume Up | Available on both hands. Stops mouse movement while active. |
| **Thumbs Down** 👎 | Volume Down | Available on both hands. Stops mouse movement while active. |
| **Left Hand Fist** ✊ | Open Keyboard | Quickly opens Windows On-Screen Keyboard. |

### Camera Window Controls
- **Drag & Move**: Click anywhere on the camera feed (not on a button) and drag to move the window.
- **Topmost**: The window always stays on top of other applications.
- **Default Position**: Resets to bottom-left on every launch.

## Controls

| Button | Action |
|--------|--------|
| **START** | Enable hand tracking. |
| **PAUSE** | Disable tracking and release any active mouse buttons. |
| **SETTINGS** | Toggle the "Control Configuration" window. |
| **EXIT** | Exit the application safely. |

## Troubleshooting

### Volume gesture not working?
- Ensure your other 4 fingers are **tightly folded** into a fist.
- Make sure your thumb is pointing clearly **Up** or **Down**.
- The mouse will stop moving while the volume gesture is detected to prevent accidental clicks.

### Scrolling when I want Volume?
- Keep your index and middle fingers tucked in for volume. Scrolling requires them to be extended.

### EXE fails to start?
- Ensure `hand_landmarker.task` is in the same folder as the EXE if you didn't bundle it.
- If you get a "mediapipe" error, ensure you used the full build command including the `--add-data` for the site-packages folder.

---

**Version**: 1.1  
**Last Updated**: April 20, 2026
