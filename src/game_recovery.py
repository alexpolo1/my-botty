from config import Config
from death_manager import DeathManager
import time
from input_layer import keyboard
from ui_manager import ScreenObjects, is_visible
from ui import view, loading
from utils.misc import set_d2r_always_on_top
from utils.misc import wait

class GameRecovery:
    def __init__(self, death_manager: DeathManager):
        self._death_manager = death_manager

    def go_to_hero_selection(self):
        set_d2r_always_on_top()
        wait(1, 1.5)
        # clean up key presses that might be pressed in the run_thread
        keyboard.release(Config().char["stand_still"])
        wait(0.1, 0.15)
        keyboard.release(Config().char["show_items"])
        start = time.time()
        while (time.time() - start) < 30:
            # make sure we are not on loading screen
            is_loading = loading.check_for_black_screen()
            while is_loading:
                is_loading = is_visible(ScreenObjects.Loading)
                is_loading |= loading.check_for_black_screen()
                wait(0.5, 0.75)
            # lets just see if you might already be at hero selection
            if is_visible(ScreenObjects.MainMenu):
                return True
            # would have been too easy, maybe we have died?
            if self._death_manager.handle_death_screen():
                wait(1, 1.5)
                continue
            # if we are in game, save and exit
            if is_visible(ScreenObjects.InGame):
                view.fast_save_and_exit()
                continue
            wait(1, 1.5)
        return False


if __name__ == "__main__":
    from death_manager import DeathManager
    from input_layer import keyboard
    import os
    keyboard.add_hotkey('f12', lambda: os._exit(1))
    keyboard.wait("f11")
    death_manager = DeathManager()
    game_recovery = GameRecovery(death_manager)
    print(game_recovery.go_to_hero_selection())
