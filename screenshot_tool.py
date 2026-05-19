"""
Screenshot capture tool for botty development.
Takes screenshots from the D2R window and saves them with timestamps.
Usage:
    python screenshot_tool.py              # press keys to capture
    python screenshot_tool.py --auto       # auto-capture every 2 seconds
Keys:
    F1  - capture current screen
    F2  - capture and open in image viewer
    F3  - capture cropped region (center of screen)
    F11 - toggle auto-capture mode
    F12 - exit
Screenshots saved to screenshots/
"""

import os
import sys
import time
import keyboard
import numpy as np
import cv2
from datetime import datetime

# Fix tesserocr DLL loading (same as main.py)
if sys.platform == "win32":
    _conda_dll_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conda_env", "Library", "bin")
    if not os.path.isdir(_conda_dll_dir):
        _conda_dll_dir = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Library", "bin")
    if os.path.isdir(_conda_dll_dir):
        os.add_dll_directory(_conda_dll_dir)

from mss import mss
from screen import find_and_set_window_position, get_offset_state, grab as screen_grab

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def capture_full():
    """Capture the D2R window using botty's screen.grab()."""
    # Find the window first
    find_and_set_window_position()
    if not get_offset_state():
        print("[ERROR] Could not find D2R window. Is D2R running and visible?")
        return None
    return screen_grab(force_new=True)


def capture_center_crop(crop_size=(640, 360)):
    """Capture the center of the D2R window."""
    img = capture_full()
    if img is None:
        return None
    h, w = img.shape[:2]
    cw, ch = crop_size
    x1 = (w - cw) // 2
    y1 = (h - ch) // 2
    return img[y1:y1+ch, x1:x1+cw]


def save_screenshot(img, label=""):
    """Save screenshot with timestamp."""
    if img is None:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"screenshot_{ts}"
    if label:
        name += f"_{label}"
    name += ".png"
    path = os.path.join(SCREENSHOT_DIR, name)
    cv2.imwrite(path, img)
    abs_path = os.path.abspath(path)
    print(f"[SAVED] {abs_path}")
    return abs_path


def show_and_save(img):
    """Save and open screenshot in default viewer."""
    if img is None:
        return
    path = save_screenshot(img, "view")
    if path and sys.platform == "win32":
        os.startfile(path)


def run_interactive():
    """Interactive screenshot mode - press F1 to capture."""
    print(f"""
=== Botty Screenshot Tool ===
D2R must be running and visible.

  F1  - capture full D2R window
  F2  - capture full + open in default image viewer
  F3  - capture center crop (640x360)
  F11 - toggle auto-capture (every 2s)
  F12 - exit

Screenshots saved to: {os.path.abspath(SCREENSHOT_DIR)}
""")

    keyboard.add_hotkey('f1', lambda: save_screenshot(capture_full()))
    keyboard.add_hotkey('f2', lambda: show_and_save(capture_full()))
    keyboard.add_hotkey('f3', lambda: save_screenshot(capture_center_crop(), "center"))

    auto_mode = False
    auto_running = False

    def toggle_auto():
        nonlocal auto_mode, auto_running
        auto_mode = not auto_mode
        if auto_mode:
            print("[AUTO CAPTURE ON] - capturing every 2 seconds. Press F11 to stop.")
            auto_running = True
            t = _start_auto()
        else:
            print("[AUTO CAPTURE OFF]")
            auto_running = False

    def _start_auto():
        import threading
        def loop():
            while auto_running:
                save_screenshot(capture_full(), "auto")
                time.sleep(2)
        threading.Thread(target=loop, daemon=True).start()

    keyboard.add_hotkey('f11', toggle_auto)
    keyboard.add_hotkey('f12', lambda: sys.exit(0))

    print("Ready. Press F1 to take a screenshot, F12 to exit.")
    keyboard.wait()


if __name__ == "__main__":
    if "--auto" in sys.argv:
        print("[AUTO MODE] Capturing every 2 seconds. Press Ctrl+C to stop.")
        try:
            while True:
                save_screenshot(capture_full(), "auto")
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        run_interactive()
