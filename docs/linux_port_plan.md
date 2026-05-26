# Linux Port Plan (Botty)

## Goal
Make Botty runnable on Linux in phased steps, with clear checkpoints and minimal regressions for current Windows users.

## Current status
Botty is currently Windows-first. Full gameplay flow does not run on Linux due to:
- Windows input stack (`win_input`, Win32 hotkey polling).
- Windows process/window management (`taskkill`, Win32 window APIs, `os.startfile`).
- Windows dependency assumptions (`pywin32`, Windows tesserocr wheel guidance).
- Windows path/env assumptions (`APPDATA`, `C:\...`, `D2R.exe`, `.bat` scripts).

## Principles
- Keep Windows behavior unchanged while adding Linux support.
- Introduce platform abstractions before replacing implementations.
- Land small, testable phases.
- Prefer graceful `NotImplemented` behavior over hard crashes on unsupported paths.

## Phase 1: Platform abstraction layer
1. Add a `platform_adapter` module with interfaces for:
   - Input (keyboard/mouse send + hotkeys)
   - Window management (find game window, set top-most, geometry)
   - Process control (start/stop/check D2R/Battle.net)
2. Route existing Windows calls through adapters.
3. Add Linux stub implementations that fail gracefully with actionable logs.
4. Add unit tests for adapter selection and fallback behavior.

## Phase 2: Linux-safe startup and tooling
1. Add Linux entry script (`run_botty.sh`) and dependency checker shell script.
2. Update startup to avoid Windows-only calls unless platform is Windows.
3. Normalize path handling to `pathlib` where feasible.
4. Ensure `main.py` can start on Linux without immediate import/runtime crashes.

## Phase 3: Linux input backend
1. Implement Linux input backend (X11/Wayland-compatible strategy):
   - Candidate libs: `pynput`, `python-xlib`, or tool-backed approach (`xdotool` for X11).
2. Match required Botty features:
   - Key press/hold/release
   - Mouse move/click with jitter and timing controls
   - Hotkey registration/polling
3. Add integration tests/mocks for input primitives.

## Phase 4: Linux screen/window backend
1. Validate capture compatibility for `mss` under target Linux desktop/session.
2. Implement Linux window discovery/focus/geometry handling.
3. Rework DPI/coordinate normalization independent of Win32 APIs.
4. Add diagnostics tool to verify coordinates, capture ROI, and template matching on Linux.

## Phase 5: Process and launcher integration
1. Linux-compatible process management (replace `taskkill` paths).
2. Replace `os.startfile` launcher logic with cross-platform process spawning.
3. Add platform-specific config defaults for game executable path conventions.

## Phase 6: Dependency and OCR strategy
1. Split dependencies by platform (base + windows extras + linux extras).
2. Document Linux OCR setup (tesseract/leptonica packages + python bindings).
3. Add CI matrix entries:
   - Windows: full current pipeline
   - Linux: import/startup + unit/integration subset first, expand later

## Phase 7: Feature parity validation
1. Verify end-to-end flows:
   - Start game, run cycle, maintenance, save/exit, restart handling
2. Validate pickit, stash/sell, discord messaging, stats logging.
3. Benchmark timing-sensitive routines and tune Linux defaults.

## Risk register
- Wayland restrictions can block synthetic input/screen capture depending on compositor.
- Template matching thresholds may differ due to capture pipeline differences.
- Hotkey handling behavior can differ across desktop environments.
- OCR reliability can vary based on font rendering stack.

## Suggested delivery milestones
1. **M1**: Linux no-crash startup + stubs + docs.
2. **M2**: Linux input backend functional in sandbox diagnostics.
3. **M3**: Linux screen/window backend and maintenance loop stable.
4. **M4**: End-to-end run support in supported Linux environments.

## Acceptance criteria
- Botty starts on Linux and logs clear capability status.
- No Windows-only hard failures on Linux code paths.
- Core run loop can execute in a supported Linux environment.
- Windows behavior remains stable and covered by existing tests/CI.
