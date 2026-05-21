# Botty Stealth - Deep Dive

## What Warden (Battle.net Anti-Cheat) Can Detect

Warden is a kernel-level anti-cheat. It can:
- **Enumerate processes** - see `main.exe` running, check the process name and parent
- **Scan loaded DLLs** - look for known botting libraries (keyboard_io.dll, mousetool.dll, pyclick)
- **Monitor API calls** - detect patterns in `SendInput` frequency and timing
- **Analyze input timing** - bots have perfectly consistent timing; humans don't
- **Check mouse trajectory** - bots move in straight lines; humans move in curves
- **Monitor memory** - detect hooks, injected code, or unusual data patterns

## Our Stealth Strategy (3 Tiers)

### Tier 1: Input-Level Stealth (Already Working)

**What we fixed:**
- Removed `keyboard` library (installed `keyboard_io.dll` kernel driver - instant detection)
- Removed `mouse`/`pyclick` library (installed `mousetool.dll` kernel driver - instant detection)
- Replaced with `ctypes` + `user32.dll` `SendInput` (standard Windows API, no drivers)
- Hidden the console window (`--noconsole`) so no visible CMD window
- Randomized the exe name from `main.exe` to something like `whvitjz2.exe`

**Mouse movement stealth (in `input_layer/mouse_impl.py`):**
- Every `mouse.move()` generates a Bezier curve with random control points
- Gaussian distortion applied to the curve (simulates hand tremor)
- Endpoint wobble - final position is 2-5 pixels off, then corrected
- Click variance - target position is randomized by +/-8px (configurable)
- Arrival-to-click delay - 50-800ms pause between arriving and clicking (beta distribution)
- Distance-based timing - closer clicks are faster, farther clicks take longer
- Human curve complexity multiplier from config (default 1.0)

**Keyboard stealth (in `input_layer/__init__.py`):**
- Every `keyboard.send()` includes micro-pauses before and after (20-120ms)
- Key press duration varies (20-200ms, exponential distribution - most short, some linger)
- Combo keys (e.g. `shift + a`) press modifiers individually with timing between

**What's NOT yet wired:**
The stealth functions `human_key_press()` and `human_keyboard_send()` exist in `utils/stealth.py` but are called via the input layer shim automatically. Every `keyboard.send()` now gets stealth timing.

### Tier 2: Behavior-Level Stealth (Partially Integrated)

**Functions defined but NOT called from anywhere in char code:**

| Function | What it does | Where it SHOULD be used |
|---|---|---|
| `should_wrong_waypoint()` | 2.5% chance of clicking wrong waypoint | `ui/waypoint.py` when selecting TP portal |
| `skill_rotation_hesitation()` | 80-300ms pause before casting | Before every skill cast in char files |
| `should_correct_skill_mistake()` | 1.5% chance of miscasting then correcting | During skill rotation in combat |
| `randomize_click_position()` | Gaussian click offset | Before every `mouse.click()` |

**Current gap:** These functions exist but are NOT called from the character combat code. The char files call `keyboard.send("1")` directly without going through a stealth wrapper. The input layer adds micro-pauses, but the behavior-level stealth (wrong skill, hesitation) is not wired in.

**What IS wired:**
- `mouse.stealth_move()` calls `randomize_click_position()` and `endpoint_wobble()` automatically
- `mouse.click()` calls `apply_click_delay()` automatically
- `keyboard.send()` calls `_stealth_before()` / `_stealth_after()` (micro-pauses) and `_stealth_duration()` (variable press duration)

### Tier 3: Session-Level Stealth (Fully Working)

**Fully integrated in `bot.py`:**

| Function | Config | Behavior |
|---|---|---|
| `should_skip_run()` | `skip_run_chance = 10` | 10% chance to skip a run entirely (randomizes runtime) |
| `maybe_afk_break()` | `afk_break_chance = 5` | 5% chance after each run to take a 2-12 minute break |
| Run reshuffle | `reshuffle_each_rotation = 1` | Re-shuffles run order after each full rotation |
| `randomize_run_duration()` | `run_duration_variance = 0.15` | +/-15% variation on expected run time |
| Wait jitter | `wait_jitter_min = 0.85` / `max = 1.20` | Every `wait()` call is multiplied by 0.85x-1.20x |

## Current Stealth Summary

| Vector | Status | Notes |
|---|---|---|
| Kernel drivers | FIXED | No keyboard_io.dll or mousetool.dll |
| Process name | PARTIAL | Randomized but still visible as a running process |
| Console window | FIXED | `--noconsole` hides the window |
| Mouse trajectory | WORKING | Bezier curves + Gaussian distortion + wobble |
| Click timing | WORKING | 50-800ms arrival-to-click delay + click variance |
| Key press timing | WORKING | 20-200ms variable duration + micro-pauses |
| Run timing | WORKING | 10% skip chance, 5% AFK break, +/-15% duration variance |
| Wait jitter | WORKING | 0.85x-1.20x on all waits |
| Wrong waypoint | WORKING (2.5%) | Wired in waypoint.py |
| Skill mistakes | WORKING (1.5%) | Wired in input_layer/__init__.py |
| Skill hesitation | WORKING (80-300ms) | Wired in input_layer/__init__.py |

## Remaining Risks

1. **Process visibility**: Warden can still see a hidden process running alongside D2R. The exe name is random but the timing of when it starts (right when D2R launches) is suspicious.

2. **Click pattern analysis**: Even with Bezier curves, Warden might detect that every "path click" follows a curve while a human sometimes double-clicks or moves in straight lines.

3. **No idle mouse movement**: When the bot is fighting or waiting, the mouse is perfectly still. Humans constantly fidget with the mouse.

4. **Skill mistake only on 1-0 keys**: The skill mistake feature only fires for skill hotkeys (number keys 1-0). It doesn't apply to inventory keys, stand_still, or other non-skill actions.

## What Would Improve Stealth Further

### High Impact (Warden likely checks these)
1. **Idle mouse movement**: Add background thread that moves mouse 1-3 pixels randomly every 1-5 seconds (simulates hand resting on mouse)
2. **Occasional straight-line clicks**: 10% of the time skip the Bezier curve and click directly (humans don't always move in curves)

### Medium Impact
3. **Process parent spoofing**: Launch the bot from a different process (e.g. from Explorer instead of directly) to hide the relationship with D2R
4. **Variable scroll speed**: Add variance to `mouse.wheel()` calls (inventory scrolling)
5. **Right-click variation**: Sometimes right-click to cancel actions before re-doing them

### Low Impact (but good for completeness)
6. **Randomize AFK break more**: Current range is 2-12 minutes, could be wider
7. **Add personality per character**: Different timing distributions per character seed
8. **Typing delays**: When using text chat (if implemented), add keystroke-by-keystroke delays
