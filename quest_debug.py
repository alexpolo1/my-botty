"""
D2R capture tool - works with Windows DPI scaling.

Set DPI awareness then grab the D2R client area directly.

Keys: F1-full OCR  F2-dialogue  F3-questlog  F4-NPCs  F5-pixel  F12-exit
"""
import os, sys, cv2, numpy as np, keyboard, win32gui, win32con, ctypes
from datetime import datetime

# Set DPI awareness - this makes Win32 APIs return logical (unscaled) coordinates
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

SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots", "debug")
os.makedirs(SAVE, exist_ok=True)


def find_d2r():
    hwnds = []
    def cb(h, r):
        if 'diablo' in win32gui.GetWindowText(h).lower() and win32gui.IsWindowVisible(h):
            r.append(h)
    win32gui.EnumWindows(cb, hwnds)
    return hwnds[0] if hwnds else None


def grab():
    """Grab D2R client area at native 1280x720 resolution."""
    from mss import mss
    hwnd = find_d2r()
    if not hwnd:
        print("  [ERROR] D2R not found")
        return None
    
    client = win32gui.GetClientRect(hwnd)
    w, h = client[2]-client[0], client[3]-client[1]
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
    
    # Resize to 1280x720 if needed
    if w != 1280 or h != 720:
        img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_LINEAR)
        print(f"  [RESIZED] {w}x{h} -> 1280x720")
    else:
        print(f"  [CAPTURED] {w}x{h}")
    
    return img


def ocr(img, roi=None):
    try:
        from d2r_image.ocr import image_to_text
        target = img if roi is None else img[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
        result = image_to_text(target, psm=6, scale=1.5, threshold=25)
        return [r.text.strip() for r in result if r.text.strip()]
    except Exception as e:
        return [f"[OCR ERROR] {e}"]


def save(img, label):
    path = os.path.join(SAVE, f"{label}_{datetime.now().strftime('%H%M%S')}.png")
    cv2.imwrite(path, img)
    print(f"  [SAVED] {path}")
    return path


# === Handlers ===

def on_f1():
    print("\n[=== FULL CAPTURE ===]")
    img = grab()
    if not img:
        return
    h, w = img.shape[:2]
    print(f"  Size: {w}x{h}")
    save(img, "full")
    
    # UI detection
    print("  UI:")
    try:
        from ui_manager import ScreenObjects, is_visible
        found = False
        for name in ['InGame', 'Loading', 'MainMenu', 'OnlineStatus', 'DeathScreen',
                     'NPCDialogue', 'RightPanel', 'LeftPanel', 'SkillsExpanded']:
            obj = getattr(ScreenObjects, name, None)
            if obj and is_visible(obj, img):
                print(f"    [VISIBLE] {name}")
                found = True
        if not found:
            print("    (none)")
    except Exception as e:
        print(f"    [err] {e}")
    
    # Full OCR
    print("  OCR:")
    lines = ocr(img)
    for l in lines[:30]:
        print(f"    {l}")
    if len(lines) > 30:
        print(f"    ... and {len(lines)-30} more")


def on_f2():
    print("\n[=== DIALOGUE ===]")
    img = grab()
    if not img:
        return
    save(img, "dialogue")
    
    text = ocr(img, (200, 460, 880, 100))
    if text:
        print("  NPC says:")
        for l in text:
            print(f"    {l}")
    else:
        print("  (no NPC text)")
    
    opts = ocr(img, (200, 560, 880, 140))
    if opts:
        print("  Options:")
        for i, o in enumerate(opts):
            print(f"    [{i}] {o}")
    else:
        print("  (no options detected - is dialogue box open?)")


def on_f3():
    print("\n[=== QUEST LOG ===]")
    img = grab()
    if not img:
        return
    save(img, "quest_log")
    for l in ocr(img, (200, 100, 880, 520)):
        print(f"    {l}")


def on_f4():
    print("\n[=== NPC DETECTION ===]")
    img = grab()
    if not img:
        return
    save(img, "npcs")
    try:
        import template_finder
        from npc_manager import npcs
        found = []
        for name, data in npcs.items():
            for t in data.get("template_group", []):
                r = template_finder.search(t, img, threshold=0.35)
                if r.valid:
                    found.append(f"  {name} at {r.center_monitor} ({r.score:.2f})")
                    break
        for f in found:
            print(f)
        if not found:
            print("  (none)")
    except Exception as e:
        print(f"  [ERROR] {e}")


def on_f5():
    img = grab()
    if not img:
        return
    import mouse as _mouse
    mx, my = _mouse.get_position()
    hwnd = find_d2r()
    if hwnd:
        screen_pos = win32gui.ClientToScreen(hwnd, (0, 0))
        ix = mx - screen_pos[0]
        iy = my - screen_pos[1]
        if 0 <= ix < img.shape[1] and 0 <= iy < img.shape[0]:
            b, g, r = img[iy, ix]
            print(f"  ({ix},{iy}) RGB({r},{g},{b})")
        else:
            print("  Mouse outside D2R client area")


# === Run ===

def run():
    print("=== Botty Capture Tool ===")
    print("  F1  - Full capture + OCR + UI detection")
    print("  F2  - Dialogue capture + OCR")
    print("  F3  - Quest log OCR (press O in D2R first)")
    print("  F4  - Detect NPCs")
    print("  F5  - Mouse pixel color")
    print("  F12 - Exit")
    print("Ready.")
    
    keyboard.add_hotkey('f1', on_f1)
    keyboard.add_hotkey('f2', on_f2)
    keyboard.add_hotkey('f3', on_f3)
    keyboard.add_hotkey('f4', on_f4)
    keyboard.add_hotkey('f5', on_f5)
    keyboard.add_hotkey('f12', lambda: (print("\nBye."), sys.exit(0)))
    keyboard.wait()


if __name__ == "__main__":
    run()
