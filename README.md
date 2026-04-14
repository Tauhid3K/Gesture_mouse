# HandMouse

Hand gesture-based mouse control using MediaPipe hand tracking. Control your cursor, click, and scroll using hand gestures instead of a physical mouse.

## Features

- 🖱️ **Cursor Control** - Move your hand to move the cursor
- 🖱️ **Left Click** - Pinch index finger and thumb
- 🖱️ **Right Click** - Touch thumb and pinky finger
- 🖱️ **Drag & Drop** - Hold pinch for 0.5 seconds then move
- 🔼 **Scroll** - Two-finger gesture (index & middle UP, ring & pinky DOWN) to scroll
- ⚙️ **Adjustable Settings** - Change DPI and scroll speed in real-time
- 💾 **Persistent Settings** - Settings are saved for next session
- 📱 **Multi-Monitor Support** - Works across all connected displays
- 🎯 **Smooth Tracking** - Exponential smoothing for natural cursor movement

## Installation

### Requirements
- Python 3.8+
- Webcam
- Windows (tested on Windows 10/11)

### Setup

1. **Clone/Download the project**
   ```bash
   cd "path\to\handmouse"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python handmouse.py
   ```

The hand landmark model (`hand_landmarker.task`) will be automatically downloaded on first run.

## Testing

To verify the gesture detection and state management logic, you can run the included unit tests:

```bash
python test_gestures.py
```

## Usage

### Starting the App

```bash
python handmouse.py
```

A window will open showing your webcam feed with:
- Hand landmarks overlaid
- Control buttons (Pause, Settings, Close)
- Current DPI and settings display

### Gestures

| Gesture | Action | Notes |
|---------|--------|-------|
| **Palm Movement** | Move Cursor | Palm center tracks smoothly |
| **Index + Thumb Pinch** (hold <0.5s) | Left Click | Quick pinch = click |
| **Index + Thumb Pinch** (hold >0.5s) | Drag & Drop | Hold longer to drag, move hand while pinching |
| **Thumb + Pinky Touch** | Right Click | Brief touch triggers right click |
| **Left Hand Fist** | Open On-Screen Keyboard | Left hand only |
| **Three Finger Touch** | Left Click | Index + Middle + Thumb together |
| **Two-Finger Scroll Gesture** | Scroll | Index & Middle UP, Ring & Pinky DOWN |

### Scroll Gesture Detail

The scroll gesture activates when:
- Index finger points UP
- Middle finger points UP
- Ring finger is DOWN (folded)
- Pinky finger is DOWN (folded)

Once activated:
- Move hand **UP** → Scroll UP
- Move hand **DOWN** → Scroll DOWN
- Return to activation point → Stop scrolling

## Settings

Click the **"Settings"** button to open the Mouse Settings window.

### Adjustable Parameters

| Setting | Range | Default | Purpose |
|---------|-------|---------|---------|
| **DPI** | 0.3x - 3.0x | 1.0x | Cursor movement sensitivity |
| **Scroll Speed** | 1x - 6x | 1x | Scroll wheel sensitivity multiplier |

Settings are automatically saved to `handmouse_settings.json`.

## Controls

| Button | Action |
|--------|--------|
| **Track** / **Pause** | Enable/disable hand tracking |
| **Settings** | Open mouse settings window |
| **Close** | Exit application |
| **Close (Settings)** | Close settings without saving |

## File Structure

```
handmouse/
├── handmouse.py              # Main application (logging enabled)
├── config.py                 # Configuration constants
├── gestures.py               # GestureState & detection logic
├── model.py                  # Hand tracking model management
├── ui.py                     # UI and settings window
├── utils.py                  # Utility functions
├── requirements.txt          # Project dependencies
├── test_gestures.py          # Unit tests for gesture logic
├── hand_landmarker.task      # MediaPipe hand model (auto-downloaded)
├── handmouse_settings.json   # User settings (auto-created)
└── README.md                 # This file
```

## Configuration

Edit `config.py` to adjust behavior:

```python
# Cursor movement sensitivity
TRACKPAD_SPEED_X = 2.6
TRACKPAD_SPEED_Y = 2.6
TRACKPAD_DEADZONE = 0.0018      # Minimum movement to register
TRACKPAD_SMOOTH_ALPHA = 0.45    # Smoothing (0-1, higher = more smooth)

# Scroll settings
SCROLL_DEADZONE = 0.003         # Minimum hand movement to trigger scroll
SCROLL_VERTICAL_GAIN = 800      # Sensitivity (higher = more scroll)
SCROLL_SMOOTH_ALPHA = 0.30      # Scroll smoothing

# Display settings
DISPLAY_SCALE = 0.62            # Preview window scale
```

## Troubleshooting

### Cursor jumps around
- Reduce `TRACKPAD_DEADZONE` for more responsiveness
- Increase `TRACKPAD_SMOOTH_ALPHA` for smoother movement (max 0.99)

### Scroll not working
- Make sure you have the correct gesture shape (index & middle UP, ring & pinky DOWN)
- Try making bigger hand movements
- Reduce `SCROLL_DEADZONE` in config.py

### Gesture not detected
- Ensure good lighting
- Move closer to camera
- Make gestures more pronounced
- Try different hand angles

### Application runs slow
- Close other heavy applications
- Reduce `DISPLAY_SCALE` in config.py
- Check webcam FPS is adequate

### Webcam won't open
- Check if another app is using the camera
- Try restarting the application
- Verify camera works in other applications (Photo app, etc.)

## System Requirements

- **Processor**: Intel Core i5 or equivalent (or better)
- **RAM**: 4GB minimum (8GB+ recommended)
- **GPU**: Optional (CPU works fine, GPU speeds up hand detection)
- **Webcam**: Standard USB webcam (or laptop built-in camera)
- **OS**: Windows 10/11
- **Python**: 3.8 or higher

## Performance Notes

- Typical latency: 50-150ms (human reaction time is ~200ms)
- Smoothing helps reduce jitter from camera/detection noise
- Higher DPI settings increase responsiveness but may feel jittery
- Scroll smoothing prevents accidental multiple scrolls from small hand shakes

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **T** | Toggle tracking (pause/resume) |
| **S** | Open/close settings |
| **Q** (in gesture test) | Quit test window |

## Tips for Best Results

1. **Lighting**: Use bright, even lighting. Avoid backlighting.
2. **Camera Position**: Position camera at chest height, slightly below eye level.
3. **Hand Distance**: Keep hand 30-60cm from camera for best detection.
4. **Clothing**: Avoid clothing colors similar to skin tone.
5. **Calibration**: Move around to let the model calibrate to your lighting.
6. **Breaks**: Take breaks to avoid fatigue from holding hand up.

## Known Limitations

- Requires good webcam and lighting
- Small delays (50-150ms) due to hand detection processing
- Cannot detect hands if completely obscured
- Works best with right hand (app can use left hand as secondary)
- Windows only (uses pyautogui and Windows APIs)

## Contributing

Feel free to modify and improve this project for your needs.

## License

This project uses:
- **MediaPipe** - Google's hand landmark detection (Apache 2.0)
- **OpenCV** - Computer vision library (Apache 2.0)
- **PyAutoGUI** - Cross-platform mouse/keyboard control (BSD)

## Future Enhancements

- [ ] Linux/macOS support
- [ ] Custom gesture profiles
- [ ] Gesture recording and training
- [ ] Eye-gaze integration
- [ ] Voice control commands
- [ ] Haptic feedback support

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Verify webcam works in other applications
3. Check console output for error messages
4. Try adjusting parameters in config.py

---

**Version**: 1.0  
**Last Updated**: April 2026
