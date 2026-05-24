from dataclasses import dataclass

from config import Config
from input_layer import keyboard
from logger import Logger
from screen import grab
import template_finder
from utils.key_detector import _normalize_key
from utils.misc import wait


@dataclass(frozen=True)
class SkillCheck:
    build: str
    skill: str
    hotkey: str
    template: str
    side: str
    required: bool


SORC_TEMPLATE_ALIASES = {
    "blizzard": ("BLIZZARD",),
    "ice_blast": ("ICE_BLAST", "ICEBLAST"),
    "static_field": ("STATIC_FIELD", "STATICFIELD"),
    "frozen_armor": ("FROZEN_ARMOR", "FROZENARMOR"),
    "energy_shield": ("ENERGY_SHIELD", "ENERGYSHIELD"),
    "telekinesis": ("TELEKINESIS",),
    "thunder_storm": ("THUNDER_STORM", "THUNDERSTORM"),
}


def _configured_hotkey(section: dict, skill: str) -> str:
    return _normalize_key(str(section.get(skill, "")))


def _first_existing_template(template_names: tuple[str, ...]) -> str | None:
    templates = template_finder.stored_templates()
    for template_name in template_names:
        if template_name in templates:
            return template_name
    return None


def get_build_skill_checks(config_instance: Config, char_type: str | None = None) -> list[SkillCheck]:
    char_type = char_type or config_instance.char.get("type", "")
    checks = []

    if char_type != "blizz_sorc":
        return checks

    build_cfg = getattr(config_instance, "blizz_sorc", {})
    blizzard_key = _configured_hotkey(build_cfg, "blizzard")
    checks.append(SkillCheck(char_type, "blizzard", blizzard_key, "BLIZZARD", "right", True))

    optional_skills = {
        "ice_blast": (build_cfg, "right"),
        "static_field": (build_cfg, "right"),
        "frozen_armor": (build_cfg, "right"),
        "energy_shield": (build_cfg, "right"),
        "telekinesis": (build_cfg, "right"),
        "thunder_storm": (build_cfg, "right"),
    }
    for skill, (section, side) in optional_skills.items():
        hotkey = _configured_hotkey(section, skill)
        if hotkey:
            template = SORC_TEMPLATE_ALIASES[skill][0]
            checks.append(SkillCheck(char_type, skill, hotkey, template, side, False))
    return checks


def _skill_roi(side: str, pad: int = 6) -> list[int]:
    x, y, w, h = Config().ui_roi["skill_left" if side == "left" else "skill_right"]
    return [max(0, x - pad), max(0, y - pad), w + pad * 2, h + pad * 2]


def _check_skill_icon(check: SkillCheck, threshold: float = 0.84) -> tuple[bool | None, str, float]:
    template_name = _first_existing_template(SORC_TEMPLATE_ALIASES.get(check.skill, (check.template,)))
    if template_name is None:
        return None, check.template, -1.0

    keyboard.send(check.hotkey)
    wait(0.15, 0.25)
    roi = _skill_roi(check.side)
    match = template_finder.search(template_name, grab(force_new=True), threshold=threshold, roi=roi)
    return match.valid, template_name, match.score


def _close_skill_picker_if_open() -> None:
    if "BIND_SKILL" not in template_finder.stored_templates():
        return
    if template_finder.search(
        "BIND_SKILL",
        grab(force_new=True),
        threshold=0.8,
        roi=Config().ui_roi["bind_skill"],
        use_grayscale=True,
    ).valid:
        keyboard.send("s")
        wait(0.20, 0.30)


def validate_build_skill_icons(config_instance: Config, char_type: str | None = None) -> bool:
    char_type = char_type or config_instance.char.get("type", "")
    checks = get_build_skill_checks(config_instance, char_type)
    if not checks:
        Logger.debug(f"Skill visual preflight skipped: no build rules for {char_type!r}")
        return True

    Logger.info(
        "Skill visual preflight: "
        f"character={config_instance.general.get('char_name') or config_instance.general.get('name')}, "
        f"build={char_type}"
    )
    _close_skill_picker_if_open()

    errors = []
    for check in checks:
        if not check.hotkey:
            if check.required:
                errors.append(f"{check.skill} has no configured hotkey")
            continue

        matched, template_name, score = _check_skill_icon(check)
        if matched is None:
            Logger.warning(
                "Skill visual preflight: "
                f"{check.skill} key={check.hotkey} side={check.side} template={template_name} missing; "
                "skipping visual match"
            )
            continue

        score_text = f"{score * 100:.1f}%" if score >= 0 else "n/a"
        status = "ok" if matched else "failed"
        Logger.info(
            "Skill visual preflight: "
            f"{check.skill} key={check.hotkey} side={check.side} template={template_name} "
            f"visual={status} score={score_text}"
        )
        if not matched:
            severity = "required" if check.required else "configured"
            errors.append(
                f"{severity} skill {check.skill} did not select {template_name} "
                f"on {check.side} skill icon (key={check.hotkey}, score={score_text})"
            )

    for error in errors:
        Logger.error(f"Skill visual preflight: {error}")
    if errors:
        Logger.error("Skill visual preflight failed. Fix D2R skill hotkeys or recapture templates before running.")
        return False

    Logger.info("Skill visual preflight passed.")
    return True
