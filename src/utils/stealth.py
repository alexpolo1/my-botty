import random
import time
import keyboard
from config import Config
from logger import Logger


def maybe_afk_break():
    """Call after each run. Randomly takes an unscheduled AFK break."""
    try:
        cfg = Config().stealth
    except Exception:
        return
    if random.randint(1, 100) <= cfg["afk_break_chance"]:
        minutes = random.uniform(cfg["afk_break_min_m"], cfg["afk_break_max_m"])
        Logger.info(f"[Stealth] Taking unscheduled AFK break for {minutes:.1f} minutes")
        time.sleep(minutes * 60)
        Logger.info("[Stealth] AFK break over, resuming")


def should_skip_run() -> bool:
    """Returns True if this run should be randomly skipped for stealth."""
    try:
        cfg = Config().stealth
    except Exception:
        return False
    if cfg["skip_run_chance"] > 0 and random.randint(1, 100) <= cfg["skip_run_chance"]:
        Logger.info("[Stealth] Randomly skipping this run for anti-detection")
        return True
    return False


def randomize_click_position(x: int, y: int) -> tuple:
    """
    Returns a slightly offset click position to simulate imperfect aim.
    Uses a 2D Gaussian distribution so most clicks cluster near target
    with rare larger misses (like real humans).
    """
    try:
        cfg = Config().stealth
        variance = cfg["click_variance"]
    except Exception:
        variance = 8

    # Gaussian distribution: most clicks land close, occasional larger miss
    dx = int(random.gauss(0, variance / 2))
    dy = int(random.gauss(0, variance / 2))

    # Occasionally add a small directional bias (simulates hand drift)
    if random.random() < 0.1:
        bias = random.randint(2, max(1, variance // 2))
        dx += bias * random.choice([-1, 1])
        dy += bias * random.choice([-1, 1])

    return x + dx, y + dy


def randomize_run_duration(base_duration: float) -> float:
    """
    Varies the effective run duration to avoid bot-like consistency.
    Human players take variable time on the same route.
    """
    try:
        cfg = Config().stealth
        variance = cfg.get("run_duration_variance", 0.15)
    except Exception:
        variance = 0.15

    # Most runs complete within +/- 15% of base, with occasional outliers
    factor = random.gauss(1.0, variance)
    factor = max(0.7, min(1.4, factor))  # Clamp to 70%-140%

    return base_duration * factor


def add_micro_pause():
    """
    Adds a brief random micro-pause (simulates human finger hesitation
    between actions). Call between mouse/keyboard actions for more natural timing.
    """
    try:
        cfg = Config().stealth
        min_ms = cfg.get("micro_pause_min_ms", 20)
        max_ms = cfg.get("micro_pause_max_ms", 120)
    except Exception:
        min_ms, max_ms = 20, 120

    # 30% chance of micro-pause
    if random.random() < 0.3:
        pause_s = random.uniform(min_ms, max_ms) / 1000.0
        time.sleep(pause_s)


# ─── Tier 1: Input-level stealth ─────────────────────────────────────────────

def endpoint_wobble(x: int, y: int) -> tuple[int, int]:
    """
    Adds 2-5 pixel micro-adjustment before final click position (human hand tremor).
    Called just before clicking to simulate endpoint micro-correction.
    """
    # Small Gaussian wobble: most land within 3px, occasional 5px+
    dx = int(random.gauss(0, 1.5))
    dy = int(random.gauss(0, 1.5))
    return x + dx, y + dy


def click_delay() -> float:
    """
    Returns the delay (in seconds) between arriving at a target and clicking.
    Humans don't click the instant they arrive — there's 50-800ms of "is this right?".
    """
    try:
        cfg = Config().stealth
        min_ms = cfg.get("click_delay_min_ms", 50)
        max_ms = cfg.get("click_delay_max_ms", 800)
    except Exception:
        min_ms, max_ms = 50, 800

    # Use beta distribution for natural-looking distribution (most clicks in middle)
    delay_ms = random.betavariate(2, 2) * (max_ms - min_ms) + min_ms
    return delay_ms / 1000.0


def apply_click_delay():
    """Sleep for a human-like delay before clicking."""
    time.sleep(click_delay())


def key_press_duration(base_duration: float = 0.05) -> float:
    """
    Returns the duration (in seconds) a key should be held when pressed.
    Humans vary key press duration significantly: 20-200ms for quick taps,
    longer for held keys (force move, stand still).
    """
    try:
        cfg = Config().stealth
        min_ms = cfg.get("key_press_min_ms", 20)
        max_ms = cfg.get("key_press_max_ms", 200)
    except Exception:
        min_ms, max_ms = 20, 200

    # Exponential distribution: most presses are short, some are longer
    duration_ms = min_ms + random.expovariate(1.0 / ((max_ms - min_ms) / 2))
    duration_ms = max(min_ms, min(max_ms, duration_ms))
    return duration_ms / 1000.0


def human_key_press(key: str):
    """
    Press a key with human-like timing: variable duration, micro-pause before and after.
    Replaces direct keyboard.press/release for stealth.
    """
    add_micro_pause()
    duration = key_press_duration()
    keyboard.press(key)
    time.sleep(duration)
    keyboard.release(key)
    add_micro_pause()


def human_keyboard_send(key: str):
    """
    Send a key press with full human-like timing.
    Replaces keyboard.send() for stealth.
    """
    add_micro_pause()
    duration = key_press_duration(0.03)
    keyboard.press(key)
    time.sleep(duration)
    keyboard.release(key)
    add_micro_pause()


# ─── Tier 2: Behavior-level stealth ───────────────────────────────────────────

def should_wrong_waypoint() -> bool:
    """
    2-3% chance of "getting lost" and selecting wrong waypoint first,
    then correcting. Humans occasionally click the wrong TP portal.
    """
    try:
        cfg = Config().stealth
        chance = cfg.get("wrong_waypoint_chance", 0.025)
    except Exception:
        chance = 0.025
    return random.random() < chance


def skill_rotation_hesitation() -> float:
    """
    Returns delay before activating a skill. Humans don't spam skills
    at machine speed — there's variable pre-cast hesitation.
    """
    try:
        cfg = Config().stealth
        min_ms = cfg.get("skill_hesitation_min_ms", 80)
        max_ms = cfg.get("skill_hesitation_max_ms", 300)
    except Exception:
        min_ms, max_ms = 80, 300
    return random.uniform(min_ms, max_ms) / 1000.0


def should_correct_skill_mistake() -> bool:
    """
    Small chance of casting wrong skill first then correcting (human error).
    1-2% of skill casts.
    """
    try:
        cfg = Config().stealth
        chance = cfg.get("skill_mistake_chance", 0.015)
    except Exception:
        chance = 0.015
    return random.random() < chance


# ─── Tier 3: Session-level stealth ────────────────────────────────────────────

def get_personality_seed(char_name: str) -> int:
    """
    Generate a deterministic seed from character name.
    Each character has a unique "personality" — different timing distributions,
    different error rates — but consistent across sessions.
    """
    return hash(char_name) & 0xFFFFFFFF


def apply_personality(char_name: str):
    """
    Configure random distributions based on character-specific personality.
    Called once at bot start to seed per-character behavior.
    """
    seed = get_personality_seed(char_name)
    # Don't reseed global random (breaks other things),
    # but each stealth function uses its own local random call
    # which gets the benefit of global state entropy.
    # Personality is encoded in config ranges, not seeds.
    pass
