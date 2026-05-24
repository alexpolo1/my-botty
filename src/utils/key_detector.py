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
    96: "numpad0", 97: "numpad1", 98: "numpad2", 99: "numpad3",
    100: "numpad4", 101: "numpad5", 102: "numpad6", 103: "numpad7",
    104: "numpad8", 105: "numpad9", 106: "numpad*", 107: "numpad+",
    109: "numpad-", 110: "numpad.", 111: "numpad/",
    112: "f1", 113: "f2", 114: "f3", 115: "f4", 116: "f5",
    117: "f6", 118: "f7", 119: "f8", 120: "f9", 121: "f10",
    122: "f11", 123: "f12",
    186: ";", 187: "=", 188: ",", 189: "-", 190: ".", 191: "/",
    192: "`", 219: "[", 220: "\\", 221: "]", 222: "'",
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


def _try_fill(cfg: dict, key: str, detected: str) -> None:
    current = _normalize_key(str(cfg.get(key, "")))
    detected = _normalize_key(str(detected))
    if not current:
        cfg[key] = detected


def _auto_fill_char(char_cfg: dict, bindings: dict) -> None:
    key_map = {
        "inventory": "inventory_screen",
        "inventory_screen": "inventory_screen",
        "show_items": "show_items",
        "stand_still": "stand_still",
        "show_belt": "show_belt",
        "force_move": "force_move",
        "potion1": "potion1",
        "potion2": "potion2",
        "potion3": "potion3",
        "potion4": "potion4",
    }
    for detected_key, config_key in key_map.items():
        if detected_key in bindings:
            _try_fill(char_cfg, config_key, bindings[detected_key])


def vk_to_name(vk_code: int) -> str | None:
    return VK_MAP.get(vk_code, None)


def parse_key_file(filepath: str) -> dict:
    """Compatibility parser used by debug tooling and tests."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        if lines and lines[0].isdigit():
            bindings = {}
            for line in lines[1:]:
                vk_str, action_str, param_str = line.split()[:3]
                key_name = vk_to_name(int(vk_str))
                if key_name is None:
                    continue
                action = int(action_str)
                param = int(param_str)
                if action == 1:
                    bindings[f"skill{param}"] = key_name
                elif action == 2:
                    bindings["inventory"] = _normalize_key(key_name)
                elif action == 3:
                    bindings["show_items"] = _normalize_key(key_name)
                elif action == 4:
                    bindings["stand_still"] = _normalize_key(key_name)
                elif action == 5:
                    bindings["show_belt"] = _normalize_key(key_name)
                elif action == 6 and 1 <= param <= 4:
                    bindings[f"potion{param}"] = key_name
                elif action == 13:
                    bindings["force_move"] = key_name
            return bindings
    except UnicodeDecodeError:
        pass

    skills, _non_skill_keys, char_bindings = _parse_binary(filepath)
    bindings = dict(char_bindings)
    if "inventory_screen" in bindings:
        bindings["inventory"] = bindings["inventory_screen"]
    for slot, key_name in skills.items():
        bindings[f"skill{slot}"] = key_name
    return bindings


def _find_key_file(d2r_path: str, char_name: str) -> str | None:
    candidates = []
    saved_games = os.path.expanduser("~/Saved Games/Diablo II Resurrected")
    char_name = (char_name or "").strip()
    for ext in ("keyo", "key"):
        candidates.append(os.path.join(saved_games, f"{char_name}.{ext}"))
    if os.path.isdir(saved_games):
        try:
            key_files = [f for f in sorted(os.listdir(saved_games)) if f.lower().endswith((".keyo", ".key"))]
            if char_name:
                normalized_char = "".join(ch for ch in char_name.lower() if ch.isalnum())
                for f in key_files:
                    normalized_file = "".join(ch for ch in os.path.splitext(f)[0].lower() if ch.isalnum())
                    if normalized_file.startswith(normalized_char):
                        candidates.append(os.path.join(saved_games, f))
            for f in key_files:
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


CHAR_BINDING_SLOTS = {
    1: "inventory_screen",
    8: "show_items",
    23: "potion1",
    24: "potion2",
    25: "potion3",
    26: "potion4",
    36: "stand_still",
    41: "show_belt",
    44: "weapon_switch",
    59: "force_move",
}


def _parse_binary(filepath: str) -> tuple:
    """Returns (skills_dict, non_skill_keys_list, char_bindings_dict)."""
    skills = {}
    non_skill_keys = []
    char_bindings = {}

    with open(filepath, "rb") as f:
        data = f.read()
    if len(data) < 14:
        return skills, non_skill_keys, char_bindings

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
        if slot in CHAR_BINDING_SLOTS:
            config_key = CHAR_BINDING_SLOTS[slot]
            normalized = _normalize_key(key_name)
            if (
                config_key not in char_bindings
                or (config_key == "show_items" and action == 0)
                or (config_key != "show_items" and action == 1)
            ):
                char_bindings[config_key] = normalized
        if action == 1:
            skills[slot] = key_name
        elif action == 0:
            non_skill_keys.append(key_name)

    return skills, non_skill_keys, char_bindings


def _apply_char_bindings(char_cfg: dict, bindings: dict) -> None:
    for config_key, detected_key in bindings.items():
        current_key = _normalize_key(str(char_cfg.get(config_key, "")))
        if not current_key:
            Logger.info(
                f"Using detected key binding for {config_key}: "
                f"{char_cfg.get(config_key, '')!r} -> {detected_key!r}"
            )
            char_cfg[config_key] = detected_key
        elif current_key != detected_key:
            Logger.debug(
                f"Keeping configured key binding for {config_key}: "
                f"{current_key!r} (detected {detected_key!r})"
            )


def apply_key_bindings(config_instance) -> None:
    d2r_path = config_instance.general.get("d2r_path", "")
    char_name = config_instance.general.get("char_name") or config_instance.general.get("name", "")
    if not char_name:
        return

    key_file = _find_key_file(d2r_path, char_name)
    if key_file is None:
        Logger.info(f"Key file not found for '{char_name}'. Set hotkeys in params.ini.")
        return

    Logger.info(f"Reading key bindings from: {key_file}")
    skills, non_skill_keys, char_bindings = _parse_binary(key_file)

    if skills:
        Logger.info(f"Skill slots: {skills}")
    if non_skill_keys:
        Logger.info(f"Non-skill keys: {non_skill_keys}")
    if char_bindings:
        Logger.info(f"Detected character key bindings: {char_bindings}")
        _apply_char_bindings(config_instance.char, char_bindings)

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


def validate_key_bindings(config_instance, routes=None) -> bool:
    d2r_path = config_instance.general.get("d2r_path", "")
    char_name = config_instance.general.get("char_name") or config_instance.general.get("name", "")
    key_file = _find_key_file(d2r_path, char_name)
    if key_file is None:
        Logger.error(f"Key preflight failed: no D2R key file found for '{char_name}'. Set [general] char_name.")
        return False

    skills, non_skill_keys, char_bindings = _parse_binary(key_file)
    detected_skill_keys = {_normalize_key(v) for v in skills.values()}
    detected_non_skill_keys = {_normalize_key(v) for v in non_skill_keys}
    configured_char_keys = {
        key: _normalize_key(str(config_instance.char.get(key, "")))
        for key in (
            "force_move", "show_items", "show_belt", "stand_still",
            "potion1", "potion2", "potion3", "potion4", "town_portal", "teleport",
            "weapon_switch", "battle_command", "battle_orders",
        )
    }
    Logger.info(f"Key preflight using: {key_file}")
    Logger.info(f"Detected skill hotkeys: {sorted(detected_skill_keys)}")
    Logger.info(f"Detected character key bindings: {char_bindings}")

    errors = []
    warnings = []
    for key in ("force_move", "show_items", "show_belt", "stand_still", "potion1", "potion2", "potion3", "potion4", "town_portal"):
        if not configured_char_keys[key]:
            errors.append(f"[char] {key} is empty")

    char_type = config_instance.char.get("type", "")
    required_build_skills = {
        "blizz_sorc": ("blizzard",),
        "blizzorb_sorc": ("blizzard", "glacial_spike"),
        "nova_sorc": ("nova",),
        "hydra_sorc": ("hydra", "alt_attack"),
        "light_sorc": ("lightning",),
    }
    section_cfg = getattr(config_instance, char_type, None)
    if section_cfg:
        for skill in required_build_skills.get(char_type, ()):
            hotkey = _normalize_key(str(section_cfg.get(skill, "")))
            if not hotkey:
                errors.append(f"[{char_type}] {skill} is empty")
            elif hotkey not in detected_skill_keys:
                errors.append(f"[{char_type}] {skill}={hotkey!r} is not bound as a skill in {os.path.basename(key_file)}")
        for skill, hotkey in section_cfg.items():
            hotkey = _normalize_key(str(hotkey))
            if hotkey and hotkey in detected_non_skill_keys:
                errors.append(f"[{char_type}] {skill}={hotkey!r} is detected as a non-skill key")

    if config_instance.char.get("cta_available"):
        missing_cta = [
            key for key in ("battle_command", "battle_orders")
            if configured_char_keys[key] and configured_char_keys[key] not in detected_skill_keys
        ]
        if missing_cta:
            warnings.append(
                "CTA is enabled but these CTA skill hotkeys are not detected as skill keys: "
                + ", ".join(missing_cta)
                + ". Disabling CTA for this session."
            )
            config_instance.char["cta_available"] = False

    for warning in warnings:
        Logger.warning(f"Key preflight: {warning}")
    for error in errors:
        Logger.error(f"Key preflight: {error}")
    if errors:
        Logger.error("Key preflight failed. Fix D2R key bindings or config before running.")
        return False
    Logger.info("Key preflight passed.")
    return True
