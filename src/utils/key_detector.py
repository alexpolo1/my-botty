"""
Auto-detect D2R key bindings from .key/.keyo files.

Binary format (D2R 2.x): 4-byte header + 137 x 10-byte entries + 2 trailing bytes.
Each entry: [pad:u16, VK:u16, action:u16, pad:u16, slot:u16]
action=1 = skill key, action=0 = non-skill key.
"""

import os
import struct

from logger import Logger

VK_MAP = {
    48: "0", 49: "1", 50: "2", 51: "3", 52: "4",
    53: "5", 54: "6", 55: "7", 56: "8", 57: "9",
    65: "a", 66: "b", 67: "c", 68: "d", 69: "e", 70: "f",
    71: "g", 72: "h", 73: "i", 74: "j", 75: "k", 76: "l",
    77: "m", 78: "n", 79: "o", 80: "p", 81: "q", 82: "r",
    83: "s", 84: "t", 85: "u", 86: "v", 87: "w", 88: "x",
    89: "y", 90: "z",
    97: "a", 98: "b", 99: "c", 100: "d", 101: "e", 102: "f",
    103: "g", 104: "h", 105: "i", 106: "j", 107: "k", 108: "l",
    109: "m", 110: "n", 111: "o", 112: "p", 113: "q", 114: "r",
    115: "s", 116: "t", 117: "u", 118: "v", 119: "w",
    120: "x", 121: "y", 122: "z",
    16: "capslock", 9: "tab", 27: "esc", 28: "enter", 32: "space",
    160: "left shift", 161: "right shift",
    162: "left ctrl", 163: "right ctrl",
    164: "left alt", 165: "right alt",
    256: "left alt", 257: "ctrl", 258: "shift",
    259: "left ctrl", 260: "right ctrl",
    283: "backspace", 13: "enter",
}


def _normalize_key(k: str) -> str:
    k = k.lower().strip()
    if k in ("left alt", "right alt", "alt"):
        return "alt"
    if k in ("left ctrl", "right ctrl", "ctrl"):
        return "ctrl"
    if k in ("left shift", "right shift", "shift"):
        return "shift"
    return k


def vk_to_name(vk_code: int) -> str | None:
    return VK_MAP.get(vk_code, None)


def _find_key_file(d2r_path: str, char_name: str) -> str | None:
    candidates = []
    saved_games = os.path.expanduser("~/Saved Games/Diablo II Resurrected")
    for ext in ("keyo", "key"):
        candidates.append(os.path.join(saved_games, f"{char_name}.{ext}"))
    if os.path.isdir(saved_games):
        try:
            for f in sorted(os.listdir(saved_games)):
                if f.endswith(".keyo") or f.endswith(".key"):
                    candidates.append(os.path.join(saved_games, f))
        except OSError:
            pass
    for ext in ("keyo", "key"):
        candidates.append(os.path.join(d2r_path, "keybinds", f"{char_name}.{ext}"))
        candidates.append(os.path.join(d2r_path, f"{char_name}.{ext}"))
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        for sub in ("keybinds", "d2r_data/char"):
            for ext in ("keyo", "key"):
                candidates.append(
                    os.path.join(appdata, "Diablo II Resurrected", sub, f"{char_name}.{ext}")
                )
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _parse_binary(filepath: str) -> tuple:
    """Returns (skills_dict, non_skill_keys_list)."""
    skills = {}
    non_skill_keys = []

    with open(filepath, "rb") as f:
        data = f.read()
    if len(data) < 14:
        return skills, non_skill_keys

    entry_size = 10
    n_entries = (len(data) - 4) // entry_size

    for i in range(n_entries):
        offset = 4 + i * entry_size
        _pad, vk, action, _pad2, slot = struct.unpack_from("<5H", data, offset)
        if vk == 0xFFFF:
            continue
        key_name = vk_to_name(vk)
        if key_name is None:
            continue
        if action == 1:
            skills[slot] = key_name
        elif action == 0:
            non_skill_keys.append(key_name)

    return skills, non_skill_keys


def apply_key_bindings(config_instance) -> None:
    d2r_path = config_instance.general.get("d2r_path", "")
    char_name = config_instance.general.get("name", "")
    if not char_name:
        return

    key_file = _find_key_file(d2r_path, char_name)
    if key_file is None:
        Logger.info(f"Key file not found for '{char_name}'. Set hotkeys in params.ini.")
        return

    Logger.info(f"Reading key bindings from: {key_file}")
    skills, non_skill_keys = _parse_binary(key_file)

    if skills:
        Logger.info(f"Skill slots: {skills}")
    if non_skill_keys:
        Logger.info(f"Non-skill keys: {non_skill_keys}")

    # Validate: check if configured skill hotkeys match game bindings
    char_type = config_instance.char.get("type", "")
    section_cfg = getattr(config_instance, char_type, None)
    if section_cfg:
        configured = {_normalize_key(h) for k, h in section_cfg.items() if h}
        detected = {_normalize_key(v) for v in skills.values()}
        for key in configured:
            if key not in detected and key in {_normalize_key(k) for k in non_skill_keys}:
                Logger.warning(
                    f"Hotkey '{key}' is configured as a skill but the game has it "
                    f"as a non-skill binding."
                )

    Logger.info("Key auto-detection complete.")
