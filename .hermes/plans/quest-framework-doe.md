# Quest Framework + Den of Evil Plan

## Goal
Build a quest automation framework in botty that can interact with D2R NPCs, handle dialogue,
track quest progress, and run Den of Evil as the first quest -- all usable by a low-level FoHdin.

---

## Architecture

The quest framework is a new subsystem that plugs into the existing botty state machine.
It follows the same patterns as existing runs (approach -> battle -> return to town) but adds
NPC dialogue interaction and quest state persistence.

### New files

```
src/quest/
    __init__.py                  # Exports
    quest_manager.py             # Quest state machine + persistence (JSON)
    quest_dialogue.py            # OCR-based NPC dialogue interaction
    quest_items.py               # Quest item detection/pickup
    quest_combat.py              # Lightweight combat wrapper (killing trash)
    a1/
        __init__.py
        q_den_of_evil.py         # Den of Evil run
```

### Modified files

```
src/npc_manager.py               # Add TOWN_MAIDEN NPC constant + templates
src/pather.py                    # Add A1_ROARING_CANYON + DoE entrance locations
src/bot.py                       # Add quest state, transitions, handler
src/run/__init__.py              # Export DenOfEvil
src/town/a1.py                   # (optional) Add can_do_den_of_evil method
config/params.ini                # Add run_doe to [routes]
config/bnip/                     # Add town_maiden.png template
```

---

## Phase 1: Foundation

### 1.1 `src/quest/quest_manager.py`

Purpose: Track which quests are done, persist between sessions, dispatch to quest modules.

```python
class QuestManager:
    """Manages quest state: tracks done/available quests per act, persists to JSON."""
    
    # Quest definitions per act
    QUESTS = {
        "a1": ["den_of_evil"],
        "a2": [],  # future: radament, horadric_staff, etc.
        ...
    }
    
    def __init__(self):
        self._state_file = "config/quest_state.json"
        self._state = self._load()
    
    def is_done(self, quest_name: str) -> bool:
        return self._state.get(quest_name, False)
    
    def mark_done(self, quest_name: str):
        self._state[quest_name] = True
        self._save()
    
    def mark_all_done(self, act: str):
        for q in self.QUESTS.get(act, []):
            self._state[q] = True
        self._save()
    
    def next_pending(self, act: str) -> str | None:
        for q in self.QUESTS.get(act, []):
            if not self.is_done(q):
                return q
        return None
    
    def all_done(self, act: str) -> bool:
        return all(self._state.get(q, False) for q in self.QUESTS.get(act, []))
    
    def _load(self) -> dict:
        if os.path.exists(self._state_file):
            with open(self._state_file) as f:
                return json.load(f)
        return {}
    
    def _save(self):
        with open(self._state_file, "w") as f:
            json.dump(self._state, f, indent=2)
```

JSON format (config/quest_state.json):
```json
{
    "den_of_evil": true,
    "search_for_smith": true,
    ...
}
```

### 1.2 `src/quest/quest_dialogue.py`

Purpose: Talk to NPCs, read dialogue options via OCR, click the right branch.
This is the core of quest automation -- it makes the bot "converse" with NPCs.

```python
class QuestDialogue:
    """OCR-based NPC dialogue interaction for quest conversations."""
    
    # ROI at 1280x720
    DIALOGUE_TEXT_ROI = (200, 470, 680, 100)   # NPC speech text
    DIALOGUE_OPTIONS_ROI = (200, 560, 680, 140)  # Player response buttons
    DIALOGUE_CLOSE_Y = 670                       # Close button area
    
    @staticmethod
    def open_dialogue(npc_name: str) -> bool:
        """Walk to NPC and open their dialogue menu."""
        from npc_manager import Npc, open_npc_menu
        return open_npc_menu(getattr(Npc, npc_name.upper()))
    
    @staticmethod
    def read_dialogue() -> dict:
        """OCR the current dialogue box. Returns:
        {
            'npc_text': str,       # What the NPC said
            'options': [str, ...],  # Response options (may be empty if no choice)
            'has_continue': bool   # True if just need to click continue
        }
        """
        img = grab()
        npc_text = ocr_roi(img, self.DIALOGUE_TEXT_ROI)
        options_text = ocr_roi(img, self.DIALOGUE_OPTIONS_ROI)
        # Parse options: split by line, filter out empty, return list
        options = [line.strip() for line in options_text.split('\n') if line.strip()]
        has_continue = len(options) == 0 or "continue" in options_text.lower()
        return {
            'npc_text': npc_text.strip(),
            'options': options,
            'has_continue': has_continue
        }
    
    @staticmethod
    def click_option(option_text: str) -> bool:
        """Find and click a specific dialogue option by matching text via OCR.
        Searches the options ROI for a template match of the option text."""
        img = grab()
        options_img = cut_roi(img, self.DIALOGUE_OPTIONS_ROI)
        # Use template_finder or OCR to locate which button matches
        # Then click at that position
        ...
    
    @staticmethod
    def continue_dialogue() -> bool:
        """Click the close/continue button to advance dialogue."""
        # Click in the close button area
        x, y, w, h = self.DIALOGUE_CLOSE_Y
        mouse.click at center of close area
        ...
    
    @staticmethod
    def follow_conversation(expected_options: list[str]) -> bool:
        """Follow a multi-step conversation:
        - Read NPC text
        - If options present, click the expected one
        - If no options, click continue
        - Repeat until dialogue closes or unexpected text appears
        """
        max_steps = 20  # Safety limit
        for i in range(max_steps):
            dialogue = self.read_dialogue()
            if not dialogue['has_continue'] and dialogue['options']:
                # We have a choice - click the expected option
                for opt in expected_options:
                    if opt.lower() in ' '.join(dialogue['options']).lower():
                        if not self.click_option(opt):
                            return False
                        break
                else:
                    Logger.warning(f"Unexpected dialogue options: {dialogue['options']}")
                    return False
            else:
                # Just continue
                if not self.continue_dialogue():
                    return False
            wait(1.0, 1.5)
            # Check if dialogue box is still visible
            if not is_visible(ScreenObjects.NPCDialogue):
                return True  # Done
        return False  # Hit max steps
```

Key design: `follow_conversation()` takes a list of expected response text. It will
match against whatever options the NPC presents and click the right one. This handles
multi-branch dialogues without hardcoding step-by-step clicks.

### 1.3 `src/quest/quest_combat.py`

Purpose: Lightweight combat for clearing trash during quests. Reuses existing char methods.

```python
class QuestCombat:
    """Combat helpers for quest areas -- reuses existing character combat logic."""
    
    @staticmethod
    def clear_area(pather: Pather, char: IChar, path_nodes: list[int], 
                   timeout: float = 60) -> bool:
        """Walk a path while killing monsters until timeout or all nodes cleared.
        This is the core of DoE: walk down, kill, walk back."""
        return pather.traverse_nodes(path_nodes, char, timeout=timeout, do_combat=True)
    
    @staticmethod
    def wait_for_clear(char: IChar, timeout: float = 15) -> bool:
        """Wait until no monsters are visible (area is clear)."""
        start = time.time()
        while time.time() - start < timeout:
            targets = get_visible_targets()
            if not targets or len(targets) == 0:
                return True
            # Attack if enemies present
            char.attack()
            wait(0.5)
        return False
```

### 1.4 `src/quest/quest_items.py`

Purpose: Detect and pick up quest items (gold glow detection).

```python
class QuestItems:
    """Quest item detection and management."""
    
    @staticmethod
    def detect_quest_items(img: np.ndarray) -> list[tuple[float, float]]:
        """Detect gold-glowing items on screen (quest items).
        Returns list of (x, y) positions in monitor coords."""
        quest_item_mask, _ = color_filter(img, Config().colors.get("gold_glow", [
            (180, 140, 0), (255, 220, 80)
        ]))
        # Find contours, return centers
        ...
    
    @staticmethod
    def pick_up_quest_items(char: IChar, img: np.ndarray = None) -> bool:
        """Find and pick up any quest items currently visible."""
        if img is None:
            img = grab()
        items = self.detect_quest_items(img)
        for pos in items:
            char.pick_up_item(pos, item_name="Quest Item")
            wait(0.5)
        return len(items) > 0
```

---

## Phase 2: NPC & Location additions

### 2.1 Add Town_Maiden to `src/npc_manager.py`

```python
# In class Npc:
TOWN_MAIDEN = "town_maiden"  # Act 1, Roaring Canyon

# In _build_npcs():
Npc.TOWN_MAIDEN: {
    "head": "town_maiden.png",  # Need to capture template
    "actions": {}  # No trade/identify - just dialogue
}
```

The Town Maiden sits in Roaring Canyon (eastern part of Act 1 town). She has a simple
dialogue: you talk to her to "unlock" the Den of Evil entrance, then you talk to her
again after clearing it to get the XP reward and reset it for another run.

### 2.2 Add locations to `src/pather.py`

```python
class Location:
    # ... existing locations ...
    
    # Act 1 Roaring Canyon / Den of Evil
    A1_ROARING_CANYON = "a1_roaring_canyon"       # Town area where Maiden is
    A1_DEN_OF_EVIL_ENTRANCE = "a1_doe_entrance"   # Stairs down to DoE
    A1_DEN_LEVEL_1 = "a1_doe_level_1"
    A1_DEN_LEVEL_2 = "a1_doe_level_2"
    A1_DEN_LEVEL_3 = "a1_doe_level_3"
    A1_DEN_LEVEL_4 = "a1_doe_level_4"
    # (DoE has 3-5 levels depending on game version - need to confirm)
```

Path nodes will need to be added for the Roaring Canyon area and each DoE level.
These are captured via quest_debug.py by walking the path and recording waypoints.

---

## Phase 3: Den of Evil run module

### 3.1 `src/quest/a1/q_den_of_evil.py`

```python
class DenOfEvil:
    """Den of Evil run - Act 1 repeatable quest for XP.
    
    Flow:
    1. Ensure character is in Act 1
    2. Walk to Roaring Canyon (Town Maiden)
    3. Talk to Town Maiden (unlock entrance if needed)
    4. Enter Den of Evil
    5. Pre-buff (FoH + Conviction for FoHdin)
    6. Walk through each level, killing trash
    7. Exit back to Roaring Canyon
    8. Talk to Town Maiden again for reward
    9. Return to town center
    """
    
    name = "run_doe"
    
    # Path nodes per level (to be filled in via quest_debug.py)
    LEVEL_PATHS = {
        1: [],  # Entrance to level 1 stairs
        2: [],  # Level 1 to level 2
        3: [],  # Level 2 to level 3
        4: [],  # Level 3 to level 4 (or final area)
    }
    
    def __init__(self, pather, town_manager, char, pickit, runs):
        self._pather = pather
        self._town_manager = town_manager
        self._char = char
        self._pickit = pickit
        self._runs = runs
        self._quest_manager = QuestManager()
        self._dialogue = QuestDialogue()
    
    def approach(self, curr_loc: Location, do_buff: bool) -> Location | bool:
        """Get to Roaring Canyon and talk to Town Maiden."""
        Logger.info("Run Den of Evil")
        
        # Ensure we're in Act 1
        if TownManager.get_act_from_location(curr_loc) != Location.A1_TOWN_START:
            curr_loc = self._town_manager.go_to_act(1, curr_loc)
            if not curr_loc:
                return False
        
        # Walk to Roaring Canyon (Town Maiden area)
        if not self._pather.traverse_nodes(
            (curr_loc, Location.A1_ROARING_CANYON), self._char, force_move=True
        ):
            return False
        
        # Talk to Town Maiden to unlock/open the Den
        if not self._dialogue.open_dialogue("town_maiden"):
            return False
        
        # Follow the conversation (expect "Oh no, not again" or similar)
        if not self._dialogue.follow_conversation(["Tell me more", "I'll help you"]):
            return False
        
        # Enter the Den
        if not self._pather.traverse_nodes(
            (Location.A1_ROARING_CANYON, Location.A1_DEN_OF_EVIL_ENTRANCE),
            self._char, force_move=True
        ):
            return False
        
        return Location.A1_DEN_OF_EVIL_ENTRANCE
    
    def battle(self, do_pre_buff: bool) -> bool | tuple[Location, bool]:
        """Fight through the Den of Evil."""
        # Pre-buff
        if do_pre_buff:
            if not self._char.pre_buff():
                return False
        
        # Clear each level
        for level in sorted(self.LEVEL_PATHS.keys()):
            Logger.info(f"Clearing Den of Evil level {level}")
            if not self._pather.traverse_nodes(
                self.LEVEL_PATHS[level], self._char, timeout=120, do_combat=True
            ):
                Logger.error(f"Failed to clear DoE level {level}")
                return False
            
            # Pick up any quest items / loot
            self._pickit.pick_up_items(self._char)
            QuestItems.pick_up_quest_items(self._char)
        
        # Walk back to Roaring Canyon
        if not self._pather.traverse_nodes(
            (Location.A1_DEN_OF_EVIL_ENTRANCE, Location.A1_ROARING_CANYON),
            self._char, force_move=True
        ):
            return False
        
        # Talk to Town Maiden for reward
        if not self._dialogue.open_dialogue("town_maiden"):
            return False
        if not self._dialogue.follow_conversation(["Yes", "Thank you"]):
            Logger.warning("Failed to collect DoE reward from Town Maiden")
        
        # Mark as done (for non-repeatable quests) or just return success
        # Note: DoE is repeatable once per real-day, so we DON'T mark permanently done
        # self._quest_manager.mark_done("den_of_evil")  # Only if non-repeatable
        
        return (Location.A1_ROARING_CANYON, True)
```

---

## Phase 4: Bot integration

### 4.1 `src/bot.py` changes

```python
# Add import
from quest.a1.q_den_of_evil import DenOfEvil

# In __init__:
self._do_runs["run_doe"] = Config().routes.get("run_doe")

self._doe = DenOfEvil(self._pather, self._town_manager, self._char, self._pickit, self._do_runs)

# In _states list:
# (No new state needed - DoE uses the existing pattern: town -> doe -> end_run -> town)

# In _transitions list (add):
{ 'trigger': 'run_doe', 'source': 'town', 'dest': 'doe', 'before': "on_run_doe" },

# Add 'doe' to end_run source list:
{ 'trigger': 'end_run', 'source': [..., 'doe'], 'dest': 'town', 'before': "on_end_run" },

# Add end_game source:
{ 'trigger': 'end_game', 'source': [..., 'doe'], 'dest': 'initialization', 'before': "on_end_game" },

# Add handler method:
def on_run_doe(self):
    res = False
    self._do_runs["run_doe"] = False
    self._game_stats.update_location("DoE")
    self._curr_loc = self._doe.approach(self._curr_loc, not self._pre_buffed)
    if self._curr_loc:
        set_pause_state(False)
        res = self._doe.battle(not self._pre_buffed)
    self._ending_run_helper(res)
```

### 4.2 `src/run/__init__.py` changes

```python
# No change needed if DoE lives in src/quest/ (not src/run/)
# But if we want consistency, add:
from quest.a1.q_den_of_evil import DenOfEvil
```

### 4.3 `config/params.ini` changes

```ini
[routes]
; ... existing runs ...
; run_doe              (Act 1 Den of Evil - repeatable daily XP)
order=run_doe
```

### 4.4 `config/params.ini` FoHdin config

For a lvl 1 Paladin running DoE, the params.ini needs:

```ini
[char]
type=fohdin
...

[fohdin]
; FoHdin-specific config for low-level DoE runs
teleport=
; No teleport at lvl 1-9, so pathing is on foot
```

---

## Phase 5: Testing workflow

### What needs user input (I cannot see D2R):

1. **Capture Town_Maiden template:**
   - Go to Roaring Canyon in Act 1
   - Stand near the Town Maiden
   - Run `quest_debug.py`, press F4 (NPC detection)
   - Paste output so I can save the template

2. **Capture DoE path nodes:**
   - Enter the Den of Evil
   - Run `quest_debug.py`, press F1 at each waypoint
   - Walk from entrance through each level
   - Paste outputs so I can build the path arrays

3. **Capture dialogue:**
   - Talk to Town Maiden (both before and after clearing)
   - Run `quest_debug.py`, press F2 (dialogue OCR)
   - Paste output so I can code the conversation flow

4. **Test run:**
   - After I write the code, you run botty with `run_doe` in the route order
   - Report what happens / paste terminal output
   - I iterate based on results

### Lvl 1 Paladin specifics:

- **FoHdin requires FOH skill lvl 6 for Feign of Life passive** -- this needs 3 skill points
  in FoH, meaning character level 9 minimum (or level 4 with a +1 skill weapon)
- Before reaching lvl 9, the bot can still run DoE but will be much more fragile
- Recommended: manually level Paladin to ~lvl 4-5 (short runs in Area 1 or 2) before
  letting the bot solo DoE with FoH
- The bot pathing should handle the walk-through at low speed with heavy FoH spam

---

## Implementation order

1. Write `quest_manager.py` (simple JSON state tracker)
2. Write `quest_dialogue.py` (OCR-based NPC interaction)
3. Write `quest_items.py` + `quest_combat.py` (lightweight helpers)
4. Add Town_Maiden NPC to npc_manager.py
5. Write `q_den_of_evil.py` (skeleton with placeholder paths)
6. Integrate into bot.py (state, transitions, handler)
7. Update params.ini
8. **USER TESTS** -- captures templates, paths, dialogue
9. I fill in the actual path nodes and dialogue based on your captures
10. Full test run and iterate

---

## File tree after implementation

```
my-botty/
├── config/
│   ├── params.ini              # Modified: +run_doe in routes
│   ├── quest_state.json        # New: auto-created by QuestManager
│   └── bnip/
│       └── town_maiden.png     # New: captured template
├── src/
│   ├── quest/                  # New directory
│   │   ├── __init__.py
│   │   ├── quest_manager.py
│   │   ├── quest_dialogue.py
│   │   ├── quest_items.py
│   │   ├── quest_combat.py
│   │   └── a1/
│   │       ├── __init__.py
│   │       └── q_den_of_evil.py
│   ├── npc_manager.py          # Modified: +TOWN_MAIDEN
│   ├── pather.py               # Modified: +A1_ROARING_CANYON, +A1_DEN_* locations
│   ├── bot.py                  # Modified: +doe state, transitions, handler
│   └── run/__init__.py         # Modified: +DenOfEvil export
```
