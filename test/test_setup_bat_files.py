"""Test that launcher bat files are well-formed and portable.

Checks:
  1. All expected .bat files exist
  2. No hardcoded usernames or absolute paths (except conda paths)
  3. find_python.bat is referenced by run_*.bat
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED_BATS = [
    "install.bat",
    "find_python.bat",
    "run_botty.bat",
    "run_asset_extractor.bat",
    "run_quest_debug.bat",
]

USERNAMES_TO_BLOCK = ["alex", "alexpolo", "ultimate"]


def _read(name):
    return open(os.path.join(ROOT, name)).read()


def _bat_exists(name):
    assert os.path.isfile(os.path.join(ROOT, name)), f"{name} is missing from repo root"


class TestBatFilesExist:
    def test_all_bats_present(self):
        for name in EXPECTED_BATS:
            _bat_exists(name)


class TestNoHardcodedUsernames:
    """run_*.bat and find_python.bat must never contain a real username."""

    _CHECKED = [
        "find_python.bat",
        "run_botty.bat",
        "run_asset_extractor.bat",
        "run_quest_debug.bat",
    ]

    def test_no_hardcoded_usernames(self):
        for name in self._CHECKED:
            content = _read(name).lower()
            for uname in USERNAMES_TO_BLOCK:
                for line in content.split("\n"):
                    stripped = line.strip().lstrip(":").lstrip("*")
                    if uname in stripped and not stripped.startswith(":"):
                        raise AssertionError(
                            f"{name} contains hardcoded username '{uname}' on: "
                            f"{line.strip()}"
                        )

    def test_no_absolute_home_paths(self):
        for name in self._CHECKED:
            content = _read(name)
            # Find C:\Users\ followed by a literal username (not %USERNAME%)
            bad = re.findall(r"C:\\Users\\([^%\s]+)", content)
            bad = [b for b in bad if b != "%USERNAME%"]
            assert not bad, f"{name} has hardcoded home path(s): {bad}"


class TestFindPythonUsage:
    """All run_*.bat should source find_python.bat."""

    _RUN_BATS = [
        "run_botty.bat",
        "run_asset_extractor.bat",
        "run_quest_debug.bat",
    ]

    def test_run_bats_call_find_python(self):
        for name in self._RUN_BATS:
            content = _read(name)
            assert "find_python.bat" in content, (
                f"{name} does not call find_python.bat -- "
                f"source the shared helper instead of duplicating conda detection"
            )

    def test_find_python_has_conda_locations(self):
        content = _read("find_python.bat")
        location_count = (
            content.count("miniforge3")
            + content.count("miniconda3")
            + content.count("anaconda3")
        )
        assert location_count >= 6, (
            f"find_python.bat only checks {location_count} conda locations, "
            f"expected >= 6"
        )


class TestInstallBat:
    def test_conda_self_test(self):
        content = _read("install.bat")
        has_test = any(
            kw in content
            for kw in ["--version", "conda test", "testing conda", "test conda"]
        )
        assert has_test, (
            "install.bat should verify conda works before creating the env"
        )

    def test_verifies_python_after_env_create(self):
        content = _read("install.bat")
        assert "python.exe" in content, (
            "install.bat should verify botty env python.exe exists after env create"
        )
