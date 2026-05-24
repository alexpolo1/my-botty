#!/usr/bin/env python
import argparse
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Config
from input_layer import keyboard
from screen import find_and_set_window_position, grab
import template_finder
from utils.misc import cut_roi, wait
from utils.skill_preflight import get_build_skill_checks


OUTPUT_DIR = os.path.join("assets", "templates", "ui", "skills")


def _target_filename(skill: str) -> str:
    if skill == "frozen_armor":
        return "frozenarmor.png"
    return f"{skill}.png"


def capture_sorc_icons(build: str, overwrite: bool, dry_run: bool) -> int:
    config = Config()
    checks = get_build_skill_checks(config, build)
    if not checks:
        print(f"No capture rules for build {build!r}")
        return 1

    print(f"Character: {config.general.get('char_name') or config.general.get('name')}")
    print(f"Build: {build}")
    for check in checks:
        target = os.path.join(OUTPUT_DIR, _target_filename(check.skill))
        print(f"{check.skill:14s} key={check.hotkey or '<empty>':5s} side={check.side:5s} -> {target}")

    if dry_run:
        return 0

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    find_and_set_window_position()
    for check in checks:
        if not check.hotkey:
            print(f"Skipping {check.skill}: no hotkey configured")
            continue

        target = os.path.join(OUTPUT_DIR, _target_filename(check.skill))
        if os.path.exists(target) and not overwrite:
            print(f"Skipping {check.skill}: {target} exists (use --overwrite)")
            continue

        print(f"Selecting {check.skill} with {check.hotkey}...")
        keyboard.send(check.hotkey)
        wait(0.25, 0.35)
        roi = config.ui_roi["skill_left" if check.side == "left" else "skill_right"]
        icon = cut_roi(grab(force_new=True), roi)
        cv2.imwrite(target, icon)
        print(f"Saved {target}")

    template_finder.stored_templates.cache_clear()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Sorceress skill icon templates from the D2R skill buttons.")
    parser.add_argument("--build", default="blizz_sorc", choices=["blizz_sorc"])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return capture_sorc_icons(args.build, args.overwrite, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
