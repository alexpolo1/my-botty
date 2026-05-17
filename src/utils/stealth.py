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
