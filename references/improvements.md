# Botty Improvements Implementation Plan

## Phase 1: Key Auto-Detection (Issue #940/#905) [DONE]
- `src/utils/key_detector.py` reads D2R .key/.keyo files
- Auto-fills empty char section hotkeys. Wired into config.py load_data()
- Key normalization: left alt ~ alt, left shift ~ shift
- Test: `tools/test_key_detector.py` and `test/test_key_detector.py` (all pass)

## Phase 2: Target Detection False Positives (Issues #959/#964) [DONE]
- Added aspect ratio filtering in `_add_markers()`
- Rejects health bars (w/h > 3.0) and immune text (w/h < 0.5)
- `TARGET_ASPECT_MIN = 0.5`, `TARGET_ASPECT_MAX = 3.0`

## Phase 3: Pickit Timing (Issue #939) [DONE]
- Added 200-300ms wait after `_yoink_item` pickup
- Prevents bot teleporting before item grab animation completes

## Phase 4: Hardcore Chicken Loop (Issue #942) [DONE]
- Added `hardcore` config flag (default 0)
- On HC death: exits safely instead of infinite restart loop
- Sends discord message if enabled

## Phase 5: Parallel Template Search (Issue #848) [PENDING]
## Phase 6: Async Mouse Moves (Issue #955) [PENDING]
## Phase 7: Auto-Label NPCs (Issue #950) [PENDING]
