"""Leveling run - follow the road from town, kill mobs along the way."""

from char import IChar
from pather import Pather, Location
from item.pickit import PickIt
from logger import Logger
from config import Config
from town.town_manager import TownManager
from collections import OrderedDict
import time
import random

from input_layer import keyboard
from screen import grab, convert_abs_to_monitor
from target_detect import get_visible_targets
from input_layer import mouse
from utils.misc import wait


class Level:
    """Walk north from town, kill mobs, repeat."""

    name = "run_level"

    def __init__(
        self,
        pather: Pather,
        town_manager: TownManager,
        char: IChar,
        pickit: PickIt,
        runs: OrderedDict
    ):
        self._pather = pather
        self._town_manager = town_manager
        self._char = char
        self._pickit = pickit
        self._runs = runs
        self._max_steps = int(Config().general.get("level_max_steps", 20))

    def approach(self, start_loc: Location, do_pre_buff: bool) -> bool | Location:
        """Already in town/outside town - just walk north."""
        Logger.info("=== Level run: walking north ===")
        # We are already outside, just walk a few steps north to get onto the road
        for i in range(4):
            pos_m = convert_abs_to_monitor((random.randint(-20, 20), -(60 + i * 40)))
            self._char.walk(pos_m, force_move=True)
            wait(0.8, 1.2)
        return Location.A1_TOWN_START

    def battle(self) -> bool | tuple[Location, bool]:
        """Walk north, attack enemies, repeat until max steps."""
        picked_up_items = False
        for step in range(self._max_steps):
            Logger.info(f"  Step {step + 1}/{self._max_steps}")

            targets = get_visible_targets(radius_max=600)
            if targets:
                Logger.info(f"    Found {len(targets)} target(s)")
                self._fight_all()
                picked_up_items |= self._pickit.pick_up_items(self._char)
            else:
                Logger.info("    No enemies, walking north")
                pos_m = convert_abs_to_monitor(
                    (random.randint(-30, 30),
                     -(100 + random.randint(0, 50)))
                )
                self._char.walk(pos_m, force_move=True)
                wait(1.0, 2.0)

        return (Location.A1_TOWN_START, picked_up_items)

    def _fight_all(self):
        """Fight until no enemies visible."""
        for _ in range(15):
            targets = get_visible_targets(radius_max=600)
            if not targets:
                break
            t = targets[0]
            pos_m = t.center_monitor
            mouse.move(*pos_m, randomize=10, delay_factor=[0.3, 0.5])
            wait(0.05, 0.1)
            mouse.press(button="left")
            start = time.time()
            while time.time() - start < random.uniform(2.0, 3.5):
                if not get_visible_targets(radius_max=400):
                    break
                mouse.move(*pos_m, randomize=15)
                wait(0.2, 0.4)
            mouse.release(button="left")
            wait(0.3, 0.6)
