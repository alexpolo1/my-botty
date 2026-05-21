"""
Native Windows input via ctypes SendInput API.
No kernel drivers, no third-party DLLs. Only standard system DLLs (user32, kernel32).
"""
import ctypes
import time
import struct
from ctypes import wintypes

# ─── user32 constants ───

# INPUT_TYPE
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# MOUSEEVENTF flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_HWHEEL = 0x01000

# KEYEVENTF flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# ─── structs ───

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUTUNION),
    ]

INPUT_ARRAY = ctypes.ARRAY(INPUT, 64)

# ─── load user32 ───

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.SendInput.restype = wintypes.UINT
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]

user32.GetAsyncKeyState.restype = wintypes.SHORT
user32.GetAsyncKeyState.argtypes = [wintypes.WORD]

user32.GetCursorPos.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]

user32.GetSystemMetrics.restype = wintypes.INT
user32.GetSystemMetrics.argtypes = [wintypes.INT]

user32.MapVirtualKeyW.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]

# ─── VK code mapping ───

# Extended keys (require KEYEVENTF_EXTENDEDKEY flag)
EXTENDED_KEYS = {
    0x27,  # numpad /
    0x91,  # right ctrl
    0x9A,  # right shift
    0xB5,  # numpad *
    0xB8,  # right alt
    0xB9,  # right win
    0xBA,  # apps key (menu)
    0xC1,  # numpad enter
    0xC7,  # numpad .
    0xC8,  # snap
}

# Common key name -> VK code
VK_MAP = {
    "left": 0x25, "right": 0x27, "up": 0x26, "down": 0x28,
    "enter": 0x0D, "return": 0x0D, "space": 0x20, "escape": 0x1B, "esc": 0x1B,
    "backspace": 0x08, "tab": 0x09, "delete": 0x2E, "end": 0x23, "home": 0x24,
    "insert": 0x2D, "pageup": 0x21, "pagedown": 0x22,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "shift": 0xA0, "left shift": 0xA0, "right shift": 0xA1,
    "ctrl": 0xA2, "left ctrl": 0xA2, "right ctrl": 0xA3,
    "lctrl": 0xA2, "rctrl": 0xA3, "ctrl_l": 0xA2, "ctrl_r": 0xA3,
    "alt": 0xA4, "left alt": 0xA4, "right alt": 0xA5,
    "lalt": 0xA4, "ralt": 0xA5, "alt_l": 0xA4, "alt_r": 0xA5,
    "caps lock": 0x14, "capslock": 0x14,
    "num lock": 0x90, "numlock": 0x90,
    "scroll lock": 0x91, "scrolllock": 0x91,
    "print screen": 0x2C, "printscr": 0x2C,
    "pause": 0x13,
    "lwin": 0x5B, "rwin": 0x5C, "win": 0x5B,
    "apps": 0x5D,
    "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62,
    "numpad3": 0x63, "numpad4": 0x64, "numpad5": 0x65,
    "numpad6": 0x66, "numpad7": 0x67, "numpad8": 0x68,
    "numpad9": 0x69,
    "numpad.": 0x6E, "numpad/": 0x6F,
    "numpad*": 0x6B, "numpad+": 0x6C,
    "numpad-": 0x6D,
    "volume_up": 0xAF, "volume_down": 0xAE, "volume_mute": 0xAD,
    "media_next": 0xB0, "media_prev": 0xB1, "media_stop": 0xB2, "media_play_pause": 0xB3,
    "back": 0xA6, "forward": 0xA7,
}

# ─── core input functions ───

def _send_input(inp: INPUT):
    """Send a single INPUT event."""
    arr = INPUT_ARRAY()
    arr[0] = inp
    result = user32.SendInput(1, arr, ctypes.sizeof(INPUT))
    if result != 1:
        raise RuntimeError(f"SendInput failed, returned {result}")

def _make_keyboard_input(vk: int, flags: int = 0, scan: int = 0):
    """Create a KEYBDINPUT struct."""
    i = INPUT()
    i.type = INPUT_KEYBOARD
    i.union.ki.wVk = vk
    i.union.ki.wScan = scan
    i.union.ki.dwFlags = flags
    i.union.ki.dwExtraInfo = None
    return i

def _make_mouse_input(flags: int, dx: int = 0, dy: int = 0, data: int = 0):
    """Create a MOUSEINPUT struct."""
    i = INPUT()
    i.type = INPUT_MOUSE
    i.union.mi.dx = dx
    i.union.mi.dy = dy
    i.union.mi.mouseData = data
    i.union.mi.dwFlags = flags | MOUSEEVENTF_ABSOLUTE
    i.union.mi.dwExtraInfo = None
    return i

def _get_vk(key_name: str):
    """Resolve a key name to its VK code."""
    key_name = key_name.strip().lower()
    if key_name in VK_MAP:
        return VK_MAP[key_name]
    # Single character
    if len(key_name) == 1:
        vk = ord(key_name)
        # Digit keys 0-9 map to VK_0 (0x0B) through VK_9 (0x13)
        if '0' <= key_name <= '9':
            return 0x0B + ord(key_name) - ord('0')
        # Letter keys map directly to their ASCII value (uppercase)
        if 'a' <= key_name <= 'z':
            return ord(key_name.upper())
        return vk
    # Try pywin32 style (vk_key)
    return None

def _is_extended(vk: int) -> bool:
    return vk in EXTENDED_KEYS

def _get_scan(vk: int) -> int:
    """Get scan code for a VK."""
    return user32.MapVirtualKeyW(vk, 0)

def key_down(vk: int):
    """Press a key down."""
    extended = KEYEVENTF_EXTENDEDKEY if _is_extended(vk) else 0
    scan = _get_scan(vk) if vk else 0
    _send_input(_make_keyboard_input(vk, extended, scan))

def key_up(vk: int):
    """Release a key."""
    extended = KEYEVENTF_EXTENDEDKEY if _is_extended(vk) else 0
    scan = _get_scan(vk) if vk else 0
    _send_input(_make_keyboard_input(vk, extended | KEYEVENTF_KEYUP, scan))

def key_press(vk: int):
    """Press and release a key."""
    key_down(vk)
    key_up(vk)

def send_key(key: str, down=True, up=True):
    """Press and/or release a key by name."""
    vk = _get_vk(key)
    if vk is None:
        raise ValueError(f"Unknown key: {key}")
    if down:
        key_down(vk)
    if up:
        key_up(vk)

def key_state(key: str) -> bool:
    """Check if a key is currently pressed (via GetAsyncKeyState)."""
    vk = _get_vk(key)
    if vk is None:
        return False
    state = user32.GetAsyncKeyState(vk)
    return bool(state & 0x8000)

# ─── mouse ───

def get_screen_size():
    """Get screen dimensions for absolute mouse positioning."""
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

def mouse_move(x: int, y: int):
    """Move mouse to absolute screen position (uses absolute SendInput)."""
    screen_w, screen_h = get_screen_size()
    # SendInput expects normalized absolute coordinates 0-65535
    norm_x = int(x * 65535 / screen_w)
    norm_y = int(y * 65535 / screen_h)
    _send_input(_make_mouse_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, norm_x, norm_y))

def mouse_down(button: str = "left"):
    """Press mouse button down."""
    if button == "left":
        _send_input(_make_mouse_input(MOUSEEVENTF_LEFTDOWN))
    elif button == "right":
        _send_input(_make_mouse_input(MOUSEEVENTF_RIGHTDOWN))
    elif button == "middle":
        _send_input(_make_mouse_input(MOUSEEVENTF_MIDDLEDOWN))
    else:
        raise ValueError(f"Unknown button: {button}")

def mouse_up(button: str = "left"):
    """Release mouse button."""
    if button == "left":
        _send_input(_make_mouse_input(MOUSEEVENTF_LEFTUP))
    elif button == "right":
        _send_input(_make_mouse_input(MOUSEEVENTF_RIGHTUP))
    elif button == "middle":
        _send_input(_make_mouse_input(MOUSEEVENTF_MIDDLEUP))
    else:
        raise ValueError(f"Unknown button: {button}")

def mouse_click(button: str = "left"):
    """Click (press + release) a mouse button."""
    mouse_down(button)
    mouse_up(button)

def mouse_wheel(delta: int):
    """Scroll mouse wheel (positive = up, negative = down).
    Delta is in "clicks" — each click is 120 units."""
    wheel_delta = delta * 120
    _send_input(_make_mouse_input(MOUSEEVENTF_WHEEL, 0, 0, wheel_delta))

def get_cursor_pos():
    """Get cursor position as (x, y)."""
    from ctypes import wintypes as wt
    p = wt.POINT()
    if user32.GetCursorPos(ctypes.byref(p)):
        return (p.x, p.y)
    return (0, 0)

# ─── text input ───

def send_text(text: str, delay: float = 0.05):
    """Send text character by character."""
    for ch in text:
        vk = _get_vk(ch)
        if vk is None:
            continue
        # Determine if shift is needed
        if ch.isupper() and ch.lower() != ch:
            # Need shift for uppercase letters
            key_down(0xA0)  # left shift
            key_press(vk)
            key_up(0xA0)
        elif not ch.isalnum() and ch != ' ':
            # Shift needed for most punctuation
            key_down(0xA0)
            key_press(vk)
            key_up(0xA0)
        else:
            key_press(vk)
        from utils.misc import wait as _wait
        _wait(delay, delay * 1.2)
