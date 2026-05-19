"""
Desktop screenshot tool - captures the full Windows desktop or a specific window.
Usage:
    python desktop_snap.py              # capture full desktop
    python desktop_snap.py D2R         # capture D2R window only
Saves to screenshots/desktop_snap.png
"""
import os
import sys
import cv2
from mss import mss

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots", "desktop_snap.png")
os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)


def snap_full_desktop():
    """Capture the full desktop."""
    with mss() as sct:
        img = sct.grab(sct.monitors[1])  # monitors[1] = primary display
        # Convert from BGRA to BGR
        img_bgr = img.rgb
        cv2.imwrite(SAVE_PATH, img_bgr)
    print(f"Saved full desktop to: {SAVE_PATH}")
    print(f"Shape: {cv2.imread(SAVE_PATH).shape}")


def snap_d2r_window():
    """Capture the D2R window."""
    import numpy as np
    import win32gui
    import win32ui
    import win32con
    
    # Find D2R window
    def enum_cb(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "diablo" in title.lower() or "d2r" in title.lower():
                results.append(hwnd)
    
    hwnds = []
    win32gui.EnumWindows(enum_cb, hwnds)
    
    if not hwnds:
        print("ERROR: D2R window not found. Is it running?")
        return
    
    hwnd = hwnds[0]
    print(f"Found D2R window: {win32gui.GetWindowText(hwnd)}")
    
    # Get window client area
    rect = win32gui.GetClientRect(hwnd)
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    
    # Capture client area
    hdc = win32gui.GetDC(hwnd)
    hdc_mem = win32gui.CreateCompatibleDC(hdc)
    bmp = win32gui.CreateCompatibleBitmap(hdc, w, h)
    win32gui.SelectObject(hdc_mem, bmp)
    win32gui.BitBlt(hdc_mem, 0, 0, w, h, hdc, 0, 0, win32con.SRCCOPY)
    
    # Convert to image
    bmp_info = win32ui.CreateBitmapFromHandle(bmp)
    bmp_info.SaveBitmapFile(hdc_mem, SAVE_PATH)
    
    win32gui.DeleteObject(bmp)
    win32gui.DeleteDC(hdc_mem)
    win32gui.ReleaseDC(hwnd, hdc)
    
    img = cv2.imread(SAVE_PATH)
    print(f"Saved D2R window to: {SAVE_PATH}")
    print(f"Shape: {img.shape}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "D2R":
        snap_d2r_window()
    else:
        snap_full_desktop()
