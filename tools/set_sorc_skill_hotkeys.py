#!/usr/bin/env python
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Config
from screen import find_and_set_window_position
from utils.skill_preflight import get_build_skill_checks
from utils.skill_hotkey_setter import bind_build_hotkeys


def main() -> int:
    parser = argparse.ArgumentParser(description="Set configured Sorceress skill hotkeys inside the D2R skill picker.")
    parser.add_argument("--build", default="blizz_sorc", choices=["blizz_sorc"])
    parser.add_argument("--skill", help="Bind only one configured skill, e.g. blizzard or static_field")
    parser.add_argument("--required-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        checks = get_build_skill_checks(Config(), args.build)
        if args.required_only:
            checks = [check for check in checks if check.required]
        if args.skill:
            checks = [check for check in checks if check.skill == args.skill]
        print("Skill hotkey setter dry run:")
        for check in checks:
            print(f"  {check.skill:14s} key={check.hotkey:5s} side={check.side:5s} required={check.required}")
        return 0

    find_and_set_window_position()
    results = bind_build_hotkeys(Config(), args.build, required_only=args.required_only, only_skill=args.skill)
    failed = [result for result in results if not result.bound or not result.verified]
    print("\nSkill hotkey setter report:")
    for result in results:
        status = "OK" if result.bound and result.verified else "FAIL"
        reason = f" ({result.reason})" if result.reason else ""
        print(f"  {status:4s} {result.skill:14s} {result.hotkey:5s} {result.side:5s} {result.template}{reason}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
