"""
Auto-label NPCs visible on screen.

Scans for all known NPCs using their template groups (in parallel via
template_finder.search) and returns a dict of {npc_name: {center, score}}.
Can be called from any game loop tick without blocking the main thread.

Usage:
    from utils.npc_auto_label import detect_visible_npcs
    npcs_on_screen = detect_visible_npcs(img)
    # npcs_on_screen = {"AKARA": {"center": (620, 300), "score": 0.82}, ...}
"""

import concurrent.futures
import template_finder
from screen import grab


# NPCs that exist per act — detected via their template groups in npc_manager
NPC_TEMPLATES = {
    # Act 1
    "AKARA":    ["AKARA_FRONT", "AKARA_BACK", "AKARA_SIDE", "AKARA_SIDE_2"],
    "CHARSI":   ["CHARSI_FRONT", "CHARSI_BACK", "CHARSI_SIDE", "CHARSI_SIDE_2", "CHARSI_SIDE_3"],
    "KASHYA":   ["KASHYA_FRONT", "KASHYA_BACK", "KASHYA_SIDE", "KASHYA_SIDE_2"],
    "CAIN":     ["CAIN_0", "CAIN_1", "CAIN_2", "CAIN_3"],
    # Act 2
    "FARA":     ["FARA_LIGHT_1", "FARA_LIGHT_3", "FARA_MEDIUM_1", "FARA_DARK_1"],
    "DROGNAN":  ["DROGNAN_FRONT", "DROGNAN_LEFT", "DROGNAN_RIGHT_SIDE"],
    "LYSANDER": ["LYSANDER_FRONT", "LYSANDER_BACK", "LYSANDER_SIDE", "LYSANDER_SIDE_2"],
    # Act 3
    "ORMUS":    ["ORMUS_0", "ORMUS_2", "ORMUS_4"],
    # Act 4
    "TYRAEL":   ["TYRAEL_1", "TYRAEL_2"],
    "JAMELLA":  ["JAMELLA_FRONT", "JAMELLA_BACK", "JAMELLA_SIDE"],
    "HALBU":    ["HALBU_FRONT", "HALBU_BACK", "HALBU_SIDE", "HALBU_SIDE_2"],
    # Act 5
    "QUAL_KEHK": ["QUAL_0", "QUAL_45", "QUAL_180", "QUAL_270"],
    "MALAH":    ["MALAH_FRONT", "MALAH_BACK", "MALAH_45", "MALAH_SIDE"],
    "LARZUK":   ["LARZUK_FRONT", "LARZUK_BACK", "LARZUK_SIDE"],
    "ANYA":     ["ANYA_FRONT", "ANYA_BACK", "ANYA_SIDE"],
}

# How many NPCs to search in parallel (limit thread pool)
MAX_WORKERS = 8

# Search ROI — skip the bottom skill bar area to reduce false positives
SEARCH_ROI = [0, 0, 1280, 480]


def _search_npc(npc_name, template_keys, img):
    """Search for one NPC using all its template variants. Returns match or None."""
    best = template_finder.search(
        template_keys,
        img,
        threshold=0.55,
        roi=SEARCH_ROI,
        best_match=True,
    )
    if best.valid:
        return {
            "center": best.center,
            "center_monitor": best.center_monitor,
            "score": best.score,
        }
    return None


def detect_visible_npcs(img=None):
    """
    Scan the screen for all known NPCs.

    :param img: Screenshot (BGR numpy array). If None, grabs one.
    :return: dict {npc_name: {"center": (x,y), "center_monitor": (x,y), "score": float}}
    """
    if img is None:
        img = grab()

    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_search_npc, name, templates, img): name
            for name, templates in NPC_TEMPLATES.items()
        }
        for future in concurrent.futures.as_completed(futures):
            npc_name = futures[future]
            try:
                match = future.result()
                if match is not None:
                    results[npc_name] = match
            except Exception:
                pass

    return results


# ─── Optional: persistent cache that expires after N seconds ───

_cache = {}
_cache_time = 0.0


def detect_visible_npcs_cached(img=None, ttl=5.0):
    """
    Like detect_visible_npcs() but caches results for ttl seconds.
    Use this when scanning every tick but only need fresh data periodically.
    """
    import time
    global _cache_time
    now = time.time()
    if now - _cache_time < ttl:
        return _cache
    _cache.clear()
    _cache.update(detect_visible_npcs(img))
    _cache_time = now
    return _cache


if __name__ == "__main__":
    import cv2
    import keyboard
    from screen import start_detecting_window

    start_detecting_window()
    print("Press F12 to exit. Scanning for NPCs...")

    while True:
        keyboard.pause(0.05, True)
        if keyboard.is_pressed("f12"):
            break

        img = grab()
        found = detect_visible_npcs(img)

        display = img.copy()
        for name, info in found.items():
            x, y = info["center"]
            cv2.putText(display, name, (x - 30, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.circle(display, (x, y), 5, (0, 255, 0), -1)

        if found:
            npc_strs = [f"{n}({info['score']:.2f})" for n, info in found.items()]
            print(f"NPCs on screen: {', '.join(npc_strs)}")
        cv2.imshow("NPC Auto-Label", display)
        cv2.waitKey(1)