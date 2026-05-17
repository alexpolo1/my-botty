#!/usr/bin/env python3
"""
Scaffold a new botty run from the command line.

Usage:
    python src/utils/new_route.py --name my_target --act 1 --location "Black Marsh"

Generates:
    src/run/my_target.py   — run class skeleton
    Prints the lines to add to: src/run/__init__.py, src/bot.py, config/params.ini
"""
import argparse
import os
import sys

RUN_TEMPLATE = """\
import time
from char import IChar
from item.pickit import PickIt
from pather import Pather, Location
from town import TownManager
from utils.misc import wait
from logger import Logger


class {class_name}:
    def __init__(self, pather: Pather, town_manager: TownManager, char: IChar, pickit: PickIt, runs: list):
        self._pather = pather
        self._town_manager = town_manager
        self._char = char
        self._pickit = pickit
        self._runs = runs

    def approach(self, start_loc: Location, do_pre_buff: bool = False) -> bool | Location:
        Logger.info("Approaching {display_name}")
        if do_pre_buff:
            self._char.pre_buff()
        # TODO: navigate to starting WP
        # if not self._pather.traverse_nodes_automap([Location.{act_wp}], self._char):
        #     return False
        wait(0.5, 0.8)
        # TODO: take waypoint to correct area
        # if not self._pather.go_to_area("{wp_area}", "WP"):
        #     return False
        return Location.{act_town_start}

    def battle(self) -> bool | tuple[Location, bool]:
        Logger.info("Starting {display_name} battle")
        # TODO: traverse recorded path nodes to target
        # if not self._pather.traverse_nodes_automap(
        #     [Location.{snake_name}_SAFE_DIST],
        #     self._char
        # ):
        #     return False
        wait(0.3, 0.5)
        # TODO: call self._char.kill_{snake_name}() — implement on char if missing
        # self._char.kill_{snake_name}()
        wait(0.5, 1.0)
        picked = self._pickit.pick_up_items(self._char)
        return Location.{act_town_start}, picked
"""

BOT_PY_GUIDE = """\

--- bot.py changes needed ---

1. Add to imports:
   from run import ..., {class_name}

2. Add to self._do_runs dict in __init__():
   "run_{snake_name}": Config().routes.get("run_{snake_name}"),

3. Add instance creation in __init__():
   self._{snake_name} = {class_name}(self._pather, self._town_manager, self._char, self._pickit, runs)

4. Add to self._states list:
   '{snake_name}',

5. Add transition (after existing run transitions):
   {{ 'trigger': 'run_{snake_name}', 'source': 'town', 'dest': '{snake_name}', 'before': "on_run_{snake_name}" }},

6. Add to end_run and end_game source lists:
   '{snake_name}',

7. Add handler method:
   def on_run_{snake_name}(self):
       res = False
       self._do_runs["run_{snake_name}"] = False
       self._game_stats.update_location("{display_name}")
       self._curr_loc = self._{snake_name}.approach(self._curr_loc, not self._pre_buffed)
       if self._curr_loc:
           set_pause_state(False)
           res = self._{snake_name}.battle()
       self._ending_run_helper(res)
"""

LOCATION_GUIDE = """\

--- pather.py: add Location constants ---

    # {display_name} path nodes
    {upper_name}_SAFE_DIST = "{snake_name}_safe_dist"
    # Add more nodes as needed, e.g. level transitions

--- config/game.ini: add path nodes (replace 0,0 after in-game recording) ---

{snake_name}_safe_dist = 0, 0

--- config/params.ini: document the route ---

; run_{snake_name}    <- add this line to the routes comment block

--- After recording path nodes in-game (use src/utils/node_recorder.py), replace 0, 0 above ---
"""

ACT_DEFAULTS = {
    "1": ("A1_WP_SOUTH", "A1_TOWN_START"),
    "2": ("A2_WP", "A2_TOWN_START"),
    "3": ("A3_STASH_WP", "A3_TOWN_START"),
    "4": ("A4_WP", "A4_TOWN_START"),
    "5": ("A5_WP", "A5_TOWN_START"),
}


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new botty run")
    parser.add_argument("--name", required=True, help="Run name in snake_case, e.g. my_target")
    parser.add_argument("--act", required=True, choices=["1", "2", "3", "4", "5"], help="D2R act (1-5)")
    parser.add_argument("--location", default="", help="WP area name e.g. 'Black Marsh'")
    args = parser.parse_args()

    snake_name = args.name.lower().replace(" ", "_")
    class_name = "".join(w.capitalize() for w in snake_name.split("_"))
    display_name = " ".join(w.capitalize() for w in snake_name.split("_"))
    upper_name = snake_name.upper()
    act_wp, act_town_start = ACT_DEFAULTS[args.act]

    out_path = os.path.join(os.path.dirname(__file__), "..", "run", f"{snake_name}.py")
    out_path = os.path.normpath(out_path)

    if os.path.exists(out_path):
        print(f"ERROR: {out_path} already exists. Aborting.")
        sys.exit(1)

    code = RUN_TEMPLATE.format(
        class_name=class_name,
        display_name=display_name,
        snake_name=snake_name,
        upper_name=upper_name,
        act_wp=act_wp,
        act_town_start=act_town_start,
        wp_area=args.location or "TODO: WP area name",
    )

    with open(out_path, "w") as f:
        f.write(code)

    print(f"Created: {out_path}")
    print(BOT_PY_GUIDE.format(class_name=class_name, snake_name=snake_name, display_name=display_name))
    print(LOCATION_GUIDE.format(display_name=display_name, snake_name=snake_name, upper_name=upper_name))


if __name__ == "__main__":
    main()
