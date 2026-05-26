# Auto Skill + Attribute Allocation Plan

## Goal
Add an optional system that automatically assigns:
- skill points
- attribute points

based on:
- active character profile (`blizz_sorc`, `fohdin`, `hammerdin`, etc.)
- current character level

without breaking existing manual setups.

## Scope
- Planning and architecture for Botty repo.
- No forced behavior changes: feature must be opt-in.

## Requirements
1. Determine current level reliably at runtime.
2. Select a build template by character profile.
3. Apply points safely only when unspent points exist.
4. Record every allocation in logs/events for audit/replay.
5. Abort safely on uncertainty (wrong UI state, OCR mismatch, missing templates).

## Current Level Detection Strategy

### Primary path
Use `player_bar.get_experience()` (already used in `game_stats.log_exp`) to derive level from XP table.

### Secondary fallback
Open character panel (`C`) and OCR level/name line directly from upper-left panel region.

### Tertiary fallback
If OCR fails repeatedly:
- keep previous known good level for session,
- do **not** allocate points until confidence is restored.

### Confidence rules
- Require two consistent reads before first allocation in a session.
- Reject impossible jumps (e.g., +5 levels at once).
- Persist `last_known_level` in session stats snapshot.

## Build Template Model

Add config-backed build templates, e.g.:
- `config/auto_builds/blizz_sorc.ini`
- `config/auto_builds/hammerdin.ini`
- `config/auto_builds/fohdin.ini`

Each template defines per-level targets:
- desired skill totals by level milestone
- desired attribute distribution (str/dex/vit/ene)

Example concept:
- Level 1-17: early progression targets
- Level 18-29: mid-game unlock path
- Level 30+: core skill maxing order

## Runtime Flow
1. Enter town and open character/skill UI.
2. Detect level and unspent points.
3. Load template for `Config().char["type"]`.
4. Compute delta between current allocation and target-at-level.
5. Apply points stepwise:
   - attributes first (optional toggle),
   - skills second.
6. Verify post-apply state.
7. Log allocation summary and persist snapshot.

## Safety Guards
- Only run in town.
- Require stash/vendor windows closed.
- Hard cap per cycle (e.g., max 10 clicks per stat/skill group).
- On mismatch/timeout:
  - stop allocation immediately,
  - screenshot + structured error event,
  - continue bot without crashing.

## Config Additions (Planned)
In `[char]` or new `[auto_build]` section:
- `auto_assign_skills=0/1`
- `auto_assign_attributes=0/1`
- `auto_build_profile=` (defaults to `char.type`)
- `auto_build_check_every_x_games=`
- `auto_build_safe_mode=1` (extra verification)

## Logging / Telemetry
Add structured events:
- `auto_build_check_started`
- `auto_build_level_detected`
- `auto_build_points_detected`
- `auto_build_applied`
- `auto_build_skipped`
- `auto_build_error`

Include:
- profile
- level
- points spent
- before/after snapshots

## UI / Input Dependencies
Need stable template references for:
- character panel level region
- unspent attribute points indicator
- unspent skill points indicator
- individual plus-buttons for stats/skills

## Test Plan
1. Unit tests:
   - level-to-target mapping
   - delta computation
   - guard conditions
2. Integration dry-run mode:
   - compute and log planned actions without clicking.
3. Live smoke tests per profile:
   - `blizz_sorc`, `hammerdin`, `fohdin`
4. Regression:
   - ensure normal runs unaffected with feature disabled.

## Inputs Needed From You
1. Screenshots for each supported class at:
   - character panel open,
   - skill tree open,
   - visible unspent points.
2. Preferred leveling templates:
   - exact skill priority order by level range.
   - attribute rules (e.g., str to gear breakpoint, then vit).
3. Whether respec-aware logic is needed in v1.

## Rollout Phases
1. Phase 1: Level detection + dry-run planner only.
2. Phase 2: Attribute auto-assign (safer, fewer UI branches).
3. Phase 3: Skill auto-assign with full verification.
4. Phase 4: Expanded profile templates + docs.

## Definition of Done
- Feature is opt-in and stable for `blizz_sorc`, `hammerdin`, `fohdin`.
- Level detection is reliable with fallback behavior.
- No crash on detection/allocation failure.
- Full logs available for every auto-allocation decision.
