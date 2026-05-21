from input_layer import mouse
from utils.misc import cut_roi, roi_center, wait, is_in_roi

from config import Config
from screen import convert_screen_to_monitor, grab
import template_finder
from utils.misc import wait
from logger import Logger
from d2r_image import ocr
import numpy as np
from ui_manager import detect_screen_object, ScreenObjects

last_char_template = None
online_character = None

def select_online_tab(region, center) -> bool:
    btn_width = center[0] - region[0]
    if online_character:
        Logger.debug(f"Selecting online tab")
        x = region[0] + (btn_width / 2)
    else:
        Logger.debug(f"Selecting offline tab")
        x = region[0] + (3 * btn_width / 2)
    pos = convert_screen_to_monitor((x, center[1]))
    # move cursor to appropriate tab and select
    mouse.move(*pos)
    wait(0.3, 0.5)
    attempts = 0
    while attempts <= 4:
        attempts += 1
        mouse.click(button="left")
        if (match := detect_screen_object(ScreenObjects.OnlineStatus, grab())).valid and online_character == online_active(match):
            return True
        wait(1.5)
    online_str = "online" if online_character else "offline"
    Logger.error(f"select_online_tab: unable to select {online_str} tab after {attempts} attempts")
    return False

def get_saved_char_template() -> np.ndarray | None:
    return None if not has_char_template_saved() else last_char_template

def has_char_template_saved():
    return last_char_template is not None

def save_char_online_status():
    if (match := detect_screen_object(ScreenObjects.OnlineStatus)).valid:
        online_status = online_active(match)
        Logger.debug(f"Saved online status. Online={online_status}")
    else:
        Logger.error("save_char_online_status: Could not determine character's online status")
        return
    global online_character
    online_character = online_status

def online_active(match) -> bool:
    return match.name == "CHARACTER_STATE_ONLINE"

def save_char_template():
    img = grab()
    if (match := detect_screen_object(ScreenObjects.SelectedCharacter)).valid:
        x, y, w, h = Config().ui_roi["character_name_sub_roi"]
        x, y = x + match.region[0], y + match.region[1]
        char_template = cut_roi(img, [x, y, w, h])
        msg=""
        try:
            ocr_result = ocr.image_to_text(
                images = cut_roi(img, [x, y, w, h]),
                model = "hover-eng_inconsolata_inv_th_fast",
                psm = 6,
                scale = 1.2,
                crop_pad = False,
                erode = False,
                invert = False,
                threshold = 0,
                digits_only = False,
                fix_regexps = False,
                check_known_errors = False,
                correct_words = False,
            )[0]
            msg += f": {ocr_result.text.splitlines()[0]}"
        except:
            pass
        Logger.debug(f"Saved character template{msg}")
    else:
        Logger.error("save_char_template: Could not save character template")
        return
    global last_char_template
    last_char_template = char_template

def select_char() -> bool:
    if last_char_template is not None:
        img = grab()
        if (match := detect_screen_object(ScreenObjects.OnlineStatus, img)).valid:
            if online_active(match) != online_character:
                if not select_online_tab(match.region, match.center):
                    return False
                img = grab()
            wait(1, 1.5)
        else:
            Logger.error("select_char: Could not find online/offline tabs")
            return False
        if not (match := detect_screen_object(ScreenObjects.SelectedCharacter, img)).valid:
            Logger.error("select_char: Could not find highlighted profile")
            return False
        scrolls_attempts = 0
        while scrolls_attempts < 2:
            if scrolls_attempts > 0:
                img = grab()
            # TODO: can cleanup logic here, can we utilize a generic ScreenObject or use custom locator?
            desired_char = template_finder.search(last_char_template, img, roi = Config().ui_roi["character_select"], threshold = 0.8)
            if desired_char.valid:
                #print(f"{match.region} {desired_char.center}")
                if is_in_roi(match.region, desired_char.center) and scrolls_attempts == 0:
                    Logger.debug("Saved character template found and already highlighted, continue")
                    return True
                else:
                    Logger.debug("Selecting saved character")
                    mouse.move(*desired_char.center_monitor)
                    wait(0.4, 0.6)
                    mouse.click(button="left")
                    wait(0.4, 0.6)
                    return True
            else:
                Logger.debug("Highlighted profile found but saved character not in view, scroll")
                # We can scroll the characters only if we have the mouse in the char names selection so move the mouse there
                center = roi_center(Config().ui_roi["character_select"])
                center = convert_screen_to_monitor(center)
                mouse.move(*center)
                wait(0.4, 0.6)
                mouse.wheel(-14)
                scrolls_attempts += 1
                wait(0.4, 0.6)
        Logger.error(f"select_char: unable to find saved profile after {scrolls_attempts} scroll attempts")

        # Fallback: try OCR-based name matching
        char_name = Config().general.get("char_name", "")
        if char_name:
            Logger.info(f"Template matching failed, trying OCR for character name: {char_name}")
            return _select_char_by_ocr(char_name)
        return False

    # No template saved — try OCR-based lookup if char_name is set
    char_name = Config().general.get("char_name", "")
    if char_name:
        Logger.info(f"No template saved, selecting character '{char_name}' via OCR")
        return _select_char_by_ocr(char_name)

    Logger.error("select_char: No character template saved and no char_name configured")
    return False


def _select_char_by_ocr(char_name: str) -> bool:
    """OCR-based character selection fallback. Scans visible character list, finds
    the matching name, clicks it, then scrolls and retries up to 2 times."""
    char_name_lower = char_name.lower()

    # Ensure we're on the right tab (online vs offline)
    online_status = None
    if online_character is not None:
        img = grab()
        if (match := detect_screen_object(ScreenObjects.OnlineStatus, img)).valid:
            online_status = online_active(match)
            if online_status != online_character:
                if not select_online_tab(match.region, match.center):
                    Logger.error("_select_char_by_ocr: could not switch online/offline tab")
                    return False
                img = grab()
                wait(1, 1.5)
    else:
        Logger.debug("_select_char_by_ocr: online status unknown, searching all tabs")

    if online_status is not None:
        img = grab()
    else:
        img = grab()

    # Get the character list ROI for scrolling
    char_roi = Config().ui_roi["character_select"]

    for scroll_pass in range(3):
        if scroll_pass > 0:
            # Scroll down and re-grab
            center = roi_center(char_roi)
            center = convert_screen_to_monitor(center)
            mouse.move(*center)
            wait(0.4, 0.6)
            mouse.wheel(-14)
            wait(0.4, 0.6)
            img = grab()

        # OCR each visible character entry
        # The character list is a vertical column — scan rows
        x, y, w, h = char_roi
        row_height = 30  # approximate height of each character entry row
        num_rows = max(1, h // row_height)

        for row in range(num_rows):
            row_y = y + row * row_height
            row_h = min(row_height + 5, y + h - row_y)
            if row_h < 5:
                break

            roi = [x, row_y, w, row_h]
            row_img = cut_roi(img, roi)

            try:
                result = ocr.image_to_text(
                    images=row_img,
                    model="hover-eng_inconsolata_inv_th_fast",
                    psm=6,
                    scale=1.2,
                    crop_pad=False,
                    erode=False,
                    invert=False,
                    threshold=0,
                    digits_only=False,
                    fix_regexps=True,
                    check_known_errors=False,
                    correct_words=False,
                )
                if result and result[0].text:
                    detected = result[0].text.strip().lower()
                    Logger.debug(f"Row {row}: OCR detected '{detected}'")
                    if char_name_lower == detected:
                        click_x = x + w // 2
                        click_y = row_y + row_h // 2
                        click_pos = convert_screen_to_monitor((click_x, click_y))
                        Logger.info(f"Found character '{char_name}' at row {row}")
                        mouse.move(*click_pos)
                        wait(0.4, 0.6)
                        mouse.click(button="left")
                        wait(0.4, 0.6)
                        return True
            except Exception as e:
                Logger.debug(f"OCR row {row} failed: {e}")
                continue

    Logger.error(f"_select_char_by_ocr: could not find '{char_name}' after scanning all visible entries")
    return False
