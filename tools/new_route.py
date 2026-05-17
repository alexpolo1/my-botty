#!/usr/bin/env python3
"""Scaffold a new farming route for botty.

Usage:
    python3 tools/new_route.py --name baal --display "Baal" --act 5
    python3 tools/new_route.py --name baal --display "Baal" --act 5 --dry-run
    python3 tools/new_route.py --undo baal
"""

import argparse
import difflib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from _codemod import apply_all, undo_all


def to_pascal_case(name):
    return "".join(word.capitalize() for word in name.split("_"))


def validate_name(name):
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        return "Name must be snake_case (e.g. 'baal', 'hellforge')"
    if (PROJECT_DIR / "src/run" / f"{name}.py").exists():
        return f"src/run/{name}.py already exists"
    init_text = (PROJECT_DIR / "src/run/__init__.py").read_text()
    if f"from .{name} import" in init_text:
        return f"Route '{name}' already wired in src/run/__init__.py"
    return None


def render_template(name, class_name, display, act, location_id):
    tmpl = (SCRIPT_DIR / "templates" / "run_template.py.j2").read_text()
    loc_str = location_id if location_id else "None  # TODO"
    for old, new in [
        ("{{name}}", name), ("{{ name }}", name),
        ("{{class_name}}", class_name), ("{{ class_name }}", class_name),
        ("{{display}}", display), ("{{ display }}", display),
        ("{{act}}", str(act)), ("{{ act }}", str(act)),
        ("{{location_id}}", loc_str), ("{{ location_id }}", loc_str),
    ]:
        tmpl = tmpl.replace(old, new)
    return tmpl


def show_diff(old, new, label):
    for line in difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"{label} (before)",
        tofile=f"{label} (after)",
        lineterm="\n",
    ):
        sys.stdout.write(line)


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new farming route for botty",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 tools/new_route.py --name baal --display Baal --act 5\n"
            "  python3 tools/new_route.py --name hellforge --act 2 --location-id A2_HELLFORGE\n"
            "  python3 tools/new_route.py --name smoketest --act 1 --dry-run\n"
            "  python3 tools/new_route.py --undo baal\n"
        ),
    )
    parser.add_argument("--name", help="Route slug (snake_case)")
    parser.add_argument("--display", default=None, help="Logger label (default: titlecased name)")
    parser.add_argument("--act", type=int, choices=[1, 2, 3, 4, 5], default=1, help="Town manager act")
    parser.add_argument("--location-id", default=None, help="Location.* constant")
    parser.add_argument("--class-name", default=None, help="Python class name (default: PascalCase)")
    parser.add_argument("--dry-run", action="store_true", help="Show diff, don't write")
    parser.add_argument("--undo", metavar="NAME", help="Reverse a scaffolded route")

    args = parser.parse_args()

    # ── Undo mode ────────────────────────────────────────────────────
    if args.undo:
        name = args.undo
        if not (PROJECT_DIR / "src/run/__init__.py").exists():
            print("ERROR: src/run/__init__.py not found")
            sys.exit(1)
        actions = undo_all(str(PROJECT_DIR), name)
        if actions:
            run_file = PROJECT_DIR / "src/run" / f"{name}.py"
            if run_file.exists():
                run_file.unlink()
                actions.append(f"removed src/run/{name}.py")
            print(f"Undid route '{name}': {', '.join(actions)}")
        else:
            print(f"Nothing to undo for '{name}'")
        return

    # ── Scaffold mode ────────────────────────────────────────────────
    if not args.name:
        parser.error("--name is required (or use --undo)")

    name = args.name
    err = validate_name(name)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    class_name = args.class_name or to_pascal_case(name)
    display = args.display if args.display else name.replace("_", " ").title()

    # ── Dry run ──────────────────────────────────────────────────────
    if args.dry_run:
        print(f"=== DRY RUN: scaffold route '{name}' ===\n")

        # Show new run file
        run_content = render_template(name, class_name, display, args.act, args.location_id)
        print("--- NEW: src/run/" + name + ".py ---")
        print(run_content)

        # Copy src dir to tmpdir and apply mutations there
        tmpdir = tempfile.mkdtemp()
        try:
            # Replicate the src/ structure
            src_dst = os.path.join(tmpdir, "src")
            shutil.copytree(str(PROJECT_DIR / "src"), src_dst, dirs_exist_ok=True)

            apply_all(tmpdir, name, class_name, display, args.act, args.location_id)

            # Show diffs
            bot_orig = (PROJECT_DIR / "src/bot.py").read_text()
            show_diff(bot_orig, Path(os.path.join(src_dst, "bot.py")).read_text(), "src/bot.py")

            init_orig = (PROJECT_DIR / "src/run/__init__.py").read_text()
            show_diff(init_orig, Path(os.path.join(src_dst, "run/__init__.py")).read_text(), "src/run/__init__.py")
        finally:
            shutil.rmtree(tmpdir)

        print("\n(Dry run complete. Re-run without --dry-run to apply.)")
        return

    # ── Write everything ─────────────────────────────────────────────
    run_content = render_template(name, class_name, display, args.act, args.location_id)
    (PROJECT_DIR / "src/run" / f"{name}.py").write_text(run_content)
    print(f"Created: src/run/{name}.py")

    actions = apply_all(str(PROJECT_DIR), name, class_name, display, args.act, args.location_id)
    print(f"Mutated bot.py: {', '.join(actions)}")

    print(f"\nDone! Route '{name}' scaffolded.")
    print(f"  - Edit src/run/{name}.py to implement approach() and battle()")
    print(f"  - Add 'run_{name}' to [routes] order= in config/params.ini")
    print(f"  - Verify: python3 -m py_compile src/bot.py")


if __name__ == "__main__":
    main()
