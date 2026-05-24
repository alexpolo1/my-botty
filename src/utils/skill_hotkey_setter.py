from dataclasses import dataclass

from config import Config
from input_layer import keyboard, mouse
from logger import Logger
from screen import convert_screen_to_monitor, grab
import template_finder
from utils.misc import wait
from utils.skill_preflight import (
    SORC_TEMPLATE_ALIASES,
    SkillCheck,
    _check_skill_icon,
    get_build_skill_checks,
)


MENU_TEMPLATES = ["SAVE_AND_EXIT_NO_HIGHLIGHT", "SAVE_AND_EXIT_HIGHLIGHT"]
PICKER_TEMPLATE_ALIASES = {
    "blizzard": ("PICKER_BLIZZARD", "BLIZZARD"),
    "frozen_armor": ("PICKER_FROZENARMOR", "PICKER_FROZEN_ARMOR", "FROZENARMOR", "FROZEN_ARMOR"),
}


@dataclass(frozen=True)
class SkillBindResult:
    skill: str
    hotkey: str
    side: str
    template: str
    bound: bool
    verified: bool
    reason: str = ""


def _skill_roi(side: str) -> list[int]:
    return Config().ui_roi["skill_left" if side == "left" else "skill_right"]


def _expanded_roi(side: str) -> list[int] | None:
    key = f"skill_{side}_expanded"
    if key in Config().ui_roi:
        return Config().ui_roi[key]
    return Config().ui_roi.get("skill_right_expanded")


def _first_existing_template(check: SkillCheck) -> str | None:
    templates = template_finder.stored_templates()
    template_names = PICKER_TEMPLATE_ALIASES.get(check.skill, SORC_TEMPLATE_ALIASES.get(check.skill, (check.template,)))
    for template_name in template_names:
        if template_name in templates:
            return template_name
    return None


def is_ingame_menu_open() -> bool:
    return template_finder.search(
        MENU_TEMPLATES,
        grab(force_new=True),
        threshold=0.85,
        roi=Config().ui_roi["save_and_exit"],
        best_match=True,
    ).valid


def is_skill_picker_open() -> bool:
    return template_finder.search(
        "BIND_SKILL",
        grab(force_new=True),
        threshold=0.8,
        roi=Config().ui_roi["bind_skill"],
        use_grayscale=True,
    ).valid


def _open_skill_picker(side: str) -> None:
    if is_ingame_menu_open():
        raise RuntimeError("in-game escape menu is open")
    already_open = is_skill_picker_open()
    Logger.info(f"Skill setter: picker already open={already_open}")
    if not already_open:
        Logger.info("Skill setter: sending 's' to open skill picker")
        keyboard.send("s")
        wait(0.25, 0.35)
        Logger.info(f"Skill setter: picker open after 's' = {is_skill_picker_open()}")
    clear_x = Config().ui_pos["screen_width"] // 2
    clear_y = Config().ui_pos["screen_height"] // 3
    clear_mx, clear_my = convert_screen_to_monitor((clear_x, clear_y))
    mouse.move(clear_mx, clear_my, randomize=0)
    wait(0.12, 0.18)
    if is_ingame_menu_open():
        raise RuntimeError("in-game escape menu opened while trying to open skill picker")


def bind_skill_hotkey(check: SkillCheck, threshold: float = 0.78) -> SkillBindResult:
    Logger.info(f"Skill setter: binding {check.skill} -> {check.hotkey} (side={check.side})")

    if not check.hotkey:
        Logger.warning(f"Skill setter: {check.skill} skipped — no hotkey configured")
        return SkillBindResult(check.skill, check.hotkey, check.side, check.template, False, False, "no hotkey configured")

    template_name = _first_existing_template(check)
    if template_name is None:
        Logger.error(f"Skill setter: {check.skill} — template missing (checked {PICKER_TEMPLATE_ALIASES.get(check.skill, (check.template,))})")
        return SkillBindResult(check.skill, check.hotkey, check.side, check.template, False, False, "template missing")

    expanded_roi = _expanded_roi(check.side)
    if expanded_roi is None:
        Logger.error(f"Skill setter: {check.skill} — expanded skill ROI missing for side={check.side}")
        return SkillBindResult(check.skill, check.hotkey, check.side, template_name, False, False, "expanded skill ROI missing")

    Logger.info(f"Skill setter: opening picker (side={check.side})")
    try:
        _open_skill_picker(check.side)
    except RuntimeError as error:
        Logger.error(f"Skill setter: {check.skill} — could not open picker: {error}")
        return SkillBindResult(check.skill, check.hotkey, check.side, template_name, False, False, str(error))

    if not is_skill_picker_open():
        Logger.error(f"Skill setter: {check.skill} — picker did not open after sending open key")
        return SkillBindResult(check.skill, check.hotkey, check.side, template_name, False, False, "skill picker did not open")

    Logger.info(f"Skill setter: picker open — searching for {template_name} in ROI {expanded_roi}")
    match = template_finder.search(template_name, grab(force_new=True), threshold=threshold, roi=expanded_roi)
    if not match.valid:
        Logger.error(f"Skill setter: {check.skill} — {template_name} not visible in picker (threshold={threshold})")
        if is_skill_picker_open():
            keyboard.send("s")
            wait(0.20, 0.30)
        return SkillBindResult(check.skill, check.hotkey, check.side, template_name, False, False, "skill not visible in picker")

    Logger.info(f"Skill setter: found {template_name} at {match.center_monitor} — moving mouse")
    mouse.move(*match.center_monitor)
    wait(0.08, 0.12)
    Logger.info(f"Skill setter: pressing hotkey {check.hotkey}")
    keyboard.send(check.hotkey)
    wait(0.15, 0.25)
    if is_skill_picker_open():
        keyboard.send("s")
        wait(0.20, 0.30)
    verified, _selected_template, score = _check_skill_icon(check)
    Logger.info(f"Skill setter: post-bind verify {check.skill} -> {'OK' if verified else 'FAILED'} (score={score:.2f})")
    return SkillBindResult(
        check.skill,
        check.hotkey,
        check.side,
        template_name,
        True,
        bool(verified),
        "" if verified else "selected skill visual verification failed",
    )


def bind_build_hotkeys(
    config_instance: Config,
    char_type: str | None = None,
    required_only: bool = False,
    only_skill: str | None = None,
) -> list[SkillBindResult]:
    char_type = char_type or config_instance.char.get("type", "")
    checks = get_build_skill_checks(config_instance, char_type)
    if required_only:
        checks = [check for check in checks if check.required]
    if only_skill:
        checks = [check for check in checks if check.skill == only_skill]

    results = []
    Logger.info(f"Skill hotkey setter: build={char_type}, required_only={required_only}, only_skill={only_skill}")
    for check in checks:
        result = bind_skill_hotkey(check)
        results.append(result)
        if result.bound and result.verified:
            Logger.info(f"Skill hotkey setter: {result.skill} -> {result.hotkey} verified")
        elif result.bound:
            Logger.error(f"Skill hotkey setter: {result.skill} -> {result.hotkey} bound but not verified: {result.reason}")
        else:
            Logger.error(f"Skill hotkey setter: {result.skill} -> {result.hotkey} not bound: {result.reason}")
    return results
