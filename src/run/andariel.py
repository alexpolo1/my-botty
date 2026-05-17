from char import IChar
from logger import Logger
from pather import Location, Pather
from item.pickit import PickIt
import template_finder
from town.town_manager import TownManager
from utils.misc import wait
from ui import loading
from ui import waypoint
from collections import OrderedDict


class Andariel:

    name = "run_andariel"

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
        self.runs = runs

    def approach(self, start_loc: Location, do_pre_buff: bool) -> bool | Location:
        Logger.info("Run Andariel")
        loc = self._town_manager.go_to_act(1, start_loc)
        if not loc:
            return False
        # Traverse to the waypoint
        if not self._pather.traverse_nodes((loc, Location.A1_WP_SOUTH), self._char):
            return False
        # Open waypoint and select Catacombs Level 2
        if not self._town_manager.open_wp(loc):
            return False
        if not waypoint.use_wp(label="Catacombs Level 2"):
            return False
        wait(0.5, 0.6)
        # Pre-buff after entering the area
        if do_pre_buff:
            self._char.pre_buff()
        return Location.A1_TOWN_START  # Catacombs L2 has no specific start Location yet; fallback

    def battle(self) -> bool | tuple[Location, bool]:
        # Traverse to Andariel's level
        if self._char.capabilities.can_teleport_natively:
            self._pather.traverse_nodes_fixed("a1_andy_level3_enter", self._char)
        else:
            if not self._pather.traverse_nodes((Location.A1_TOWN_START, Location.A1_ANDY_LEVEL3_ENTER), self._char):
                return False
            if not self._pather.traverse_nodes((Location.A1_ANDY_LEVEL3_ENTER, Location.A1_ANDY_LEVEL4_ENTER), self._char):
                return False
            if not self._pather.traverse_nodes((Location.A1_ANDY_LEVEL4_ENTER, Location.A1_ANDY_SAFE_DIST), self._char):
                return False
        if self._char.capabilities.can_teleport_natively:
            self._pather.traverse_nodes_fixed("a1_andy_safe_dist", self._char)

        self._char.kill_andariel()
        wait(0.2, 0.3)
        picked_up_items = self._pickit.pick_up_items(self._char)
        return (Location.A1_TOWN_START, picked_up_items)
