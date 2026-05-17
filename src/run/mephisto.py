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


class Mephisto:

    name = "run_mephisto"

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
        Logger.info("Run Mephisto")
        loc = self._town_manager.go_to_act(3, start_loc)
        if not loc:
            return False
        # Traverse to the waypoint at stash
        if not self._pather.traverse_nodes((loc, Location.A3_STASH_WP), self._char):
            return False
        # Open waypoint and select Durance of Hate Level 2
        if not self._town_manager.open_wp(loc):
            return False
        if not waypoint.use_wp(label="Durance of Hate Level 2"):
            return False
        wait(0.5, 0.6)
        # Pre-buff after entering the area
        if do_pre_buff:
            self._char.pre_buff()
        return Location.A3_TOWN_START  # Durance L2 fallback

    def battle(self) -> bool | tuple[Location, bool]:
        # Traverse to Mephisto's location
        if self._char.capabilities.can_teleport_natively:
            self._pather.traverse_nodes_fixed("a3_meph_level3_enter", self._char)
        else:
            if not self._pather.traverse_nodes((Location.A3_TOWN_START, Location.A3_MEPH_LEVEL3_ENTER), self._char):
                return False
        if self._char.capabilities.can_teleport_natively:
            self._pather.traverse_nodes_fixed("a3_meph_safe_dist", self._char)
        else:
            if not self._pather.traverse_nodes((Location.A3_MEPH_LEVEL3_ENTER, Location.A3_MEPH_SAFE_DIST), self._char):
                return False

        self._char.kill_mephisto()
        wait(0.2, 0.3)
        picked_up_items = self._pickit.pick_up_items(self._char)
        return (Location.A3_TOWN_START, picked_up_items)
