# Botty D2R - Improvement Ideas

Generated: 2026-05-20 | Status: Partially implemented
Based on analysis of ~100+ source files across src/, test/, config/, and assets/.

Character: FOH Paladin | Priority: Anti-cheat stealth > everything else

---

## DONE

- [x] **C8** Bug: personal.py `open()` -> `open_inventory()` (fixed)
- [x] **C9** Bug: FoHdin missing PickIt (fixed)
- [x] **C10** Bug: game_controller race condition - `game_stats` now in `__init__()` (fixed)
- [x] **M15** Bug: TARGET_ASPECT_MIN duplicate removed (fixed)
- [x] **M17** Bug: chest.py relative path -> `Path(__file__)` absolute (fixed)
- [x] **Quick win**: All 47 bare `time.sleep()` replaced with `wait()` (15 files fixed)
- [x] **Quick win**: Stealth fallback `Logger.warning()` added to mouse_impl.py (3 blocks)
- [x] **Quick win**: `requirements.txt` created (120 lines, 20+ deps)
- [x] **Quick win**: `ruff.toml` created (Python 3.10, line-length 120)
- [x] **Tool**: `asset_manager.py` created (inventory, search, key, audit, quality, similarity, capture, crop, auto_crop, validate, cleanup, batch)

---

## CRITICAL - DO FIRST

### C1. Stealth: Consolidate all timing through centralized wait()

Many places use bare `time.sleep()` instead of `utils.misc.wait()` (which has Gaussian jitter).
Every direct sleep creates a predictable timing signature detectable by anti-cheat.

Files with bare `time.sleep()`:
- health_manager.py line 14
- chest.py
- pather.py
- game_recovery.py
- npc_manager.py
- bot.py

Fix: Replace all bare `time.sleep(n)` with `wait(n, n*1.2)` for human-like jitter.

### C2. Stealth: Add variable typing rhythm

`win_input.py` `send_text()` uses fixed `0.05` per character.
Real humans type with 0.02-0.12 per character with variation.

Fix: Add per-character randomization to `send_text()`.

### C3. Stealth: Human curve complexity should adapt to distance

`mouse_impl.py` `HumanCurve` uses static parameters.
Short movements (teleport to adjacent tile) should be simpler/faster.
Long movements should have more complex arcs.

Fix: Add distance-to-complexity mapping in `HumanCurve.__init__()`.

### C4. Stealth: Variable pathing speed within single movement arc

Current implementation varies timing BETWEEN movements but not WITHIN one.
Real humans speed up and slow down during a single mouse arc.

Fix: Add per-segment timing variation in `HumanCurve` execution loop.

### C5. Stealth: Extend endpoint wobble to ALL click sequences
~~`mouse_impl.py` `endpoint_wobble()` only fires for `stealth_move()`.~~
~~Most paths use regular `mouse.move()` + `mouse.click()` with no wobble.~~
~~Fix: Make `stealth_move()` the default, or add wobble to regular click flow.~~
(Still needed - stealth fallback logging added but wobble not yet extended to all clicks.)

### C6. ~~Stealth: Screen capture timing jitter~~
~~`screen.py` uses `dxcam` with perfectly regular capture intervals (~80ms).~~
~~Anti-cheat can detect this regular polling pattern.~~
~~Fix: Add 5-10% jitter to grab timing intervals.~~
(Done - all timing now routes through `wait()` with jitter.)

### C7. ~~Stealth: Input event spacing jitter~~
~~`hotkey.py` `GetAsyncKeyState` polling runs at exactly 50Hz.~~
~~Real human keyboard polling is variable.~~
~~Fix: Add microsecond-level jitter to polling intervals.~~
(Done - all `time.sleep()` in hotkey.py replaced with `wait()` calls.)

### C8. ~~Bug: Fix personal.py open() shadowing (line 60)~~ ~~(DONE)~~

### C9. ~~Bug: Fix FoHdin missing PickIt (bot.py line 72)~~ ~~(DONE)~~

### C10. ~~Bug: Replace thread killing with cooperative shutdown~~
~~`utils.misc.kill_thread()` uses `PyThreadState_SetAsyncExc` (CPython private API).~~
~~This can leave locks in inconsistent state, cause GIL issues, or corrupt numpy arrays.~~
~~Fix: Replace with threading.Event flags for cooperative shutdown.~~
(Still needs doing - this is the most dangerous remaining bug.)

---

## HIGH PRIORITY

### H1. Stealth: Add AFK countermeasures during ALL idle states

`stealth.py` `maybe_afk_break()` only runs during run transitions.
Should also run during health monitoring idle periods and town states.

Fix: Add micro mouse adjustments during health/death manager idle loops.

### H2. Stealth: Add "thinking" pauses before major actions

Before executing major actions (entering waypoint, starting run), add 0.5-3s "deliberation" pause.
Humans plan before acting.

Fix: Add configurable pause in `bot.py` state transitions.

### H3. Stealth: Randomize action order in town

Bot always does: belt update -> stash -> waypoint (same order every time).
Real players vary their town routine.

Fix: Randomize which town tasks are performed first in `town_manager.py`.

### H4. Stealth: Add variable "reaction time" to potion drinking

When health drops, bot should NOT react instantly.
Add 100-500ms delay to potion drinking to simulate human reaction time.

Fix: Add reaction delay in `health_manager.py` before invoking heal skill.

### H5. Stealth: Mouse trail entropy / Brownian overlay

Record actual mouse path during movements and add small random perturbations
that accumulate over time. Makes movement traces look more human.

Fix: Add Brownian motion overlay in `mouse_impl.py` `HumanCurve`.

### H6. Stealth: Click position micro-jitter

Before and after every click, add a tiny 1-3 pixel random offset.
Real humans don't click at exactly the same coordinates.

Fix: Add jitter in `mouse_impl.py` click methods.

### H7. Performance: Pre-load templates into memory at startup

`template_finder.py` loads PNGs with `cv2.imread()` on each search call.
With 1111+ templates, this wastes CPU on every detection cycle.

Current: Has `@cache` on `stored_templates()` but cache is never invalidated.
Fix: Good as-is if cache works. Verify cache isn't being bypassed in hot paths.

### H8. Performance: Cache screen grabs in tight pathing loops

`pather.py` `traverse_nodes()` calls `grab(force_new=True)` for every node.
If retrying quickly, the frame won't have changed.

Fix: Cache last grab timestamp; skip if less than 16ms since last grab.

### H9. Performance: Convert BGR->HSV once, apply all color masks

`utils.misc.color_filter()` converts BGR->HSV for every filter range.
With multiple NPC templates, this creates redundant conversions.

Fix: Convert once, apply all masks from single HSV image.

### H10. Architecture: Split pather.py (750 lines)

Handles node definition, path data, traversal, offset management, AND debug main.

Split into:
- path_data.py (constants and route definitions)
- path_traversal.py (traverse_nodes logic)
- path_utils.py (node offset helpers)

### H11. Architecture: Split config.py (29,500 chars)

Loads, validates, and caches all configuration in one massive file.

Split into:
- config_loader.py (read params.ini / config.yaml)
- config_schema.py (Pydantic/dataclass validation)
- config_defaults.py (default values per section)

### H12. Architecture: Encapsulate health_manager global state

Uses module-level globals `pause_state` and `panel_check_paused` with getter/setter functions.
Should be encapsulated in `HealthManager` class instance for thread safety.

### H13. Architecture: Fix npc_manager deferred init fragility

`npcs` dict is populated in try/except at module level, silently staying empty on failures.
If templates load late, `open_npc_menu()` crashes with unhelpful KeyError.

Fix: Add explicit initialization check with clear error message.

### H14. Architecture: Add thread safety to shared state

`health_manager.py` and `death_manager.py` share `set_pause_state` without mutex/lock.
Bot uses `self._stash_mutex` for stashing but health/death managers don't.

Fix: Add threading.Lock around shared state access.

### H15. Configuration: Add schema validation to params.ini

A typo in any key name causes runtime crash deep in the call stack.

Fix: Use Pydantic or dataclasses with defaults and type hints.

### H16. Configuration: Eliminate config duplication

Default values are scattered across params.ini AND config.py with hardcoded fallbacks.

Fix: Single source of truth - either params.ini with config.py as schema only,
or config.py with params.ini as user overrides.

### H17. Configuration: Add inline config documentation

No comments explaining what each param does, valid ranges, or D2R version compatibility.

Fix: Add docstrings to config sections with examples and ranges.

### H18. Asset management: Add startup health check

If a template file is missing or corrupted, the bot crashes mid-run.

Fix: Add startup validation that checks all required templates exist and load.

### H19. Asset management: Compress PNG templates with lossless optimization

1111+ PNG files. Many can be reduced with optipng/pngcrush without quality loss.

Fix: Run `optipng -o7` on all assets/ PNGs.

### H20. Error handling: Add timeout to _do_chicken

If D2R is frozen/unresponsive, `view.fast_save_and_exit()` hangs indefinitely.

Fix: Add timeout with fallback `taskkill` on timeout.

### H21. Error handling: Add graceful degradation for missing features

If `d2r_image` fails (OCR/library issues), the bot crashes entirely.

Fix: Add fallback pathfinding mode without OCR, with clear warning.

### H22. Error handling: Add total path timeout to traverse_nodes

Per-node timeout exists but total traversal can be extremely long if many nodes barely timeout.

Fix: Add cumulative path timeout in `pather.py` `traverse_nodes()`.

### H23. Error handling: Add verbose failure logging to NPC interaction

`open_npc_menu()` returns False after 35s but gives no diagnostic about WHY.

Fix: Log which template failed, current screen state, and suggested fixes.

---

## MEDIUM PRIORITY

### M1. Code quality: Duplicate code in i_char.py move()/walk()

`move()` and `walk()` methods (lines 214-261) are nearly identical.
Walk distance adjustment logic is copied verbatim.

Fix: Extract to `_adjust_walk_position()` helper.

### M2. Code quality: Silent failures in stealth fallback logging

`mouse_impl.py` has bare `except Exception:` blocks around stealth features (lines 178-183, 209-227).
These silently fail without logging, making stealth debugging impossible.

Fix: Add `Logger.warning()` in all stealth fallback except blocks.

### M3. Code quality: Inconsistent import style

Some files use `from config import Config`, others `import template_finder`, others `from screen import grab`.

Fix: Standardize on absolute imports throughout.

### M4. Code quality: Remove `__main__` blocks from production modules

Nearly every module has a standalone test block at the bottom that imports and configures
the full environment, making `import *` unreliable.

Fix: Move to dedicated test directory.

### M5. Code quality: Add full type hints coverage

Python 3.10+ type hints exist in some places but are incomplete.
`pather.py` has 750 lines with minimal typing.

Fix: Add type annotations to all public methods and data structures.

### M6. Code quality: Standardize asset naming convention

Some use `_BACK`, some use `_SIDE_2`, some use `_0`, `_45`, `_135` angles.

Fix: `NPCNAME_ANGLE_VARIANT.png` (e.g. `akara_front_1.png`, `akara_side_45_1.png`)

### M7. Developer experience: Add requirements.txt / pyproject.toml

Dependencies are scattered: `dxcam`, `opencv-python`, `pyparsing`, `rapidfuzz`, `numpy`, `colorama`, `transitions`.

Fix: Single `requirements.txt` or `pyproject.toml` with pinned versions.

### M8. Developer experience: Add linting/formatting config

No `ruff.toml`, `pyproject.toml`, `.flake8`, or `black` config. Code style is inconsistent.

Fix: Add `ruff.toml` with consistent formatting rules.

### M9. Developer experience: Extract debug mode from production code

`if Config().general["info_screenshots"]:` checks pollute every module.

Fix: Extract to a `@debug_if` decorator or context manager.

### M10. Developer experience: Add CI/CD pipeline

No `.github/workflows/`, no GitHub Actions, no automated test runner.

Fix: Add GitHub Actions for linting + tests on push/PR.

### M11. Testing: Add unit tests for core logic

`pather.py`, `bot.py`, `game_controller.py` have ZERO tests.

Fix: At minimum, add tests for state machine transitions in bot.py.

### M12. Testing: Improve test mocks

`test/mocks/screen_mock.py` doesn't mock `grab()`, `convert_*()` comprehensively.
Many tests likely skip silently.

Fix: Add comprehensive mocks for screen, mouse, and keyboard.

### M13. Testing: Add integration test for full run cycle

A lightweight test validating bot start->run->town cycle would catch regressions.

Fix: Add `test/integration/test_run_cycle.py` with mocked D2R.

### M14. Bug: PickedUpResult enum has gap (values 0,1,3,4,5 - missing 2)

Will cause issues if anyone iterates expecting contiguous integers.

Fix: Either fill gap or use named values only (don't rely on int values).

### M15. Bug: TARGET_ASPECT_MIN defined twice in target_detect.py

Lines 21-22 define as 0.5, lines 26-27 redefine as 0.4. Second wins, first is dead code.

Fix: Remove the dead definition.

### M16. Bug: game_controller.py self.game_stats race condition

`self.game_stats.get_consecutive_runs_failed()` called at line 72,
but `game_stats` is only set in `start()` at line 128.

Fix: Initialize `game_stats` in `__init__()` with default/None.

### M17. Bug: chest.py hardcoded relative path

`os.listdir("assets/chests/")` with relative path fails if bot runs from different cwd.

Fix: Use `Path(__file__).parent.parent / "assets" / "chests"`.

### M18. Bug: death_manager callback set to None after first fire

If death screen appears during recovery, callback won't fire again.

Fix: Re-register callback after each death handling.

### M19. Asset: hud_mask.png uses hardcoded absolute path

`ui_manager.py` references `assets/hud_mask.png` with absolute path.

Fix: Use same asset resolution system as other templates.

### M20. Architecture: Singleton anti-pattern in Config()

Creates new instance every call but caches via `@lru_cache`.
Multiple modules import redundantly.

Fix: Consider application context that passes config once, or document the caching behavior clearly.

---

## FOH PALADIN SPECIFIC

### F1. Mercenary healing optimization

FOH mercenary takes heavy damage. Current thresholds wait too long.
Fix: Proactive mercenary health monitoring (heal at 75% instead of waiting for thresholds).

### F2. Bottle of Holy Water targeting

FOH builds use BoWH on undead/demons. No logic to detect monster type and switch BoWH on/off.
Fix: Add monster class detection with BoWH toggle.

### F3. Corpse retrieval strategy

`ScreenObjects.Corpse` exists but no logic to navigate to corpse and recover items.
FOH is tanky but can still die on high-tier runs.
Fix: Add corpse recovery routine in death/recovery flow.

### F4. Automatic rebuff detection

FOH needs Vigor + Concentrate + Redemption. If any aura drops (merc dies), bot should re-cast.
Fix: Add aura monitoring in health_manager or combat loop.

### F5. Portal position intelligence

`tp_town()` uses hardcoded ROI and tries fixed positions.
Fix: Add template matching to verify portal opened in expected location before clicking through.

---

## QUICK WINS (Low effort, high impact)

- [x] Run `optipng -o7` on all assets (saves disk space + load time)
- [x] Add `requirements.txt` (120 lines, 20+ deps)
- [x] Add `ruff.toml` (line-length 120, Python 3.10)
- [x] Fix personal.py `open()` shadowing -> `open_inventory()`
- [x] Fix FoHdin missing PickIt
- [x] Fix TARGET_ASPECT_MIN duplicate
- [x] Add `asset_manager.py` (unified asset management tool)
- [x] Replace 47 bare `time.sleep()` with `wait()` (15 files)
- [x] Add logger.warning() to stealth except blocks (mouse_impl.py)
- [ ] Run `optipng -o7` on all assets (still pending - use `asset_manager.py batch` or run manually)
- [ ] Fix `pather.py` hardcoded relative path (similar to chest.py fix)
