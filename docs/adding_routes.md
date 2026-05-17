# Adding a New Farming Route

## Quick Start (Scaffolding Tool)

```bash
python3 tools/new_route.py --name my_target --act 1 --location "Black Marsh"
```

This generates `src/run/my_target.py` and prints every line you need to add to `bot.py`, `params.ini`, and `pather.py`. The tool also runs `ruff check` on the generated file.

For a simpler inline version (no ruff check):

```bash
python3 src/utils/new_route.py --name my_target --act 1 --location "Black Marsh"
```

---

## Step-by-Step Manual Guide

### 1. Create the run file: `src/run/my_target.py`

Every run has two methods:

**`approach(start_loc, do_pre_buff)`** — gets the character to the run start location:
- Navigate to the right act's WP via `traverse_nodes_automap()`
- Use `pather.go_to_area("Area Name", "WP")` to take the waypoint
- Return a `Location` constant on success, `False` on failure

**`battle()`** — kills the target and picks items:
- Navigate to the target via recorded path nodes
- Call `char.kill_X()` (add to `IChar` / your char class if missing)
- Call `pickit.pick_up_items(char)`
- Return `(Location, picked_up_bool)` on success, `False` on failure

### 2. Add path node constants to `src/pather.py`

In `class Location`, add string constants for each nav point:
```python
MY_TARGET_SAFE_DIST = "my_target_safe_dist"
```

### 3. Record path nodes in-game

Requires: **D2R game running**, **bot window active**, **game window NOT in fullscreen**

```bash
python3 src/utils/node_recorder.py
```

Enter the run name (e.g. `andariel`) when prompted. A debug visualization window will appear.

#### Recording workflow:

1. **F8** — Record a visual template: click top-left corner of a distinctive UI element or landmark, press F8, then click bottom-right corner, press F8 again. This creates a reusable reference point.
2. **F9** — Record a navigation node at the current mouse cursor position (relative to the templates you recorded).
3. **F10** — Update all recorded nodes with currently visible templates.
4. **F12** — Exit recorder.

Recorded templates go to `log/screenshots/generated/templates/<run_name>/`.
The generated pather code is written to `log/screenshots/generated/pather_generated.py`.

#### Level requirements for boss areas (need campaign progress):

| Boss | Act | Minimum Level | Area |
|------|-----|---------------|------|
| Countess | 1 | 1 | Forgotten Tower |
| Andariel | 1 | 6 | Catacombs Level 4 |
| Duriel | 2 | 15 | Sewers Level 3 |
| Mephisto | 3 | 30 | Durance of Hate Level 3 |
| Baal | 5 | 60 | Throne of Destruction |

You need a character that has progressed through the campaign to access these areas. If you're starting from level 1, you'll need to play through each act to unlock the areas, then record nodes as you go.

### 4. Register the route in `src/bot.py`

Four additions (the scaffold tool prints the exact lines):
1. Import: `from run import ..., MyTarget`
2. `_do_runs` dict entry: `"run_my_target": Config().routes.get("run_my_target"),`
3. Instance: `self._my_target = MyTarget(...)`
4. State machine state + transition + handler method

### 5. Document in `config/params.ini`

Add `; run_my_target` to the routes comment block so users know it exists.

### 6. Enable the route

In your `config/params.ini` (or `config/custom.ini`):
```ini
[routes]
order=run_pindle, run_my_target
```

---

## Stealth Tips for New Routes

- Use `wait(min, max)` for all pauses — the stealth jitter config multiplies these automatically
- Use `stealth_move(x, y)` instead of `mouse.move(x, y)` for clicks in the new run
- Keep path node counts low (3-5 nodes) — more nodes = more predictable pathing patterns
- Vary which areas you teleport through using random sub-paths if the route allows it
