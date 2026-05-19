#!/usr/bin/env python
"""
Test the key auto-detection module against your actual D2R .key file.

Run from botty conda environment:
    python tools/test_key_detector.py
"""

import os
import sys

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from key_detector import vk_to_name, _find_key_file, parse_key_file
from config import Config

print("=" * 50)
print("  KEY DETECTOR TEST")
print("=" * 50)

from utils.key_detector import vk_to_name, _find_key_file, parse_key_file, apply_key_bindings

# Test 1: VK code mapping
print("1. VK code mapping tests:")
test_cases = {
    73: "i",       # inventory
    75: "k",       # show_belt
    69: "e",       # force_move
    87: "w",       # weapon_switch
    16: "capslock",  # stand_still
    256: "alt",    # show_items
    52: "5",       # teleport
    53: "6",       # town_portal
    116: "f5",     # conviction
    117: "f6",     # foh
    118: "f7",     # holy_bolt
    49: "1",       # potion1
    50: "2",       # potion2
}
ok = 0
fail = 0
for vk, expected in test_cases.items():
    result = vk_to_name(vk)
    status = "OK" if result == expected else "FAIL"
    if status == "FAIL":
        fail += 1
    else:
        ok += 1
    print(f"  VK {vk:3d} -> {result:>10s} (expected {expected:>10s}) [{status}]")
print(f"  Result: {ok} passed, {fail} failed")

# Test 2: Find key file
print("\n2. Finding key file:")
config = Config()
d2r_path = config.general["d2r_path"]
char_name = config.general["name"]
print(f"  D2R path: {d2r_path}")
print(f"  Character: {char_name}")

key_file = _find_key_file(d2r_path, char_name)
if key_file:
    print(f"  FOUND: {key_file}")
else:
    print(f"  NOT FOUND - key file missing for '{char_name}'")
    print("  Checked paths:")
    sg = os.path.expanduser("~/Saved Games/Diablo II Resurrected")
    print(f"    {sg}/*.key*")
    kb = os.path.join(d2r_path, "keybinds")
    print(f"    {kb}/*.key*")
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        print(f"    {appdata}/Diablo II Resurrected/keybinds/*.key*")
        print(f"    {appdata}/Diablo II Resurrected/d2r_data/char/*.key*")
    print("\n  To test, copy a .key file to one of these locations.")

# Test 3: Parse key file if found
if key_file:
    print("\n3. Parsing key file:")
    bindings = parse_key_file(key_file)
    for k, v in sorted(bindings.items()):
        print(f"  {k:20s} = {v}")

# Test 4: Check auto-filled values
print("\n4. Auto-filled config values:")
char_keys = ["inventory_screen", "show_items", "stand_still", "show_belt",
             "force_move", "potion1", "potion2", "potion3", "potion4",
             "teleport", "town_portal"]
for key in char_keys:
    val = config.char.get(key, "")
    print(f"  config.char['{key}'] = '{val}'")

print("\n" + "=" * 50)
print("Done.")
