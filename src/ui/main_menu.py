import time
from input_layer import keyboard
from config import Config
from utils.misc import wait
from logger import Logger
from ui import error_screens
from ui_manager import detect_screen_object, is_visible, select_screen_object_match, ScreenObjects
import template_finder
from screen import grab

MAIN_MENU_MARKERS = ["MAIN_MENU_TOP_LEFT","MAIN_MENU_TOP_LEFT_DARK"]
TOWN_MARKERS = ["A5_TOWN_0", "A5_TOWN_1", "A4_TOWN_4", "A4_TOWN_5", "A3_TOWN_0", "A3_TOWN_1", "A2_TOWN_0", "A2_TOWN_1", "A2_TOWN_10", "A1_TOWN_1", "A1_TOWN_3"]

def _play_active(match) -> bool:
    return match.name == "PLAY_BTN"

def start_game() -> bool:
    """
    Starting a game. Will wait and retry on server connection issue.
    :return: Bool if action was successful
    """
    Logger.debug("Wait for Play button")
    difficulty = Config().general["difficulty"].lower()
    difficulty_key = "r" if difficulty == "normal" else "n" if difficulty == "nightmare" else "h"

    for _ in range(3):
        start = time.time()
        while True:
            if (m := detect_screen_object(ScreenObjects.PlayBtn)).valid:
                if _play_active(m):
                    Logger.debug(f"Found Play Btn, select and press key: {difficulty_key}")
                    select_screen_object_match(m)
                    keyboard.press(difficulty_key)
                    break
            else:
                # If we're already in town (e.g. previous game wasn't fully exited), continue flow.
                if template_finder.search(TOWN_MARKERS, grab(), best_match=True).valid:
                    Logger.warning("start_game: Already in town, skipping game creation")
                    return True
                Logger.error("start_game: No play button found, not on main menu screen")
                return False
            wait(1, 2)
            if time.time() - start > 45:
                Logger.error("start_game: Active play button never appeared")
                return False

        start = time.time()
        while True:
            if is_visible(ScreenObjects.Loading):
                Logger.debug("Found loading screen / creating game")
                keyboard.release(difficulty_key)
                return True
            wait(0.2)
            if is_visible(ScreenObjects.ServerError):
                error_screens.handle_error()
                keyboard.release(difficulty_key)
                break
            if template_finder.search(TOWN_MARKERS, grab(), best_match=True).valid:
                keyboard.release(difficulty_key)
                Logger.warning("start_game: Detected town while creating game, continuing")
                return True
            if time.time() - start > 15:
                Logger.error(f"Could not find {difficulty}_BTN or LOADING, retrying")
                keyboard.release(difficulty_key)
                break
    Logger.error("start_game: Failed to create game after retries")
    return False
