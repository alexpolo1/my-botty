"""
D2R Asset Extractor

Runs on your local Windows machine. Captures D2R, saves screenshot.
You then send the screenshot to the AI agent for analysis.
AI returns bounding boxes -> run crop.py to extract PNGs.

Usage:
  Run:    python asset_extractor.py
  F1:     Capture D2R screen -> screenshots/debug/latest.png
  F2:     Crop entities from screenshots/debug/latest_annotations.json
  F3:     List existing assets
  F12:    Exit

Workflow:
  1. Run this script in the botty conda env
  2. F1 to capture
  3. Tell your AI agent to analyze screenshots/debug/latest.png
  4. AI writes screenshots/debug/latest_annotations.json with bounding boxes
  5. F2 to crop entities into assets/enemies/ or assets/npc/
"""
import os, sys, cv2, numpy as np, keyboard, json, ctypes, win32gui
from datetime import datetime
from mss import mss

# DPI awareness - must be first
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

# Fix tesserocr DLLs
if sys.platform == "win32":
    _dll = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Library", "bin")
    if os.path.isdir(_dll):
        os.add_dll_directory(_dll)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

BASE = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE, "screenshots", "debug")
ENEMIES_DIR = os.path.join(BASE, "assets", "enemies")
NPC_DIR = os.path.join(BASE, "assets", "npc")

for d in [SAVE_DIR, ENEMIES_DIR, NPC_DIR]:
    os.makedirs(d, exist_ok=True)

LATEST_PATH = os.path.join(SAVE_DIR, "latest.png")
ANNOTATIONS_PATH = os.path.join(SAVE_DIR, "latest_annotations.json")

# Known NPC names for routing
NPC_NAMES = {
    'akara', 'charsi', 'kashya', 'cain', 'drognan', 'lysander',
    'fara', 'ormus', 'tyrael', 'jamella', 'halbu', 'qual_kehk',
    'qual-kehk', 'qualkehk', 'malah', 'larzuk', 'anya'
}


def find_d2r():
    hwnds = []
    def cb(h, r):
        title = win32gui.GetWindowText(h)
        if 'diablo' in title.lower() and win32gui.IsWindowVisible(h):
            r.append(h)
    win32gui.EnumWindows(cb, hwnds)
    return hwnds[0] if hwnds else None


def grab():
    """Grab D2R client area. Resizes to 1280x720 if needed."""
    hwnd = find_d2r()
    if not hwnd:
        print("  [ERROR] D2R not found. Is it running and visible?")
        return None

    client = win32gui.GetClientRect(hwnd)
    w, h = client[2] - client[0], client[3] - client[1]
    screen_pos = win32gui.ClientToScreen(hwnd, (0, 0))

    with mss() as sct:
        region = {
            'top': screen_pos[1],
            'left': screen_pos[0],
            'width': w,
            'height': h
        }
        sct_img = sct.grab(region)
        img = np.array(sct_img)[:, :, :3]  # BGRA -> BGR

    if w != 1280 or h != 720:
        img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_LINEAR)
        print(f"  [RESIZED] {w}x{h} -> 1280x720")
    else:
        print(f"  [CAPTURED] {w}x{h}")

    return img


def on_f1():
    """Capture D2R and save."""
    print("\n[=== CAPTURING ===]")
    img = grab()
    if not img:
        return
    cv2.imwrite(LATEST_PATH, img)
    print(f"  [SAVED] {LATEST_PATH}")
    print(f"  Now ask your AI agent to analyze: {LATEST_PATH}")
    print(f"  AI should write: {ANNOTATIONS_PATH}")
    print('  Format: [{"name":"skeleton","x":100,"y":200,"w":60,"h":80}, ...]')


def on_f2():
    """Crop entities from latest capture using annotations JSON."""
    print("\n[=== CROPPING ENTITIES ===]")
    if not os.path.exists(LATEST_PATH):
        print("  [ERROR] No capture found. Press F1 first.")
        return
    if not os.path.exists(ANNOTATIONS_PATH):
        print("  [ERROR] No annotations found.")
        print(f"  Create: {ANNOTATIONS_PATH}")
        print('  [{"name":"skeleton","x":100,"y":200,"w":60,"h":80}, ...]')
        return

    img = cv2.imread(LATEST_PATH)
    with open(ANNOTATIONS_PATH) as f:
        entities = json.load(f)

    print(f"  Image: {img.shape[1]}x{img.shape[0]}, Entities: {len(entities)}")

    saved = 0
    for ent in entities:
        name = ent['name'].lower().replace(' ', '_')
        x, y = int(ent['x']), int(ent['y'])
        w, h = int(ent['w']), int(ent['h'])
        i_w, i_h = img.shape[1], img.shape[0]

        # Crop with 5px padding
        pad = 5
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(i_w, x + w + pad), min(i_h, y + h + pad)
        crop = img[y1:y2, x1:x2]

        # Route to npc or enemies folder
        if name in NPC_NAMES:
            save_dir = NPC_DIR
        else:
            save_dir = ENEMIES_DIR

        # Auto-number duplicates
        fname = f"{name}.png"
        save_path = os.path.join(save_dir, fname)
        variant = 1
        while os.path.exists(save_path):
            variant += 1
            fname = f"{name}_{variant}.png"
            save_path = os.path.join(save_dir, fname)

        cv2.imwrite(save_path, crop)
        print(f"  [SAVED] {save_path} ({crop.shape[1]}x{crop.shape[0]})")
        saved += 1

    print(f"\n  Total: {saved} assets cropped.")


def on_f3():
    """List existing assets."""
    print("\n[=== ASSETS INVENTORY ===]")
    for label, d in [("enemies", ENEMIES_DIR), ("npc", NPC_DIR)]:
        if os.path.isdir(d):
            files = sorted(os.listdir(d))
            print(f"\n  assets/{label}/ ({len(files)} files):")
            for f in files:
                sz = os.path.getsize(os.path.join(d, f))
                print(f"    {f} ({sz}b)")
        else:
            print(f"\n  assets/{label}/ - EMPTY")


def run():
    print("=== D2R Asset Extractor ===")
    print("  F1  - Capture D2R screen")
    print("  F2  - Crop entities from annotations")
    print("  F3  - List assets")
    print("  F12 - Exit")
    print("Ready.")

    keyboard.add_hotkey('f1', on_f1)
    keyboard.add_hotkey('f2', on_f2)
    keyboard.add_hotkey('f3', on_f3)
    keyboard.add_hotkey('f12', lambda: (print("\nBye."), sys.exit(0)))
    keyboard.wait()


if __name__ == "__main__":
    run()
