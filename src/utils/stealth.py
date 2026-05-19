import random
import time
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
