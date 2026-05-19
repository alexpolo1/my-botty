# Botty Auto-Quest: Implementation Plan

## 1. Architecture

```
src/quest/
    __init__.py
    quest_manager.py      # State machine, quest sequencing, persistence
    quest_state.py         # JSON-based quest progress tracker
    quest_npc.py           # Generic NPC interaction utilities (talk to NPC, dialogue selection)
    quest_items.py         # Quest item detection and management
    quest_combat.py        # Combat helpers for quest-specific fights
    a1/
        __init__.py        # Act 1 quest runner
        q1a1_smith.py      # Q1: The Search for the Smith
        q1a2_cain.py        # Q2: Tools of the Trade
        q1a3_sacrifice.py  # Q3: Sacrifice
        q1a4_town_portal.py# Q4: The Summoner
        q1a5_skeleton_king.py # Q5: The Shepherd
        q1a6_andariel.py   # Q6: The Fallen Angel
    a2/
        __init__.py        # Act 2 quest runner
        q2a1_jerhyn.py     # Q1: Radament
        q2a2_atheistic.py  # Q2: The Horadric Staff
        q2a3_hephalon.py   # Q3: Tyrael's Breath
        q2a4_atalai.py     # Q4: Secrets
        q2a5_tarbedit.py   # Q5: The Summoner
        q2a6_nihlathak.py  # Q6: The Seven Tombs
        q2a7_duriel.py     # Q7: The Fallen Angel
    a3/
        __init__.py        # Act 3 quest runner
        q3a1_larzuk.py     # Q1: The Forgotten Tower
        q3a2_cain.py        # Q2: The Quest for the Horizon
        q3a3_kaelthas.py   # Q3: The Hellforge
        q3a4_hellgate.py   # Q4: The Hellgate
        q3a5_mephisto.py   # Q5: The Prime Evil
    a4/
        __init__.py        # Act 4 quest runner
        q4a1_izual.py      # Q1: The Fallen Angel
        q4a2_harumony.py   # Q2: The Fallen Angel
        q4a3_diablo.py     # Q3: The Prime Evil
    a5/
        __init__.py        # Act 5 quest runner
        q5a1_ancients.py   # Q1: The Fallen Angel
        q5a2_cain.py        # Q2: The Quest for the Horizon
        q5a3_baal.py       # Q3: The Prime Evil
```

## 2. Quest Manager Design

```python
# quest/quest_manager.py

from enum import Enum
import json, os
from config import Config

class QuestStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class QuestManager:
    _state_file = "config/quest_state.json"

    def __init__(self):
        self.state = self._load_state()
        self.char = None  # reference to IChar
        self.pather = None

    def _load_state(self):
        if os.path.exists(self._state_file):
            with open(self._state_file) as f:
                return json.load(f)
        return self._default_state()

    def _default_state(self):
        # All 25 quests tracked by (act, quest_number)
        return {
            "current_act": 1,
            "quests": {
                "1-1": QuestStatus.PENDING, "1-2": QuestStatus.PENDING,
                "1-3": QuestStatus.PENDING, "1-4": QuestStatus.PENDING,
                "1-5": QuestStatus.PENDING, "1-6": QuestStatus.PENDING,
                "2-1": QuestStatus.PENDING, "2-2": QuestStatus.PENDING,
                "2-3": QuestStatus.PENDING, "2-4": QuestStatus.PENDING,
                "2-5": QuestStatus.PENDING, "2-6": QuestStatus.PENDING,
                "2-7": QuestStatus.PENDING,
                "3-1": QuestStatus.PENDING, "3-2": QuestStatus.PENDING,
                "3-3": QuestStatus.PENDING, "3-4": QuestStatus.PENDING,
                "3-5": QuestStatus.PENDING,
                "4-1": QuestStatus.PENDING, "4-2": QuestStatus.PENDING,
                "4-3": QuestStatus.PENDING,
                "5-1": QuestStatus.PENDING, "5-2": QuestStatus.PENDING,
                "5-3": QuestStatus.PENDING,
            }
        }

    def save(self):
        with open(self._state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def next_quest(self) -> tuple | None:
        """Returns (act, quest_num) of next pending quest, or None if all done."""
        current = self.state["current_act"]
        for qn in range(1, 8):  # max 7 quests per act
            key = f"{current}-{qn}"
            if key in self.state["quests"] and self.state["quests"][key] == QuestStatus.PENDING:
                return (current, qn)
        return None

    def mark_complete(self, act, qn):
        self.state["quests"][f"{act}-{qn}"] = QuestStatus.COMPLETED

    def is_act_complete(self, act):
        for qn in range(1, 8):
            key = f"{act}-{qn}"
            if key in self.state["quests"] and self.state["quests"][key] == QuestStatus.PENDING:
                return False
        return True

    def advance_to_next_act(self):
        """Called when all quests in current act are done."""
        current = self.state["current_act"]
        # ... handle act transition (talk to quest NPC to unlock next act)
        self.state["current_act"] = current + 1
        self.save()

    def run_next_quest(self):
        """Dispatches to the appropriate quest implementation."""
        nxt = self.next_quest()
        if not nxt:
            return
        act, qn = nxt
        self.state["quests"][f"{act}-{qn}"] = QuestStatus.IN_PROGRESS
        # Route to quest implementation
        # ... call quest module
```

## 3. Quest NPC Interaction

Every quest requires talking to NPCs. The existing `npc_manager.py` has `talk_to_npc()` which we extend.

```python
# quest/quest_npc.py
# Utilities for NPC dialogue selection

from utils.custom_mouse import mouse
from utils.misc import wait
from template_finder import search_and_wait
from screen import grab

def talk_and_select(dialogue_choice: str, npc_name: str):
    """
    Talk to NPC and select a specific dialogue option.
    botty already detects NPC and opens dialogue. We need to click
    the specific dialogue button.
    """
    from npc_manager import talk_to_npc
    talk_to_npc(npc_name)
    wait(1)
    # D2R shows dialogue options in a box at bottom center.
    # Detect the text of each option using OCR and click the matching one.
    click_dialogue_option(dialogue_choice)

def click_dialogue_option(text: str):
    """
    Use OCR to read dialogue options and click the one containing the given text.
    """
    from d2r_image.ocr import image_to_text
    img = grab()
    roi = (300, 530, 680, 190)  # dialogue box area
    result = image_to_text(cut_roi(img, roi), psm=6)
    for line in result.text.split('\n'):
        if text.lower() in line.lower():
            # Click near the center of this text line
            # ... (use OCR bounding box to find click position)
            break

def check_quest_item_on_screen() -> bool:
    """Detect if a quest item tooltip is visible (gold item name)."""
    # Quest items have a gold/purple glow. Detect by color.
    img = grab()
    roi = (400, 400, 200, 200)  # quest item pickup area
    # Check for gold-colored pixels indicating a quest item
    ...
```

## 4. Quest Item Tracking

Quest items (keys, scrolls, weapons) need to be tracked. We extend the inventory system.

```python
# quest/quest_items.py

QUEST_ITEMS = {
    "stone_of_jah": "Stone of Jah",
    "hephaestons_key": "Hephaston's Key",
    "tal_rashas_will": "Tal Rasha's Will",
    "keys_to_the_crypt": "Keys to the Crypt",
    "harumony": "Harumony",
    "ancients_battle_order": "Ancient's Battle Order",
    "horadric_cube": "Horadric Cube",
    "horadric_staff": "Horadric Staff",
    "amulet_of_the_vipers": "Amulet of the Vipers",
}

def has_quest_item(name: str) -> bool:
    """Check if quest item is in inventory."""
    # Use OCR to scan inventory for item name
    # OR check by item template matching (faster)
    ...

def equip_quest_item(name: str):
    """Click on quest item in inventory to equip it."""
    ...

def pickup_quest_item():
    """Detect and pickup quest items on ground (gold glow)."""
    # Quest items have a gold/purple glow around them
    # Detect with color thresholding
    ...
```

## 5. Quest Combat

Most quests involve fighting a boss or clearing a path. Botty already has combat logic.

```python
# quest/quest_combat.py

from char.i_char import IChar
from pather import Pather

def kill_boss(boss_name: str, atk_len: float, char: IChar, pather: Pather):
    """
    Navigate to boss, fight until dead.
    Reuses botty's existing kill_* methods from run/*.py
    """
    # 1. Find boss on screen
    # 2. Move to boss position
    # 3. Attack until dead (same as run/trav.py)
    # 4. Return to town
    ...

def clear_room(char: IChar, pather: Pather):
    """Clear a room of monsters (for quests requiring room clearance)."""
    # Same logic as pather.follow_path() but with combat
    ...
```

## 6. Integration with Bot State Machine

The existing bot uses a state machine (transitions library). We add quest states.

```python
# bot.py changes

# Add quest states to the state machine
self._states = self._states + [
    'quest', 'quest_act_transition'
]

# Add quest transitions
self._transitions = self._transitions + [
    {'trigger': 'run_quest', 'source': 'town', 'dest': 'quest', 'before': 'on_run_quest'},
    {'trigger': 'end_quest', 'source': 'quest', 'dest': 'town', 'before': 'on_end_quest'},
    {'trigger': 'act_transition', 'source': 'town', 'dest': 'quest_act_transition',
     'before': 'on_act_transition'},
]

def on_run_quest(self):
    """Start next quest."""
    from quest.quest_manager import QuestManager
    qm = QuestManager()
    nxt = qm.next_quest()
    if nxt:
        act, qn = nxt
        quest_func = self._get_quest_function(act, qn)
        quest_func()
        qm.mark_complete(act, qn)
        qm.save()

def on_end_quest(self):
    """After a quest completes, check if act is done."""
    qm = QuestManager()
    if qm.is_act_complete(self.current_act):
        self.trigger_or_stop('act_transition')
    else:
        self.trigger_or_stop('run_quest')

def on_act_transition(self):
    """Transition to next act (talk to NPC, unlock next act)."""
    qm = QuestManager()
    qm.advance_to_next_act()
    # ... handle act transition logic
    self.trigger_or_stop('start_from_town')
```

## 7. Configuration

Add to `params.ini`:

```ini
[quest]
; Enable quest mode (disables farming runs until quests are done)
enabled = 1

; Skip quests that are too dangerous for your character level
; 0 = run all quests, 50 = skip quests below level 50
min_level = 0

; Auto-stash quest items between acts
auto_stash_quest_items = 1

; Continue farming after all quests are done
farm_after_quest = 1
```

## 8. Implementation Order

### Phase 1: Foundation (Quest Manager + NPC Interaction)
- quest_manager.py with state tracking
- quest_npc.py for dialogue interaction
- quest_state.py for persistence

### Phase 2: Act 1 (6 quests)
- Q1: Search for the Smith (kill Rats, talk to Charsi)
- Q2: Tools of the Trade (get items from Andariel's lair)
- Q3: Sacrifice (kill Skeletons at Crypt)
- Q4: The Summoner (kill Summoner in Catacombs)
- Q5: The Shepherd (kill Skeleton King + Gargothon)
- Q6: The Fallen Angel (kill Andariel)

### Phase 3: Act 2 (7 quests)
- Q1: Radament
- Q2: The Horadric Staff (combine Cube + Scroll)
- Q3: Tyrael's Breath (clear Sewers, talk to Alkor)
- Q4: Secrets (activate 4 stone tablets)
- Q5: The Summoner (kill Duriel)
- Q6: The Seven Tombs (kill all 7 tomb bosses)
- Q7: The Fallen Angel (kill Duriel again)

### Phase 4: Act 3 (5 quests)
- Q1: The Forgotten Tower
- Q2: The Quest for the Horizon (Cain)
- Q3: The Hellforge
- Q4: The Hellgate
- Q5: The Prime Evil (Mephisto)

### Phase 5: Act 4 (3 quests)
- Q1: The Fallen Angel (Harumony)
- Q2: The Fallen Angel (Tal Rasha's Will)
- Q3: The Prime Evil (Diablo)

### Phase 6: Act 5 (3 quests)
- Q1: The Fallen Angel (Ancient's Battle Order)
- Q2: The Quest for the Horizon (Cain)
- Q3: The Prime Evil (Baal)

## 9. Testing Strategy

1. Test each quest independently in singleplayer
2. Test quest-to-quest transitions
3. Test act transitions
4. Test recovery from death during quest
5. Test with different character builds

## 10. Challenges

- **NPC dialogue**: D2R has branching dialogue. Need to handle all paths.
- **Quest items**: Some quests require carrying specific items (keys, weapons).
- **Room secrets**: Act 2 Q4 requires finding hidden passages.
- **Multi-stage quests**: Some quests span multiple areas (Act 3 Q2-4).
- **Character level**: Quests are designed for specific levels. A level 90 character kills everything too fast/slow.
- **Anti-cheat**: Questing is more visible to anti-cheat than farming. Need stealth settings.
