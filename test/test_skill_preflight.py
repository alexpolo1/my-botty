import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.skill_preflight import get_build_skill_checks


class DummyConfig:
    char = {"type": "blizz_sorc"}
    blizz_sorc = {
        "blizzard": "f1",
        "ice_blast": "",
        "energy_shield": "f3",
        "frozen_armor": "f4",
        "static_field": "f5",
        "telekinesis": "f6",
        "thunder_storm": "",
    }


def test_blizz_sorc_skill_checks():
    checks = get_build_skill_checks(DummyConfig())
    by_skill = {check.skill: check for check in checks}

    assert by_skill["blizzard"].required is True
    assert by_skill["blizzard"].side == "right"
    assert by_skill["blizzard"].hotkey == "f1"

    assert "ice_blast" not in by_skill
    assert by_skill["energy_shield"].required is False
    assert by_skill["frozen_armor"].side == "right"
    assert by_skill["static_field"].hotkey == "f5"
    assert by_skill["telekinesis"].hotkey == "f6"


def test_blizz_sorc_optional_attack_is_right_skill():
    config = DummyConfig()
    config.blizz_sorc = dict(DummyConfig.blizz_sorc)
    config.blizz_sorc["ice_blast"] = "f2"

    by_skill = {check.skill: check for check in get_build_skill_checks(config)}

    assert by_skill["ice_blast"].side == "right"


def test_unknown_build_has_no_checks():
    assert get_build_skill_checks(DummyConfig(), "hammerdin") == []
