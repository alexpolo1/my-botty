from char import IChar
from logger import Logger
from pather import Location, Pather
from item.pickit import PickIt
import template_finder
from town.town_manager import TownManager
from utils.misc import wait
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

    def approach(self, start_loc: Location) -> bool | Location:
        # TODO: Implement approach logic for Andariel
        Logger.info("Run Andariel")
        # loc = self._town_manager.go_to_act(1, start_loc)
        # if not loc:
        #     return False
        # TODO: Add traversal to None  # TODO
        # if not self._pather.traverse_nodes((loc, Location.None  # TODO), self._char):
        #     return False
        return False  # Replace with actual start Location constant

    def battle(self, do_pre_buff: bool) -> bool | tuple[Location, bool]:
        # TODO: Implement battle logic for Andariel
        # if not template_finder.search_and_wait(["TODO"], threshold=0.65, timeout=20).valid:
        #     return False
        # if do_pre_buff:
        #     if not self._char.pre_buff():
        #         return False
        # if self._char.capabilities.can_teleport_natively:
        #     self._pather.traverse_nodes_fixed("todo_safe_dist", self._char)
        # else:
        #     if not self._pather.traverse_nodes((Location.TODO), self._char):
        #         return False
        # self._char.kill_todo()
        # wait(0.2, 0.3)
        # picked_up_items = self._pickit.pick_up_items(self._char)
        # return (Location.TODO, picked_up_items)
        return False
