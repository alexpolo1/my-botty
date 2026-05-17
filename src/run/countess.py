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


class Countess:

    name = "run_countess"

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
        Logger.info("Run Countess")
        loc = self._town_manager.go_to_act(1, start_loc)
        if not loc:
            return False
        # Traverse to the waypoint
        if not self._pather.traverse_nodes((loc, Location.A1_WP_NORTH), self._char):
            return False
        # Open waypoint and select Black Marsh
        if not self._town_manager.open_wp(loc):
            return False
        if not waypoint.use_wp(label="Black Marsh"):
            return False
        wait(0.5, 0.6)
        # Pre-buff after entering the area
        if do_pre_buff:
            self._char.pre_buff()
        return Location.A1_TOWN_START  # Black Marsh / tower entrance fallback

    def battle(self) -> bool | tuple[Location, bool]:
        # Traverse through tower levels 2-5 to the Countess
        if self._char.capabilities.can_teleport_natively:
            self._pather.traverse_nodes_fixed("a1_tower_level2_enter", self._char)
        else:
            if not self._pather.traverse_nodes((Location.A1_TOWN_START, Location.A1_TOWER_LEVEL2_ENTER), self._char):
                return False
            if not self._pather.traverse_nodes((Location.A1_TOWER_LEVEL2_ENTER, Location.A1_TOWER_LEVEL3_ENTER), self._char):
                return False
            if not self._pather.traverse_nodes((Location.A1_TOWER_LEVEL3_ENTER, Location.A1_TOWER_LEVEL4_ENTER), self._char):
                return False
            if not self._pather.traverse_nodes((Location.A1_TOWER_LEVEL4_ENTER, Location.A1_TOWER_LEVEL5_ENTER), self._char):
                return False
        if self._char.capabilities.can_teleport_natively:
            self._pather.traverse_nodes_fixed("a1_countess_safe_dist", self._char)
        else:
            if not self._pather.traverse_nodes((Location.A1_TOWER_LEVEL5_ENTER, Location.A1_COUNTESS_SAFE_DIST), self._char):
                return False

        self._char.kill_countess()
        wait(0.2, 0.3)
        picked_up_items = self._pickit.pick_up_items(self._char)
        return (Location.A1_TOWN_START, picked_up_items)
