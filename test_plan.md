# Botty Singleplayer Test Plan

## Pre-Flight Checklist

Before running, verify:
- [ ] D2R installed and running at 1280x720 windowed
- [ ] D2R language is English
- [ ] Offline play is available (no battle.net required for singleplayer)
- [ ] Character is a sorceress with Town Portal + Teleport (level 65+)
- [ ] Belt setup: Col 1=HP potions, Col 2=MP potions, Col 3-4=Rejuv
- [ ] Skill hotkeys match params.ini:
  - F1 = Nova (right skill, pre-selected)
  - F3 = Energy Shield, F4 = Frozen Armor, F5 = Static Field
  - 5 = Teleport, 6 = Town Portal
  - W = weapon switch, 7 = Battle Orders, 8 = Battle Command


## Phase 1: Launch Test

Goal: Verify botty starts without import errors.

1. Open cmd, activate the botty env:
   conda activate botty
   cd C:\Users\alex\Downloads\my-botty

2. Run: python src\main.py

Expected:
- "============ Botty 0.8.1-dev [name: bigfont] ============="
- Hotkey table (F7, F8, F9, F10, F11, F12)
- Console idles waiting for hotkey input
- No Python errors in console

If it crashes here, we fix the import error before proceeding.


## Phase 2: Auto Settings

Goal: Apply the required D2R graphics settings so botty's template matching works.

Preparation:
- D2R must be running (on main menu or character selection)
- Press F9 in botty console

Expected:
- Botty reads your Settings.json and rewrites it
- Botty sets launch options: -mod bigfont -txt
- Console prints: "Adapted settings successfully"
- You restart D2R and it runs at 720p with low settings

After this, restart D2R once.


## Phase 3: Character Selection

Goal: Botty detects the character selection screen and clicks Play.

1. Start D2R, navigate to character selection
2. Highlight your Nova sorc character (left-click it)
3. Make sure the "Offline" tab is selected (bottom left of char selection)
4. Press F11 in botty

Expected console output:
- "Wait for Play button" / "Found Play Btn"
- D2R difficulty key pressed (H = Hell)
- D2R loading screen appears (black screen)

Press F12 to stop botty once the loading screen appears.

If botty can't find the Play button:
- Make sure D2R is at 720p windowed (not fullscreen, not borderless)
- Make sure the window is not minimized


## Phase 4: Full Run Cycle (Travincal)

Goal: Complete first run without manual intervention.

1. D2R at character selection, sorc selected
2. Press F11
3. Watch botty:
   - Selects character, starts game
   - Loads into town (Kurast for Act 3 / Lut Gholein)
   - Pre-buffs: Energy Shield -> Battle Orders -> Battle Command
   - Casts Town Portal on ground, steps through
   - Teleports to Travincal area, enters the dungeon
   - Finds Travincal, attacks with Nova (right click)
   - Travincal dies
   - Picks up loot
   - Town Portal back to town
   - Save & Exit
   - Returns to hero selection
   - Restarts automatically

Watch for problems:
- Character doesn't move -> check Always Run is ON
- Character doesn't attack -> check Nova is pre-selected right skill
- Character doesn't TP -> check teleport hotkey (5)
- Character gets stuck pathing -> bot may need to adjust, or D2R settings off


## Phase 5: Second Run (Eldritch/Shenk)

After Trav completes, botty starts a new game and does the second configured run. Same flow, different destination.


## Phase 6: Multi-Game Stability

Run 5-10 complete rotations without touching the keyboard. Watch for:
- Consistent runs (no crashes or freezes)
- Potions being consumed
- Bot recovering from failures (auto-restart via chicken/save-and-exit)
- Memory/Python stability


## Hotkeys

F9  = Auto Settings (reconfigure D2R graphics)
F11 = Start/Pause bot
F12 = Stop bot


## Troubleshooting

- "No play button found" -> D2R not at main menu, or wrong resolution
- Character doesn't move -> "Always Run" not enabled in D2R options
- Character doesn't attack -> right skill not set to Nova, or hotkey wrong
- "Failed to detect MAIN_MENU" -> restart D2R, make sure window is visible
- OCR errors on character name -> ensure -mod bigfont is in launch options
