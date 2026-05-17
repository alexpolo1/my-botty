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


class Baal:

    name = "run_baal"

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
        Logger.info("Run Baal")
        loc = self._town_manager.go_to_act(5, start_loc)
        if not loc:
            return False
        # Traverse to the waypoint
        if not self._pather.traverse_nodes((loc, Location.A5_WP), self._char):
            return False
        # Open waypoint and select Throne of Destruction (Worldstone Keep Level 2 is the closest;
        # Throne of Destruction is not a direct waypoint but accessed from it)
        if not self._town_manager.open_wp(loc):
            return False
        if not waypoint.use_wp(label="Worldstone Keep Level 2"):
            return False
        wait(0.5, 0.6)
        # Pre-buff after entering the area
        if do_pre_buff:
            self._char.pre_buff()
        return Location.A5_TOWN_START  # Throne of Destruction fallback

    def battle(self) -> bool | tuple[Location, bool]:
        # Traverse into the Throne of Destruction
        if self._char.capabilities.can_teleport_natively:
            self._pather.traverse_nodes_fixed("a5_baal_throne_entry", self._char)
        else:
            if not self._pather.traverse_nodes((Location.A5_TOWN_START, Location.A5_BAAL_THRONE_ENTRY), self._char):
                return False
        if self._char.capabilities.can_teleport_natively:
            self._pather.traverse_nodes_fixed("a5_baal_safe_dist", self._char)
        else:
            if not self._pather.traverse_nodes((Location.A5_BAAL_THRONE_ENTRY, Location.A5_BAAL_SAFE_DIST), self._char):
                return False

        # Clear the waves of minions (~45s of combat)
        self._char.kill_baal_waves()
        # Kill Baal
        self._char.kill_baal()
        wait(0.2, 0.3)
        picked_up_items = self._pickit.pick_up_items(self._char)
        return (Location.A5_TOWN_START, picked_up_items)
