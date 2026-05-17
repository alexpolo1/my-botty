#!/usr/bin/env python3
"""Smoke tests for the new_route scaffolding tool."""

import os
import subprocess
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLI = os.path.join(PROJECT, "tools", "new_route.py")
TEST_NAME = "smoketest"
TEST_DISPLAY = "Smoketest"
TEST_ACT = 1


def _git_restore():
    """Reset src/bot.py and src/run/__init__.py to HEAD; remove run file."""
    subprocess.run(["git", "checkout", "src/bot.py", "src/run/__init__.py"],
                   cwd=PROJECT, capture_output=True)
    p = os.path.join(PROJECT, "src", "run", TEST_NAME + ".py")
    if os.path.exists(p):
        os.remove(p)


def _run(args, expect_rc=0):
    r = subprocess.run(["python3", CLI] + args, cwd=PROJECT,
                       capture_output=True, text=True)
    if expect_rc != 0 and r.returncode == 0:
        raise AssertionError(f"Expected failure but got success: {r.stdout}")
    if expect_rc == 0 and r.returncode != 0:
        raise AssertionError(f"Expected success but got rc={r.returncode}: {r.stderr}")
    return r


def _compile_ok():
    r = subprocess.run(["python3", "-m", "py_compile", "src/bot.py"],
                       cwd=PROJECT, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"py_compile failed: {r.stderr}")


def test_scaffold_and_undo():
    """Full cycle: clean -> scaffold -> compile -> undo -> compile."""
    print("\n--- test_scaffold_and_undo ---")
    _git_restore()
    _run(["--name", TEST_NAME, "--display", TEST_DISPLAY, "--act", str(TEST_ACT)])
    _compile_ok()

    assert os.path.exists(os.path.join(PROJECT, "src", "run", TEST_NAME + ".py"))
    with open(os.path.join(PROJECT, "src", "bot.py")) as f:
        bot = f.read()
    assert f"self._{TEST_NAME}" in bot, "Instantiation not found"
    assert f"on_run_{TEST_NAME}" in bot, "Handler not found"

    _run(["--undo", TEST_NAME])
    _compile_ok()

    assert not os.path.exists(os.path.join(PROJECT, "src", "run", TEST_NAME + ".py"))
    with open(os.path.join(PROJECT, "src", "bot.py")) as f:
        bot2 = f.read()
    assert f"self._{TEST_NAME}" not in bot2, "Instantiation still present after undo"
    print("PASS")


def test_idempotency():
    """Second scaffold of same name should be refused."""
    print("\n--- test_idempotency ---")
    _git_restore()
    _run(["--name", TEST_NAME, "--display", TEST_DISPLAY, "--act", str(TEST_ACT)])
    r = _run(["--name", TEST_NAME, "--display", TEST_DISPLAY, "--act", str(TEST_ACT)], expect_rc=1)
    assert "already exists" in r.stderr.lower() or "already" in r.stderr.lower()
    _run(["--undo", TEST_NAME])
    _git_restore()
    print("PASS")


def test_dry_run():
    """Dry run should not modify any files."""
    print("\n--- test_dry_run ---")
    _git_restore()
    bot_before = open(os.path.join(PROJECT, "src", "bot.py")).read()
    _run(["--name", TEST_NAME, "--display", TEST_DISPLAY, "--act", str(TEST_ACT), "--dry-run"])
    bot_after = open(os.path.join(PROJECT, "src", "bot.py")).read()
    assert bot_before == bot_after, "Dry run modified bot.py"
    assert not os.path.exists(os.path.join(PROJECT, "src", "run", TEST_NAME + ".py"))
    print("PASS")


def test_bad_name():
    """Non-snake-case name should be rejected."""
    print("\n--- test_bad_name ---")
    _git_restore()
    _run(["--name", "Bad_Name", "--act", "1"], expect_rc=1)
    print("PASS")


if __name__ == "__main__":
    test_scaffold_and_undo()
    test_idempotency()
    test_dry_run()
    test_bad_name()
    print("\n=== ALL TESTS PASSED ===")
