"""
Auto-detect D2R key bindings from the game's .key/.keyo file.

The .key file lives in:
  %APPDATA%/Diablo II Resurrected/<char_name>.key        (offline)
  %APPDATA%/Diablo II Resurrected/<char_name>.keyo       (online)

Format (text, one binding per line, first line is count):
  <num_bindings>
  <vk_code> <action_type> <param>

Action types:
  1 = skill hotkey       (param = skill slot 1-7, corresponds to UI bar positions)
  2 = inventory          (param = 0)
  3 = show_items         (param = 0)
  4 = stand_still        (param = 0)
  5 = show_belt          (param = 0)
  6 = potion             (param = potion slot 1-4)
  13 = force_move        (param = 0)

VK codes are standard Windows virtual key codes:
  48='0', 49='1', ..., 57='9'
  65='a', ..., 90='z'
  112='f1', ..., 123='f12'
  16='capslock', 256='left alt', 27='esc', etc.

After reading the .key file, this module auto-fills empty hotkey values
in the config. Params.ini values always take priority.

Limitations:
  The .key file only tells us which KEY is bound to each skill slot (1-7),
  not which SKILL is in that slot. To know that, the bot must visually
  inspect the skill bar in-game (PR #905 approach). For now we only auto-fill
  non-skill keys (inventory, belt, stand_still, etc.) and map skill slots
  to already-configured hotkeys.
"""

import os

from logger import Logger

# Standard Windows VK codes -> keyboard names (lowercase for params.ini compatibility)
VK_MAP = {
    # Numbers (top row)
    48: "0", 49: "1", 50: "2", 51: "3", 52: "4",
    53: "5", 54: "6", 55: "7", 56: "8", 57: "9",
    # Letters
    65: "a", 66: "b", 67: "c", 68: "d", 69: "e", 70: "f",
    71: "g", 72: "h", 73: "i", 74: "j", 75: "k", 76: "l",
    77: "m", 78: "n", 79: "o", 80: "p", 81: "q", 82: "r",
    83: "s", 84: "t", 85: "u", 86: "v", 87: "w", 88: "x",
    89: "y", 90: "z",
    # Function keys
    112: "f1", 113: "f2", 114: "f3", 115: "f4",
    116: "f5", 117: "f6", 118: "f7", 119: "f8",
    120: "f9", 121: "f10", 122: "f11", 123: "f12",
    # Modifiers
    16: "capslock",
    160: "left shift",
    161: "right shift",
    162: "left ctrl",
    163: "right ctrl",
    164: "left alt",
    165: "right alt",
    256: "alt",
    257: "ctrl",
    258: "shift",
    # Navigation / misc
    27: "esc",
    28: "enter",
    9: "tab",
    32: "space",
    283: "backspace",
    37: "left", 38: "up", 39: "right", 40: "down",
    44: "insert", 45: "delete", 46: "home", 47: "end",
    188: ",", 190: ".", 191: "/", 186: ";", 187: "=",
    189: "-", 192: "`", 219: "[", 221: "]", 220: "\\",
}


def vk_to_name(vk_code: int) -> str | None:
    """Convert a virtual key code to a keyboard name."""
    return VK_MAP.get(vk_code, None)


# ─── File discovery ─────────────────────────────────────────────────────────

def _find_key_file(d2r_path: str, char_name: str) -> str | None:
    """Find the .key or .keyo file, searching common locations."""
    # Paths to check (in priority order)
    candidates = []

    # 1. Saved Games folder (most common for D2R)
    saved_games = os.path.expanduser("~/Saved Games/Diablo II Resurrected")
    for ext in ("key", "keyo"):
        candidates.append(os.path.join(saved_games, f"{char_name}.{ext}"))
        # Online chars sometimes have hash suffix: e.g. Paladin53672482.keyo
        # We'll scan for any file starting with char_name + .key(o)
        if os.path.isdir(saved_games):
            try:
                for f in os.listdir(saved_games):
                    base = os.path.splitext(f)[0]
                    if base.startswith(char_name) and f.endswith(".keyo"):
                        candidates.append(os.path.join(saved_games, f))
            except OSError:
                pass

    # 2. D2R install directory keybinds (try both keybinds subdir and root)
    d2r_keybinds = os.path.join(d2r_path, "keybinds")
    for ext in ("key", "keyo"):
        candidates.append(os.path.join(d2r_keybinds, f"{char_name}.{ext}"))
        candidates.append(os.path.join(d2r_path, f"{char_name}.{ext}"))

    # 3. APPDATA
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        for sub in ("keybinds", "d2r_data/char"):
            for ext in ("key", "keyo"):
                candidates.append(os.path.join(appdata, "Diablo II Resurrected", sub, f"{char_name}.{ext}"))

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


# ─── Parsing ─────────────────────────────────────────────────────────────────

def parse_key_file(filepath: str) -> dict:
    """
    Parse a D2R .key file.

    Returns dict with keys:
      inventory, show_items, stand_still, show_belt, force_move,
      potion1..potion4,
      skill1..skill7  (slot number -> key name)
    """
    result = {}

    try:
        # Try utf-8 first, then latin-1, then binary
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                with open(filepath, "r", encoding=encoding) as f:
                    lines = f.read().strip().splitlines()
                break
            except (UnicodeDecodeError, ValueError):
                continue
        else:
            Logger.warning(f"Could not parse key file '{filepath}' with any encoding")
            return result
    except OSError as e:
        Logger.warning(f"Failed to open key file '{filepath}': {e}")
        return result

    if not lines:
        return result

    # First line is the number of bindings
    try:
        count = int(lines[0].strip())
    except ValueError:
        count = len(lines) - 1

    for line in lines[1:1 + count]:
        parts = line.strip().split()
        if len(parts) < 3:
            continue

        try:
            vk_code = int(parts[0])
            action_type = int(parts[1])
            param = int(parts[2])
        except (ValueError, IndexError):
            continue

        key_name = vk_to_name(vk_code)
        if key_name is None:
            Logger.debug(f"Unknown VK code {vk_code} in key file, skipping")
            continue

        # Map action type to result key
        action_map = {
            1: f"skill{param}",      # skill slot
            2: "inventory",
            3: "show_items",
            4: "stand_still",
            5: "show_belt",
            6: f"potion{param}",
            13: "force_move",
        }

        result_key = action_map.get(action_type)
        if result_key:
            result[result_key] = key_name

    return result


# ─── Auto-fill ────────────────────────────────────────────────────────────────

# Mapping: parsed action name -> config.char key
CHAR_KEY_MAP = {
    "inventory": "inventory_screen",
    "show_items": "show_items",
    "stand_still": "stand_still",
    "show_belt": "show_belt",
    "force_move": "force_move",
}


def _try_fill(config: dict, key: str, value: str) -> None:
    """Fill a config value from detected binding. Only if empty. Warn on mismatch."""
    current = config.get(key, "")
    if not current:
        config[key] = value
        Logger.info(f"Auto-filled '{key}' = '{value}' from .key file")
    elif current.lower() != value.lower():
        # Normalize: treat 'alt', 'left alt', 'right alt' as equivalent
        # Same for 'ctrl', 'shift'
        normalized = _normalize_key(value).strip()
        current_norm = _normalize_key(current).strip()
        if normalized == current_norm:
            Logger.debug(f"Key '{key}': '{current}' ~ '{value}' (normalized match, keeping params.ini)")
            return
        Logger.warning(
            f"Hotkey mismatch '{key}': params.ini='{current}' != .key='{value}'. "
            f"Using params.ini value."
        )


def _normalize_key(k: str) -> str:
    """Normalize key names for comparison: 'left alt'/'right alt'/'alt' -> 'alt'."""
    k = k.lower().strip()
    if k in ("left alt", "right alt", "alt"):
        return "alt"
    if k in ("left ctrl", "right ctrl", "ctrl"):
        return "ctrl"
    if k in ("left shift", "right shift", "shift"):
        return "shift"
    return k


def _auto_fill_char(char_config: dict, bindings: dict) -> None:
    """Auto-fill [char] section hotkeys."""
    for action_key, char_key in CHAR_KEY_MAP.items():
        if action_key in bindings:
            _try_fill(char_config, char_key, bindings[action_key])

    for slot in range(1, 5):
        pk = f"potion{slot}"
        if pk in bindings:
            _try_fill(char_config, pk, bindings[pk])


def _auto_fill_skills(config_instance, bindings: dict) -> None:
    """
    Auto-fill skill hotkeys from detected skill slot bindings.

    Strategy:
      1. Match existing config hotkeys to detected skill slots (if a skill's
         configured hotkey matches a detected slot key, we know that slot).
      2. For empty config skills, we CANNOT reliably know which unused slot
         they map to without in-game visual inspection. So we log them as
         'unmatched' and suggest the user set them manually.
    """
    skill_slots = {}  # slot_num -> key_name
    for k, v in bindings.items():
        if k.startswith("skill"):
            try:
                slot = int(k[5:])
                skill_slots[slot] = v
            except ValueError:
                pass

    if not skill_slots:
        return

    # Get the active character section
    char_type = config_instance.char.get("type", "")
    section_cfg = getattr(config_instance, char_type, None)
    if section_cfg is None:
        return

    # Step 1: match configured skills to slots
    for skill_key, configured_key in section_cfg.items():
        if not configured_key:
            continue
        for slot, slot_key in skill_slots.items():
            if slot_key.lower() == configured_key.lower():
                Logger.debug(f"Skill '{skill_key}' (slot {slot}) hotkey confirmed: {slot_key}")
                break

    # Step 2: log unmatched slots (can't auto-assign without visual discovery)
    used_slots = set()
    for skill_key, configured_key in section_cfg.items():
        if not configured_key:
            continue
        for slot, slot_key in skill_slots.items():
            if slot_key.lower() == configured_key.lower():
                used_slots.add(slot)

    unused = {s: k for s, k in skill_slots.items() if s not in used_slots}
    if unused:
        Logger.info(
            f"Unmatched skill slots: {unused}. "
            f"These keys are bound to skill slots in-game but not yet mapped to "
            f"config entries for '{char_type}'. Set them in params.ini or custom.ini."
        )


# ─── Main entry point ─────────────────────────────────────────────────────────

def apply_key_bindings(config_instance) -> None:
    """
    Detect key bindings from the .key file and apply them to the config.

    Called from config.py load_data() after all config dicts are populated.
    """
    d2r_path = config_instance.general.get("d2r_path", "")
    char_name = config_instance.general.get("name", "")

    if not char_name:
        Logger.debug("Key auto-detection: no character name configured")
        return

    key_file = _find_key_file(d2r_path, char_name)
    if key_file is None:
        Logger.info(
            f"Key file not found for '{char_name}'. "
            f"Hotkeys must be set manually in params.ini."
        )
        return

    Logger.info(f"Reading key bindings from: {key_file}")
    bindings = parse_key_file(key_file)

    if not bindings:
        Logger.warning(f"Key file '{key_file}' was empty or unparseable.")
        return

    Logger.info(f"Detected bindings: {bindings}")

    _auto_fill_char(config_instance.char, bindings)
    _auto_fill_skills(config_instance, bindings)

    Logger.info("Key auto-detection complete.")
