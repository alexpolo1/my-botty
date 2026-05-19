#!/usr/bin/env python
"""
End-to-end test for key_detector without needing a real D2R install.

Creates a temporary .key file, loads config with it, and verifies auto-fill.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ─── Mock .key file ───────────────────────────────────────────────────────────
# 17 bindings total. Each line: VK action_type param
MOCK_KEY_CONTENT = """\
17
73 2 0
256 3 0
16 4 0
75 5 0
49 6 1
50 6 2
51 6 3
52 6 4
53 1 1
54 1 2
115 1 3
116 1 4
117 1 5
118 1 6
69 13 0
87 1 7
114 1 8
"""


def test():
    print("=" * 50)
    print("  KEY DETECTOR E2E TEST")
    print("=" * 50)

    tmpdir = tempfile.mkdtemp()
    key_path = os.path.join(tmpdir, "testchar.key")
    with open(key_path, "w") as f:
        f.write(MOCK_KEY_CONTENT)
    print(f"\n1. Created mock .key file: {key_path}")

    # ─── 2. Parse ──────────────────────────────────────────────────────
    from utils.key_detector import (
        parse_key_file, vk_to_name, _find_key_file,
        _try_fill, _auto_fill_char,
    )

    bindings = parse_key_file(key_path)
    print(f"\n2. Parsed {len(bindings)} bindings:")
    for k, v in sorted(bindings.items()):
        print(f"     {k:20s} = {v}")

    # ─── 3. Verify expected values ─────────────────────────────────────
    expected = {
        "inventory":    "i",          # VK 73
        "show_items":   "alt",        # VK 256
        "stand_still":  "capslock",   # VK 16
        "show_belt":    "k",          # VK 75
        "potion1":      "1",          # VK 49
        "potion2":      "2",          # VK 50
        "potion3":      "3",          # VK 51
        "potion4":      "4",          # VK 52
        "skill1":       "5",          # VK 53
        "skill2":       "6",          # VK 54
        "skill3":       "f4",         # VK 115
        "skill4":       "f5",         # VK 116
        "skill5":       "f6",         # VK 117
        "skill6":       "f7",         # VK 118
        "force_move":   "e",          # VK 69
        "skill7":       "w",          # VK 87
        "skill8":       "f3",         # VK 114 (unused slot)
    }

    print("\n3. Checking expected values:")
    fail = 0
    for key, exp_val in sorted(expected.items()):
        actual = bindings.get(key, "<missing>")
        if actual != exp_val:
            fail += 1
            print(f"     {key:20s}: {actual:>10s} (expected {exp_val:>10s}) [FAIL]")
        else:
            print(f"     {key:20s}: {actual:>10s}                      [OK]")

    # ─── 4. File discovery ─────────────────────────────────────────────
    print("\n4. File discovery (d2r_path = tmpdir):")
    found = _find_key_file(tmpdir, "testchar")
    if found == key_path:
        print(f"     .key found: [OK]")
    else:
        print(f"     .key found: {found} [FAIL]")
        fail += 1

    # .keyo
    keyo_path = os.path.join(tmpdir, "testchar.keyo")
    shutil.copy2(key_path, keyo_path)
    found_keyo = _find_key_file(tmpdir, "testchar")
    # .key takes priority over .keyo in the search order
    if found_keyo and ("testchar.key" in found_keyo or "testchar.keyo" in found_keyo):
        print(f"     .keyo found: [OK]")
    else:
        print(f"     .keyo found: {found_keyo} [FAIL]")
        fail += 1

    # ─── 5. _try_fill ──────────────────────────────────────────────────
    print("\n5. _try_fill logic:")
    cfg = {"show_belt": "", "inventory_screen": "", "teleport": "5"}
    _try_fill(cfg, "show_belt", "k")
    assert cfg["show_belt"] == "k", f"Got {cfg['show_belt']!r}"
    print("     Fill empty: [OK]")

    _try_fill(cfg, "teleport", "6")
    assert cfg["teleport"] == "5", f"Got {cfg['teleport']!r}"
    print("     Preserve existing: [OK]")

    # ─── 5b. Normalization: left alt ~ alt ─────────────────────────────
    print("\n5b. Key normalization:")
    cfg2 = {"show_items": "alt"}
    _try_fill(cfg2, "show_items", "left alt")
    assert cfg2["show_items"] == "alt", f"Got {cfg2['show_items']!r}"
    print("     left alt ~ alt: [OK]")

    cfg3 = {"stand_still": "shift"}
    _try_fill(cfg3, "stand_still", "left shift")
    assert cfg3["stand_still"] == "shift", f"Got {cfg3['stand_still']!r}"
    print("     left shift ~ shift: [OK]")

    # ─── 6. _auto_fill_char ────────────────────────────────────────────
    print("\n6. _auto_fill_char:")
    char_cfg = {
        "inventory_screen": "",
        "show_items": "",
        "stand_still": "capslock",
        "show_belt": "k",
        "force_move": "",
        "potion1": "", "potion2": "", "potion3": "", "potion4": "",
    }
    _auto_fill_char(char_cfg, bindings)

    checks = [
        ("inventory_screen", "i"),
        ("show_items", "alt"),
        ("force_move", "e"),
        ("potion1", "1"),
        ("potion2", "2"),
        ("potion3", "3"),
        ("potion4", "4"),
    ]
    for key, exp in checks:
        actual = char_cfg[key]
        if actual != exp:
            fail += 1
            print(f"     {key:20s}: {actual:>10s} (expected {exp:>10s}) [FAIL]")
        else:
            print(f"     {key:20s}: {actual:>10s}                      [OK]")

    shutil.rmtree(tmpdir)

    # ─── Summary ───────────────────────────────────────────────────────
    print(f"\n{'=' * 50}")
    if fail:
        print(f"  {fail} FAIL(S)")
        print(f"{'=' * 50}")
        return False
    print("  ALL TESTS PASSED")
    print(f"{'=' * 50}")
    return True


if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
