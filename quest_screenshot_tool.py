"""
Quest screenshot capture tool.
Guides you through capturing specific game screens needed for building
the quest system.

Usage:
    1. Launch D2R, create/select your character
    2. Run: python quest_screenshot_tool.py
    3. Follow the prompts

Screenshots saved to screenshots/quest/
"""

import os
import sys
import time
import numpy as np
import cv2
from datetime import datetime

# Fix tesserocr DLL loading
if sys.platform == "win32":
    _conda_dll_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conda_env", "Library", "bin")
    if not os.path.isdir(_conda_dll_dir):
        _conda_dll_dir = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Library", "bin")
    if os.path.isdir(_conda_dll_dir):
        os.add_dll_directory(_conda_dll_dir)

from screen import find_and_set_window_position, get_offset_state, grab as screen_grab

QUEST_DIR = "screenshots/quest"
os.makedirs(QUEST_DIR, exist_ok=True)


def capture():
    """Capture the D2R window using botty's grab()."""
    find_and_set_window_position()
    if not get_offset_state():
        print("[ERROR] Could not find D2R window. Is D2R running and visible?")
        return None
    return screen_grab(force_new=True)


def save(img, name):
    """Save with timestamp prefix."""
    ts = datetime.now().strftime("%H%M%S")
    path = os.path.join(QUEST_DIR, f"{ts}_{name}.png")
    cv2.imwrite(path, img)
    abs_path = os.path.abspath(path)
    print(f"  Saved: {abs_path}")
    return abs_path


STEPS = [
    {
        "name": "act1_town_overview",
        "instructions": (
            "\nSTEP 1: Act 1 Town Overview\n"
            "----------------------------------------\n"
            "1. Stand in the middle of Act 1 town (New Tristram)\n"
            "2. Make sure NO menus are open (close inventory, skills, etc.)\n"
            "3. Position your character so all NPCs are visible\n"
            "Press ENTER when the screen shows the full town...\n"
        ),
    },
    {
        "name": "akara_dialogue_first",
        "instructions": (
            "\nSTEP 2: Akara - First Dialogue Screen\n"
            "----------------------------------------\n"
            "1. Walk up to Akara and LEFT-CLICK her\n"
            "2. The dialogue box should appear with options\n"
            "3. DO NOT click any option - just show this screen\n"
            "Press ENTER when the first dialogue is visible...\n"
        ),
    },
    {
        "name": "akara_dialogue_second",
        "instructions": (
            "\nSTEP 3: Akara - Second Dialogue Screen\n"
            "----------------------------------------\n"
            "1. Click the FIRST dialogue option (usually the quest-related one)\n"
            "2. The next set of options should appear\n"
            "3. This shows the quest dialogue choices\n"
            "4. DO NOT click any option - just show this screen\n"
            "Press ENTER when the second dialogue is visible...\n"
        ),
    },
    {
        "name": "akara_quest_given",
        "instructions": (
            "\nSTEP 4: Quest Given Notification\n"
            "----------------------------------------\n"
            "1. Click the quest-related option to accept the quest\n"
            "2. After the dialogue completes, press ESC to close it\n"
            "3. Show the screen with the quest notification/text\n"
            "   (a message should appear on screen about the quest)\n"
            "Press ENTER when you see the quest notification...\n"
        ),
    },
    {
        "name": "quest_log_open",
        "instructions": (
            "\nSTEP 5: Quest Log\n"
            "----------------------------------------\n"
            "1. Press 'O' to open the Quest Log\n"
            "2. The quest log panel should be visible\n"
            "3. Show the full quest log\n"
            "Press ENTER when the quest log is open...\n"
        ),
    },
    {
        "name": "charsi_dialogue",
        "instructions": (
            "\nSTEP 6: Charsi NPC Dialogue\n"
            "----------------------------------------\n"
            "1. Walk up to Charsi\n"
            "2. LEFT-CLICK her to open dialogue\n"
            "3. Show the first dialogue screen\n"
            "Press ENTER when Charsi's dialogue is open...\n"
        ),
    },
    {
        "name": "kashya_dialogue",
        "instructions": (
            "\nSTEP 7: Kashya NPC Dialogue\n"
            "----------------------------------------\n"
            "1. Walk up to Kashya (the skill teacher)\n"
            "2. LEFT-CLICK her to open dialogue\n"
            "3. Show the first dialogue screen\n"
            "Press ENTER when Kashya's dialogue is open...\n"
        ),
    },
    {
        "name": "sewer_entrance",
        "instructions": (
            "\nSTEP 8: Sewer / Rat Area Entrance\n"
            "----------------------------------------\n"
            "1. Go to the sewer entrance (south of town)\n"
            "2. Stand near the entrance looking into the rat area\n"
            "3. This is for the first quest (kill rats)\n"
            "Press ENTER when you can see the rat area...\n"
        ),
    },
    {
        "name": "item_on_ground",
        "instructions": (
            "\nSTEP 9: Item on the Ground\n"
            "----------------------------------------\n"
            "1. Kill some rats in the sewer\n"
            "2. If a quest item drops (gold glow), show it on the ground\n"
            "3. If no quest item drops, show ANY item on the ground\n"
            "4. The item name tooltip should be visible\n"
            "Press ENTER when an item is visible on the ground...\n"
        ),
    },
    {
        "name": "inventory_with_item",
        "instructions": (
            "\nSTEP 10: Inventory with Item Tooltip\n"
            "----------------------------------------\n"
            "1. Pick up the item\n"
            "2. Press 'I' to open inventory\n"
            "3. Hover over the item to show its tooltip\n"
            "4. Show the tooltip with the item name visible\n"
            "Press ENTER when the item tooltip is visible...\n"
        ),
    },
    {
        "name": "dialogue_box_full",
        "instructions": (
            "\nSTEP 11: Full Dialogue Box (Any NPC)\n"
            "----------------------------------------\n"
            "1. Talk to ANY NPC\n"
            "2. Get to a screen with 3+ dialogue options\n"
            "3. Show the full dialogue box with all options visible\n"
            "4. This helps us measure the dialogue button positions\n"
            "Press ENTER when a dialogue with multiple options is visible...\n"
        ),
    },
    {
        "name": "game_start_menu",
        "instructions": (
            "\nSTEP 12: Game Start / Difficulty Selection\n"
            "----------------------------------------\n"
            "1. Save & Exit to return to hero selection\n"
            "2. Click Play (or let botty do it)\n"
            "3. Show the difficulty selection screen\n"
            "   (Normal/Nightmare/Hell buttons)\n"
            "Press ENTER when the difficulty screen is visible...\n"
        ),
    },
]


def run():
    print("=" * 60)
    print("  Botty Quest Screenshot Tool")
    print("=" * 60)
    print()
    print("Make sure D2R is running and visible on screen.")
    print("You'll be guided through capturing each needed screen.")
    print()
    print("Press ENTER to start...")
    input()

    captured = []
    failed = []

    for i, step in enumerate(STEPS, 1):
        print()
        print(step["instructions"])

        try:
            input()  # wait for user
            img = capture()
            if img is not None:
                path = save(img, step["name"])
                captured.append((step["name"], path))
                print(f"  [OK] {step['name']}")
            else:
                print(f"  [FAIL] Could not capture for {step['name']}")
                failed.append(step["name"])
        except KeyboardInterrupt:
            print("\n[STOPPED]")
            break

    # Summary
    print()
    print("=" * 60)
    print("  Capture Summary")
    print("=" * 60)
    print(f"  Captured: {len(captured)}/{len(STEPS)}")
    for name, path in captured:
        print(f"    [OK]  {name}")
    if failed:
        print(f"  Failed: {len(failed)}")
        for name in failed:
            print(f"    [XX]  {name}")
    print()
    print(f"All screenshots in: {os.path.abspath(QUEST_DIR)}")
    print()


if __name__ == "__main__":
    run()
