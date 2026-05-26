import json
import os

from logger import Logger


class FGPriceTracker:
    def __init__(self, cfg_path: str = "config/fg_prices.json"):
        self._cfg_path = cfg_path
        self._rules: list[dict] = []
        self._enabled = False
        self._load()

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join((text or "").strip().upper().split())

    @staticmethod
    def _compact(text: str) -> str:
        return "".join(ch for ch in (text or "").upper() if ch.isalnum())

    def _load(self):
        cfg_candidates = [self._cfg_path, os.path.join("..", self._cfg_path)]
        cfg_path = next((p for p in cfg_candidates if os.path.exists(p)), None)
        if not cfg_path:
            Logger.info(f"FG tracker config not found at {self._cfg_path}, tracker disabled")
            return
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._enabled = bool(data.get("enabled", True))
            raw_rules = data.get("rules", [])
            parsed = []
            for rule in raw_rules:
                parsed.append({
                    "name": rule.get("name", ""),
                    "match": str(rule.get("match", "exact")).lower(),
                    "fg": float(rule.get("fg", 0)),
                    "pattern": self._normalize(rule.get("pattern", "")),
                })
            self._rules = [r for r in parsed if r["pattern"] and r["fg"] > 0]
            Logger.info(f"FG tracker loaded {len(self._rules)} pricing rules")
        except Exception as e:
            Logger.warning(f"Failed to load FG tracker config '{self._cfg_path}': {e}")
            self._enabled = False
            self._rules = []

    def estimate(self, item_name: str) -> tuple[float, str] | tuple[None, None]:
        if not self._enabled or not self._rules:
            return None, None
        normalized = self._normalize(item_name)
        compact = self._compact(item_name)
        for rule in self._rules:
            if rule["match"] == "contains":
                if rule["pattern"] in normalized:
                    return rule["fg"], rule["name"] or rule["pattern"]
            else:
                # Be tolerant to OCR/style variants like "ELRUNE" vs "EL RUNE".
                if normalized == rule["pattern"] or compact == self._compact(rule["pattern"]):
                    return rule["fg"], rule["name"] or rule["pattern"]
        return None, None
