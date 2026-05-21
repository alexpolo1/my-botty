# Botty Architecture

## Overview

Botty is an autonomous bot for Diablo II Resurrected (D2R) that uses computer vision and native Windows API input to run endgame content without kernel drivers. It's built in Python 3.10 and distributed as a PyInstaller onefile executable.

## Entry Points

Two standalone executables are built from the same source:

| Executable | Source | Purpose |
|---|---|---|
| `main.exe` | `src/main.py` | Main bot controller |
| `shop.exe` | `src/shopper.py` | Standalone vendor shopping |

## Threading Model

main.py spawns three concurrent threads:

```
main.py (main thread)
├── game_controller.py (bot loop thread)
│   └── bot.py (state machine thread)
├── health_manager.py (background thread)
└── death_manager.py (background thread)
```

- **Main thread**: Shows UI, registers hotkeys (F7-F12), calls `keyboard.wait()` to block
- **Game Controller**: Orchestrates the bot loop - starts/stops the bot thread, handles game recovery, tracks stats
- **Health Manager**: Polls health/mana/merc every ~1s, auto-potions, chickens when low
- **Death Manager**: Polls every ~1s for "You Have Died" screen, triggers recovery

## Core Modules

### Input Layer (`src/input_layer/`)

Native Windows API input replacement (no kernel drivers):

| File | Purpose |
|---|---|
| `win_input.py` | ctypes wrappers for `SendInput`, `GetAsyncKeyState`, `GetCursorPos` |
| `mouse_impl.py` | Humanized mouse with Bezier curves, Gaussian distortion, endpoint wobble |
| `hotkey.py` | Polling-based hotkey manager (replaces `keyboard.add_hotkey`) |
| `__init__.py` | Drop-in API: `from input_layer import keyboard, mouse` |

All key presses include stealth micro-pauses and variable press duration automatically.

### Screen Capture (`src/screen.py`)

Handles D2R window detection and screenshot capture via MSS library. Converts between coordinate systems: Monitor (top-left first monitor), Screen (per-monitor), Absolute (character center), Relative (template-matched).

### Image Recognition (`src/template_finder.py`)

Template matching via OpenCV (`cv2.matchTemplate`). Searches against pre-captured asset templates in `assets/templates/`. Returns match position and validity.

### UI Detection (`src/ui/`)

| File | Detects |
|---|---|
| `main_menu.py` | Main menu buttons (play, save & exit) |
| `character_select.py` | Character portraits and selection |
| `skills.py` | Skill bar state, skill availability |
| `meters.py` | Health/mana globes, potion charges |
| `player_bar.py` | Player status bar, XP bar |
| `view.py` | Minimap, inventory screen detection |
| `waypoint.py` | Waypoint portal selection |
| `error_screens.py` | Error dialogs, death screen |
| `loading.py` | Loading screen detection |

### Pathing (`src/pather.py`)

Pathfinding via reference template matching with relative coordinates. Each location has numbered nodes with template references. The `Location` class defines named destinations (towns, dungeons). Path definitions map (start, end) pairs to node sequences.

### Character System (`src/char/`)

Inheritance hierarchy:

```
IChar (abstract base)
├── Basic / Basic_Ranged
├── Paladin
│   ├── Hammerdin
│   └── FoHdin
├── Sorceress (base for all sorc builds)
│   ├── BlizzSorc
│   ├── BlizzorbSorc
│   ├── NovaSorc
│   ├── LightSorc
│   └── HydraSorc
├── Amazon
│   └── Javazon
├── Trapsin
├── Barbarian
├── Necro
├── Poison_Necro
├── Bone_Necro
└── Warlock
    ├── FireLock
    ├── EchoLock
    └── AbyssLock
```

Each character class implements: run methods, skill usage, attack patterns, position-specific behavior.

### Run System (`src/run/`)

| File | Run |
|---|---|
| `pindle.py` | Pindle of Purity |
| `shenk_eld.py` | Shenk + Eldritch |
| `trav.py` | Travincal |
| `nihlathak.py` | Nihlathak's Temple |
| `arcane.py` | Arcane Sanctuary |
| `diablo.py` | Chaos Sanctuary + Diablo |
| `vizier.py` | Vizier (Seal Boss) |
| `baal.py` | Baal |
| `mephisto.py` | Mephisto |
| `andariel.py` | Andariel |
| `countess.py` | Countess |
| `level.py` | General leveling runs |

### Town System (`src/town/`)

`TownManager` orchestrates act-specific town routines. Each act (A1-A5) has its own module with NPC interactions, waypoint usage, and stash handling.

### Inventory (`src/inventory/`)

| File | Purpose |
|---|---|
| `belt.py` | Belt slot management, potion detection |
| `personal.py` | Personal inventory grid, item positions |
| `vendor.py` | Vendor trade window |
| `stash.py` | Personal stash, shared stash |
| `cube.py` | Horadric Cube |
| `common.py` | Shared inventory utilities |

### Item Recognition (`src/item/`)

| File | Purpose |
|---|---|
| `pickit.py` | Pickup decisions, item filtering |
| `consumables.py` | Potion and consumable identification |

BNIP parser (`src/bnip/`) handles item filter rules from `.bnip` files.

### Transmute (`src/transmute/`)

Gem transmutation: collects gems from inventory/stash, performs cube recipes, manages stash destinations.

### Messages (`src/messages/`)

| File | Purpose |
|---|---|
| `messenger.py` | Message dispatcher |
| `discord_embeds.py` | Discord webhook formatting |
| `generic_api.py` | Generic HTTP webhook support |

### Configuration (`src/config.py`)

Singleton that merges config files in priority order:
`custom.ini` > `params.ini` > `game.ini` > `shop.ini` > `transmute.ini`

Supports variable substitution via `[variables]` sections.

### Stealth (`src/utils/stealth.py`)

Three-tier stealth system:
- **Tier 1 (Input)**: Micro-pauses, click variance, key press duration, endpoint wobble
- **Tier 2 (Behavior)**: Wrong waypoint chance, skill mistake chance, skill hesitation
- **Tier 3 (Session)**: AFK breaks, run skipping, personality seed per character

### Utilities (`src/utils/`)

| File | Purpose |
|---|---|
| `misc.py` | Window management, DPI awareness, timing utilities |
| `restart.py` | Game launch/kill, D2R always-on-top |
| `auto_settings.py` | D2R game settings adjustment |
| `key_detector.py` | Auto-detect skill bindings from `.key`/`.keyo` files |
| `graphic_debugger.py` | Visual debugging overlay |
| `node_recorder.py` | Record new path nodes |
| `stealth.py` | Stealth behavior randomization |

## Data Flow

```
D2R Game Window
       │
       ▼
  screen.grab() ──→ Image (numpy array)
       │
       ▼
  template_finder.search() ──→ Position + Validity
       │
       ▼
  ui_manager.detect_screen_object() ──→ Current UI state
       │
       ▼
  bot.py (state machine) ──→ Decides next action
       │
       ▼
  char.run() / pather.go_to() ──→ Movement + Interaction
       │
       ▼
  input_layer.keyboard.send() / mouse.click() ──→ SendInput API
       │
       ▼
  D2R Game Window (response captured on next grab)
```

## Build System

- **Build script**: `build.py` (PyInstaller with `--onefile --noconsole`)
- **Dependencies**: `pyproject.toml`
- **Distribution**: Random exe name, no console window, no kernel drivers
- **Assets**: `assets/` directory copied to build output

## Key Detection

At startup, `key_detector.py` reads the character's `.key`/`.keyo` file from `Saved Games/Diablo II Resurrected/` to auto-detect skill bindings and non-skill keys (inventory, show items, etc.). This eliminates manual key configuration.

## Coordinate Systems

| System | Origin | Used By |
|---|---|---|
| Monitor | Top-left of first monitor | `screen.grab()` |
| Screen | Per-monitor client area | UI detection |
| Absolute | Character at screen center | Pathing, target detection |
| Relative | Template match position | Inventory grid, NPC interaction |

Conversion functions in `screen.py`: `convert_monitor_to_screen()`, `convert_screen_to_abs()`, etc.
