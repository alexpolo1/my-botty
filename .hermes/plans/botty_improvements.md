# Botty Improvements Implementation Plan

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Done
- [-] Cancelled / low priority

---

## Phase 1: Key Auto-Detection (Issue #940)
Read D2R .key file and auto-fill hotkeys.

- [x] Create src/utils/key_detector.py module
- [x] VK code mapping (partial — needs review for accuracy)
- [x] Parse .key file (text format: VK action_type param)
- [x] Auto-fill empty [char] hotkeys from detected bindings
- [x] Auto-fill build-specific skill hotkeys (fohdin, hammerdin, etc.)
- [x] Wire into config.py load_data()
- [ ] REVIEW: Verify VK_MAP accuracy (D2R uses its own VK offset scheme)
- [ ] REVIEW: Skill slot-to-config matching is heuristic — may misassign
- [ ] TEST: Verify against actual D2R .key file on user's machine

## Phase 2: Target Detection False Positives (Issues #959/#964)
Health bars and "immune to X" text mistaken for targets.

- [ ] Analyze current get_visible_targets() in target_detect.py
- [ ] Add shape/size filtering: health bars are thin horizontal strips, immune text is small
- [ ] Add aspect ratio check: real targets (poison/freeze auras) are roughly circular/elliptical
- [ ] Add minimum bounding box height constraint (filter out thin text)
- [ ] Optionally: add color temperature check (immune text is yellow/gold, not blue/green)
- [ ] Test with screenshots of edge cases

## Phase 3: Pickit Timing Fix (Issue #939)
Items skipped because bot teleports away before grabbing.

- [ ] Review pickit.py _yoink_item() for timing issues
- [ ] Add configurable pickup_delay parameter (current: fixed timing)
- [ ] Add retry logic: if item still visible after pickup attempt, re-try
- [ ] Add "slow mode" for large/heavy items (framed/magic items may animate longer)
- [ ] Ensure bot doesn't teleport until pickup animation completes
- [ ] Test: verify no "Attempt to pick xyz" warnings followed by teleport

## Phase 4: Parallel Template Search (Issue #848)
Speed up template_finder.search() with threading.

- [ ] Add ThreadPoolExecutor-based search_all_parallel() 
- [ ] Keep existing search() for single-template (no overhead)
- [ ] Only parallelize when searching >3 templates simultaneously
- [ ] Benchmark: measure speedup on typical 1280x720 grab

## Phase 5: Async Mouse Moves (Issue #955)
Non-blocking mouse movement.

- [ ] Add async_move() to utils/custom_mouse.py
- [ ] Run movement in background thread
- [ ] Add is_moving() / wait_for_move() synchronization
- [ ] Integrate into game_controller.py for smoother action chains

## Phase 6: Hardcore Chicken Loop Fix (Issue #942)
Prevent infinite death loops on Hardcore characters.

- [ ] Review death_manager.py chicken logic
- [ ] Add max_chicken_count config parameter (default: 3)
- [ ] If max chicken count exceeded on HC, exit gracefully instead of re-entering
- [ ] Add defensive chicken config option (chicken to TP instead of full chicken)
- [ ] Test: verify HC character exits cleanly after N deaths

## Phase 7: Auto-Label NPCs (Issue #950)
Learn vendor identities automatically during gameplay.

- [ ] During town states, detect NPC name plates via OCR
- [ ] Cross-reference detected names with known NPC list
- [ ] Auto-capture NPC templates when confidence is high
- [ ] Store learned templates in assets/npc/
- [ ] This is a long-term feature — lower priority

---

## Priority Order (implement in this order)
1. **Phase 1** - Key auto-detection (already partially done, needs review + test)
2. **Phase 3** - Pickit timing (high impact on loot collection)
3. **Phase 2** - Target detection (high impact on kill reliability)
4. **Phase 6** - Hardcore chicken fix (safety critical)
5. **Phase 4** - Parallel template search (performance)
6. **Phase 5** - Async mouse moves (quality of life)
7. **Phase 7** - Auto-label NPCs (long-term feature)
