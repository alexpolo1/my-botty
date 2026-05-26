# Run Cows Route Plan

## Goal
Add a stable `run_cows` route that can:
- create/open Secret Cow Level portal in Act 1,
- clear cows with safe movement and loot handling,
- exit cleanly and continue normal run rotation.

## Scope
This plan is for implementation and testing in this repo only.  
No behavior changes to existing routes unless needed for shared helpers.

## Constraints
- Keep it compatible with current config style (`[routes]`, `[char]`, per-build sections).
- Prioritize stability over speed for first release.
- Avoid forcing hard dependencies on OCR for core route progression.

## Route Design
1. Town prep in Act 1:
   - go to stash/cube workflow position.
   - ensure cube available.
2. Cow portal creation:
   - verify Wirt's Leg + Tome of Town Portal availability.
   - transmute in Act 1 town.
   - detect red portal reliably.
3. Entry and combat:
   - enter portal.
   - execute deterministic clear pattern (clockwise + center sweep).
   - run character-specific attack loop with timeout guard.
4. Loot and exit:
   - reuse existing pickit flow.
   - return through TP or save/exit based on safety state.

## Code Changes (Planned)
1. Add new run module:
   - `src/run/cows.py` (`name = "run_cows"`)
   - methods: `approach()`, `battle()`
2. Wire route registration:
   - include `run_cows` in route loader/dispatcher used by `bot.py`.
3. Town/cube helpers:
   - add minimal helper(s) for cube transmute flow if missing.
4. Pathing/templates:
   - add cow portal/town waypoint templates only as needed.
   - add robust fallback checks for portal detect/select.
5. Config/docs:
   - document `run_cows` in `config/params.ini` route comments.
   - add usage notes to `README.md`.

## Config Additions (Planned)
In `[char]` or dedicated route section:
- `cows_clear_timeout_s` (default safe value, e.g. 90-150)
- `cows_use_tp_exit` (1/0)
- `cows_repair_before_run` (1/0, default 1)

Keep defaults conservative.

## Safety & Recovery
- If portal creation fails: log once, abort current cow attempt, continue next route.
- If portal click fails: retry from known anchor position once.
- If in-combat timeout reached: force exit sequence and mark run failed.
- If inventory full during cows: run pickit stop logic and exit route early.

## Character Compatibility Strategy
Phase 1 support:
- Blizz Sorc
- Hammerdin
- FoHdin

Phase 2 support:
- remaining builds with route-specific combat tuning.

## Telemetry / Stats
Track in `game_stats`:
- `run_cows` attempts
- success/fail count
- elapsed duration
- rune/valuable item outcomes (already covered by global item tracking)

## Test Plan
1. Unit-ish tests:
   - route registration includes `run_cows`
   - config parsing accepts route key without crash
2. Integration smoke (manual):
   - portal creation success path
   - missing Wirt’s Leg failure path
   - missing tome failure path
   - portal click retry path
3. Stability run:
   - 25+ games mixed with existing routes
   - verify no regression in Pindle/Trav/Diablo flows

## Assets / Inputs Needed
- Screenshot set for:
  - Act 1 stash/cube interaction points
  - successful cow portal in town
  - entry location inside cows
- Optional:
  - map movement recording for an efficient clear loop.

## Screenshot + Coordinates SOP (Detailed)

### Why this matters
Cow route reliability depends on visual matching and deterministic interaction points.  
Bad captures (cursor overlap, wrong UI state, mismatched lighting) are the #1 reason for unstable routes.

### Environment lock before capture
1. Use the same D2R setup that bot runtime uses:
   - same resolution,
   - same UI scale,
   - same graphics preset,
   - same window mode.
2. Apply Botty auto settings before capture.
3. Keep panel state consistent:
   - inventory closed unless the step explicitly needs it,
   - item labels in known state,
   - no obstructing chat/quest panels.

### Capture tools in this repo
- `screenshot_tool.py`
- `quest_screenshot_tool.py`
- `quest_debug.py`
- `desktop_snap.py`
- Graphic debugger hotkey from `config/params.ini` (`advanced_options.graphic_debugger_key`)

### Capture types required per target
For every actionable object, collect both:
1. Full-context screenshot (for debugging and reproducibility)
2. Tight template crop (for matching)

Template crop rules:
- include only the unique visual feature + small margin,
- avoid cursor overlap,
- avoid tooltip overlap unless tooltip itself is the detection target,
- avoid over-cropping edges that change with animation.

### Coordinate types to record
For each target interaction, record:
1. Screen/monitor click point used when interaction succeeds.
2. Whether template-center click worked.
3. Optional fallback click point if template-center is unreliable.
4. ROI used (if narrowed in code/tests).
5. Confidence range seen in quick manual validation.

### Mandatory cows capture checklist (in order)
1. Act 1 town anchor (post-spawn)
   - full screenshot
   - possible anchor templates
2. Stash interaction
   - full screenshot near stash
   - stash template crop(s)
   - successful click coordinate(s)
3. Cube interaction/transmute context
   - inventory+cube state screenshot
   - transmute UI screenshot references
4. Cow portal in town (opened)
   - full screenshot with portal visible
   - portal template crops (2-3 variants)
   - portal click success coordinates
5. Cow level entry area
   - immediate post-load screenshot(s)
   - safe first-move anchor capture
6. Exit path reference
   - screenshot where exit action is normally triggered
   - any portal/escape interaction target needed

### Variants to capture for robustness
Per critical template (stash, portal, entry anchor), capture:
- 3-5 samples with slight camera/position variation,
- at least one “busy background” sample,
- one sample with nearby NPC/player clutter if possible.

### Validation pass before route coding
For each template candidate:
1. Verify it matches across the sample set at intended threshold.
2. Verify it does not false-match to nearby unrelated objects.
3. Verify click-at-center triggers the intended interaction.
4. Record accepted threshold and failure notes.

Reject templates that:
- only match at very low confidence,
- require exact pixel-perfect camera alignment,
- frequently collide with non-target objects.

### File naming convention
Use deterministic names aligned with route semantics, e.g.:
- `A1_COW_PORTAL_0`
- `A1_COW_PORTAL_1`
- `A1_STASH_REF_0`
- `COW_ENTRY_ANCHOR_0`

Keep source full screenshots in a dated debug folder and final template crops in the templates location used by the project.

### Capture log format (what testers should write down)
For each target:
- `template_name`
- capture timestamp
- location/context
- successful click point(s)
- confidence range observed
- notes on failed attempts

### Inputs needed from testers (you + friend)
Provide:
1. ZIP/folder of full screenshots + template crops.
2. Short markdown/text capture log using format above.
3. Character/build used during capture (Blizz Sorc / FoH / Hammerdin).
4. Any observed instability notes (miss-clicks, wrong target matches, etc.).

### Acceptance criteria for capture package
Capture package is ready for implementation when:
- all mandatory checklist targets are present,
- each critical target has multi-sample variants,
- at least one tester validated successful interaction per target,
- naming is consistent and unambiguous.

## Rollout
1. Land Phase 1 behind route opt-in (`order=... ,run_cows`).
2. Keep disabled by default in examples until 10+ stable sessions.
3. Promote to documented standard route after stability threshold.

## Definition of Done
- `run_cows` can run repeatedly without manual intervention.
- Failure modes recover without crashing whole bot loop.
- Route is documented in `params.ini` and `README.md`.
- CI/lint/tests pass for changed files.
