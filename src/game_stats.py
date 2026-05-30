import math
import numpy as np
import time
import threading
import inspect
import json
import os
import re
from beautifultable import BeautifulTable

from logger import Logger
from config import Config
from messages import Messenger
from fg_price_tracker import FGPriceTracker
from utils.misc import hms
from utils.levels import get_level, get_level_from_exp
from version import __version__

from ui import player_bar


class GameStats:
    _TOP_VALUABLE_ITEMS = (
        "ZOD RUNE",
        "JAH RUNE",
        "BER RUNE",
        "CHAM RUNE",
        "LO RUNE",
        "SUR RUNE",
        "TYRAEL'S MIGHT",
        "DEATH'S WEB",
        "GRIFFON'S EYE",
        "DEATH'S FATHOM",
        "RAINBOW FACET",
        "HIGH LORD'S WRATH",
        "MARA'S KALEIDOSCOPE",
        "THE STONE OF JORDAN",
        "BUL-KATHOS' WEDDING BAND",
        "WAR TRAVELER",
        "HARLEQUIN CREST",
        "ARACHNID MESH",
        "ANDARIEL'S VISAGE",
        "HERALD OF ZAKARUM",
        "THE REAPER'S TOLL",
    )

    def __init__(self):
        self._messenger = Messenger()
        self._start_time = time.time()
        self._timer = None
        self._timepaused = None
        self._paused = False
        self._game_counter = 0
        self._chicken_counter = 0
        self._death_counter = 0
        self._merc_death_counter = 0
        self._runs_failed = 0
        self._run_counter = 1
        self._consecutive_runs_failed = 0
        self._failed_game_time = 0
        self._location = None
        self._location_stats = {}
        self._location_stats["totals"] = {
            "items": 0,
            "deaths": 0,
            "chickens": 0,
            "merc_deaths": 0,
            "failed_runs": 0,
            "runes": 0,
            "fg_estimated": 0.0,
            "gold_stashed": 0,
        }
        self._gold_in_stash = 0
        self._gold_stashed_total = 0
        self._valuable_item_counts = {name: 0 for name in self._TOP_VALUABLE_ITEMS}
        self._fg_tracker = FGPriceTracker()
        self._fg_item_counts = {}
        self._fg_item_totals = {}
        self._stats_filename = f'stats_{time.strftime("%Y%m%d_%H%M%S")}.log'
        self._events_filename = f'events_{time.strftime("%Y%m%d_%H%M%S")}.jsonl'
        self._mini_stats_filename = f'mini_stats_{time.strftime("%Y%m%d_%H%M%S")}.json'
        self._nopickup_active = False
        self._starting_exp = 0
        self._current_exp = 0
        self._current_lvl = 0
        self._exp_logging_disabled = False
        self._exp_logging_error_warned = False
        self._last_status_report_game = 0
        self._last_status_report_run = 0
        self._last_failure_reason = None
        os.makedirs("log/stats", exist_ok=True)

    def set_failure_reason(self, reason: str):
        """Store the reason for the last failure (e.g. disk full, uncaught exception)."""
        self._last_failure_reason = str(reason)

    def get_failure_reason(self) -> str | None:
        return self._last_failure_reason

    def _log_event(self, event_type: str, data: dict | None = None):
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event": event_type,
            "game": self._game_counter,
            "run": self._run_counter,
            "location": self._location,
        }
        if data:
            payload.update(data)
        try:
            with open(file=f"log/stats/{self._events_filename}", mode="a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        except Exception as e:
            Logger.warning(f"Failed to write structured event log: {e}")

    def _persist_snapshot(self):
        # Keep a crash-resilient human-readable snapshot updated throughout a session.
        try:
            self._save_stats_to_file()
            self._save_mini_stats_to_file()
        except Exception as e:
            Logger.warning(f"Failed to persist stats snapshot: {e}")

    def update_location(self, loc: str):
        if self._location != loc:
            previous_location = self._location
            self._location = str(loc)
            self.populate_location_stat()
            self._log_event("location_changed", {"from": previous_location, "to": self._location})
            self._persist_snapshot()

    def populate_location_stat(self):
        if self._location not in self._location_stats:
            self._location_stats[self._location] = {
                "items": [],
                "item_counts": {},
                "rune_counts": {},
                "valuable_counts": {},
                "fg_item_counts": {},
                "fg_item_totals": {},
                "deaths": 0,
                "chickens": 0,
                "merc_deaths": 0,
                "failed_runs": 0,
                "gold_stashed": 0
            }

    @staticmethod
    def _normalize_item_name(item_name: str) -> str:
        return " ".join((item_name or "").strip().upper().split())

    @staticmethod
    def _is_rune(item_name: str) -> bool:
        normalized = GameStats._normalize_item_name(item_name)
        if normalized.endswith(" RUNE"):
            return True
        compact = re.sub(r"[^A-Z0-9]", "", normalized)
        return compact.endswith("RUNE")

    def log_item_keep(self, item_name: str, send_message: bool, img: np.ndarray, ocr_text: str = '', expression: str = '', item_props: dict = {}):
        filtered_substrings = [" POTION", " OF IDENTIFY", " OF TOWN PORTAL", " AMETHYST", " RUBY", " TOPAZ", " EMERALD", " SAPPHIRE", " DIAMOND"]
        filtered_matches = ["DIAMOND", "AMETHYST", "RUBY", "TOPAZ", "EMERALD", "SAPPHIRE", "ARROWS", "BOLTS",
                            "CHIPPED SKULL", "FLAWED SKULL", "SKULL", "FLAWLESS SKULL", "PERFECT SKULL"]
        skip_log = any(substring in item_name for substring in filtered_substrings) or any(match == item_name.strip() for match in filtered_matches)
        normalized_name = self._normalize_item_name(item_name)
        fg_value = None
        fg_name = None
        if self._location is not None and not skip_log:
            Logger.debug(f"Stashed and logged: {item_name}")
            self._location_stats[self._location]["items"].append(item_name)
            item_counts = self._location_stats[self._location]["item_counts"]
            item_counts[item_name] = item_counts.get(item_name, 0) + 1
            self._location_stats["totals"]["items"] += 1
            if self._is_rune(item_name):
                rune_counts = self._location_stats[self._location]["rune_counts"]
                rune_counts[normalized_name] = rune_counts.get(normalized_name, 0) + 1
                self._location_stats["totals"]["runes"] += 1
                self._log_event("rune_kept", {"item_name": normalized_name})
            if normalized_name in self._valuable_item_counts:
                valuable_counts = self._location_stats[self._location]["valuable_counts"]
                valuable_counts[normalized_name] = valuable_counts.get(normalized_name, 0) + 1
                self._valuable_item_counts[normalized_name] += 1
                self._log_event("valuable_item_kept", {"item_name": normalized_name})
            fg_value, fg_name = self._fg_tracker.estimate(normalized_name)
            if fg_value is not None and fg_name:
                fg_counts = self._location_stats[self._location]["fg_item_counts"]
                fg_totals = self._location_stats[self._location]["fg_item_totals"]
                fg_counts[fg_name] = fg_counts.get(fg_name, 0) + 1
                fg_totals[fg_name] = fg_totals.get(fg_name, 0.0) + fg_value
                self._fg_item_counts[fg_name] = self._fg_item_counts.get(fg_name, 0) + 1
                self._fg_item_totals[fg_name] = self._fg_item_totals.get(fg_name, 0.0) + fg_value
                self._location_stats["totals"]["fg_estimated"] += fg_value
                self._log_event("fg_item_kept", {"item_name": normalized_name, "fg_name": fg_name, "fg_value": fg_value})
            self._log_event("item_kept", {"item_name": item_name, "expression": expression})
            self._persist_snapshot()
        elif self._location is not None and skip_log:
            self._log_event("item_kept_filtered", {"item_name": item_name, "reason": "filtered"})

        if send_message and self._messenger.enabled and not skip_log:
            if expression[0] != "@":
                expression_with_fg = expression
                if fg_value is not None and fg_name:
                    expression_with_fg = f"{expression} | est_fg={fg_value:.1f}"
                self._messenger.send_item(item_name, img, self._location, ocr_text, expression_with_fg, item_props)

    def log_death(self, img: str):
        self._death_counter += 1
        if self._location is not None:
            self._location_stats[self._location]["deaths"] += 1
            self._location_stats["totals"]["deaths"] += 1
            self._log_event("death")
            self._persist_snapshot()

        if self._messenger.enabled:
            self._messenger.send_death(self._location, img)

    def log_chicken(self, img: str):
        self._chicken_counter += 1
        if self._location is not None:
            self._location_stats[self._location]["chickens"] += 1
            self._location_stats["totals"]["chickens"] += 1
            self._log_event("chicken")
            self._persist_snapshot()

        if Config().general["discord_log_chicken"] and self._messenger.enabled:
            self._messenger.send_chicken(self._location, img)

    def log_merc_death(self):
        self._merc_death_counter += 1
        if self._location is not None:
            self._location_stats[self._location]["merc_deaths"] += 1
            self._location_stats["totals"]["merc_deaths"] += 1
            self._log_event("merc_death")
            self._persist_snapshot()

    def log_gold_stashed(self, gold_amount: int):
        if self._location is not None:
            self._location_stats[self._location]["gold_stashed"] += gold_amount
            self._location_stats["totals"]["gold_stashed"] += gold_amount
            self._gold_stashed_total += gold_amount
            self._log_event("gold_stashed", {"amount": gold_amount})
            self._persist_snapshot()

    def log_gold_in_stash(self, gold_amount: int):
        self._gold_in_stash = gold_amount

    def _format_gold(self, amount: int) -> str:
        return f"{amount:,}"

    def log_start_game(self):
        if self._game_counter > 0:
            self._save_stats_to_file()
            # Legacy game-based status updates are only used when run-based updates are disabled.
            if not Config().general.get("discord_status_runs"):
                if Config().general["discord_status_count"] and self._game_counter % Config().general["discord_status_count"] == 0:
                    # every discord_status_count game send a message update about current status
                    self._send_status_update()
        self._game_counter += 1
        self._timer = time.time()
        Logger.info(f"Starting game #{self._game_counter}")
        self._log_event("game_started")
        self._persist_snapshot()

    def log_end_game(self, failed: bool = False):
        elapsed_time = 0
        if self._timer is not None:
            elapsed_time = time.time() - self._timer
        self._timer = None
        if failed:
            self._runs_failed += 1
            self._consecutive_runs_failed += 1
            if self._location is not None:
                self._location_stats[self._location]["failed_runs"] += 1
                self._location_stats["totals"]["failed_runs"] += 1
            self._failed_game_time += elapsed_time
            Logger.warning(f"End failed game: Elapsed time: {elapsed_time:.2f}s Fails: {self._consecutive_runs_failed}")
            self._log_event("game_ended", {"failed": True, "elapsed_seconds": round(elapsed_time, 2)})
        else:
            self._consecutive_runs_failed = 0
            Logger.info(f"End game. Elapsed time: {elapsed_time:.2f}s")
            self._log_event("game_ended", {"failed": False, "elapsed_seconds": round(elapsed_time, 2)})
        self._persist_snapshot()

    def log_exp(self):
        if self._exp_logging_disabled:
            return

        try:
            exp = player_bar.get_experience()
        except RuntimeError as e:
            self._exp_logging_disabled = True
            Logger.warning(f"XP tracking disabled for this session: {e}")
            self._log_event("exp_tracking_disabled", {"reason": str(e)})
            self._persist_snapshot()
            return
        except Exception as e:
            if not self._exp_logging_error_warned:
                Logger.warning(f"Failed to log exp (will continue silently): {e}")
                self._exp_logging_error_warned = True
            else:
                Logger.debug(f"Failed to log exp: {e}")
            return

        if self._starting_exp == 0:
            self._starting_exp = exp[0]

        if exp[0] > 0:
            self._current_exp = exp[0]
            curr_lvl = get_level_from_exp(self._current_exp)["lvl"]
            if curr_lvl > 0:
                self._current_lvl = curr_lvl

    def pause_timer(self):
        if self._timer is None or self._paused:
            return
        self._timepaused = time.time()
        self._paused = True

    def resume_timer(self):
        if self._timer is None or not self._paused:
            return
        pausetime = time.time() - self._timepaused
        self._timer = self._timer + pausetime
        self._paused = False

    def get_current_game_length(self):
        if self._timer is None:
            return 0
        if self._paused:
            return self._timepaused - self._timer
        else:
            return time.time() - self._timer

    def get_consecutive_runs_failed(self):
        return self._consecutive_runs_failed

    def log_run_started(self, run_name: str):
        self._log_event("run_started", {"run_name": run_name})

    def log_run_finished(self, run_name: str, failed: bool, picked_up_items: bool | None = None):
        payload = {"run_name": run_name, "failed": failed}
        if picked_up_items is not None:
            payload["picked_up_items"] = picked_up_items
        self._log_event("run_finished", payload)
        self._persist_snapshot()

    def log_run_completed(self):
        status_runs = Config().general.get("discord_status_runs")
        if status_runs and (self._run_counter - 1) > 0 and (self._run_counter - 1) % status_runs == 0:
            self._send_status_update()

    def _create_msg(self):
        elapsed_time = time.time() - self._start_time
        elapsed_time_str = hms(elapsed_time)
        avg_length_str = "n/a"
        good_games_count = self._game_counter - self._runs_failed
        good_games_time = elapsed_time - self._failed_game_time

        if good_games_count == 0:
            good_games_count = 1

        avg_length = good_games_time / float(good_games_count)
        avg_length_str = hms(avg_length)

        curr_lvl = get_level(self._current_lvl) if self._current_lvl > 0 else { "lvl": 0, "exp": 0, "xp_to_next": 0 }

        msg = f'\nSession length: {elapsed_time_str}'
        msg += f'\nGames: {self._game_counter}'
        msg += f'\nAvg Game Length: {avg_length_str}'
        msg += f'\nCurrent Level: {curr_lvl["lvl"] if curr_lvl["lvl"] > 0 else "n/a"}'
        msg += f'\nRunes Kept: {self._location_stats["totals"]["runes"]}'
        msg += f'\nEstimated FG: {self._location_stats["totals"]["fg_estimated"]:.1f}'
        msg += f'\nGold Stashed (Session): {self._format_gold(self._location_stats["totals"]["gold_stashed"])}'
        msg += f'\nGold In Stash: {self._format_gold(self._gold_in_stash)}'

        if curr_lvl["lvl"] > 0 and curr_lvl["lvl"] < 99 and self._current_exp > 0:
            try:
                exp_gained = self._current_exp - curr_lvl['exp']
                gained_exp = self._current_exp - self._starting_exp
                xp_to_next = curr_lvl["xp_to_next"]
                if xp_to_next <= 0 or good_games_time <= 0 or good_games_count <= 0:
                    raise ValueError("invalid XP/session denominator")
                per_to_lvl = exp_gained / xp_to_next
                exp_per_second = gained_exp / good_games_time if gained_exp > 0 else 0
                exp_per_hour = round(exp_per_second * 3600, 1)
                exp_per_game = round(gained_exp / float(good_games_count), 1)
                exp_needed = max(0, xp_to_next - exp_gained)
                msg += f'\nPercent to Level: {math.ceil(per_to_lvl*100)}%'
                msg += f'\nXP Gained: {gained_exp:,}'
                msg += f'\nXP Per Hour: {exp_per_hour:,}'
                msg += f'\nXP Per Game: {exp_per_game:,}'
                if exp_per_second > 0:
                    msg += f'\nTime Needed To Level: {hms(exp_needed / exp_per_second)}'
                else:
                    msg += f'\nTime Needed To Level: n/a'
                if exp_per_game > 0:
                    msg += f'\nGames Needed To Level: {math.ceil(exp_needed / exp_per_game):,}'
                else:
                    msg += f'\nGames Needed To Level: n/a'
            except Exception as e:
                Logger.debug(f"Skipping XP projection in status report: {e}")

        table = BeautifulTable()
        table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)
        for location in self._location_stats:
            if location == "totals":
                continue
            stats = self._location_stats[location]
            table.rows.append([location, len(stats["items"]), stats["chickens"], stats["deaths"], stats["merc_deaths"], stats["failed_runs"]])

        table.rows.append([
            "T",
            self._location_stats["totals"]["items"],
            self._location_stats["totals"]["chickens"],
            self._location_stats["totals"]["deaths"],
            self._location_stats["totals"]["merc_deaths"],
            self._location_stats["totals"]["failed_runs"]
        ])

        table.columns.header = ["Run", "I", "C", "D", "MD", "FR"]

        msg += f"\n{str(table)}\n"
        return msg

    def _send_status_update(self):
        # Prevent duplicate status updates for the same game/run counters.
        if self._last_status_report_game == self._game_counter and self._last_status_report_run == self._run_counter:
            Logger.debug("Skip duplicate Discord status update for same game/run counters")
            return
        msg = f"Status Report\n{self._create_msg()}\nVersion: {__version__}"
        if self._messenger.enabled:
            self._messenger.send_message(msg)
            self._last_status_report_game = self._game_counter
            self._last_status_report_run = self._run_counter

    def _save_stats_to_file(self):
        msg = self._create_msg()
        msg += "\nItems:"
        for location in self._location_stats:
            if location == "totals":
                continue
            stats = self._location_stats[location]
            msg += f"\n  {location}:"
            for item_name in stats["items"]:
                msg += f"\n    {item_name}"
            if len(stats["item_counts"]) > 0:
                msg += "\n    Item counts:"
                sorted_counts = sorted(stats["item_counts"].items(), key=lambda x: x[1], reverse=True)
                for item_name, count in sorted_counts:
                    msg += f"\n      {item_name}: {count}"
            if len(stats["rune_counts"]) > 0:
                msg += "\n    Rune counts:"
                sorted_runes = sorted(stats["rune_counts"].items(), key=lambda x: x[1], reverse=True)
                for rune_name, count in sorted_runes:
                    msg += f"\n      {rune_name}: {count}"
            if len(stats["valuable_counts"]) > 0:
                msg += "\n    Top-10 valuable item counts:"
                sorted_valuables = sorted(stats["valuable_counts"].items(), key=lambda x: x[1], reverse=True)
                for valuable_name, count in sorted_valuables:
                    msg += f"\n      {valuable_name}: {count}"
            if len(stats["fg_item_totals"]) > 0:
                msg += "\n    FG tracked items:"
                sorted_fg = sorted(stats["fg_item_totals"].items(), key=lambda x: x[1], reverse=True)
                for fg_name, fg_total in sorted_fg:
                    count = stats["fg_item_counts"].get(fg_name, 0)
                    msg += f"\n      {fg_name}: {count}x, {fg_total:.1f} fg"
            if stats.get("gold_stashed", 0) > 0:
                msg += f"\n    Gold stashed: {self._format_gold(stats['gold_stashed'])}"

        msg += "\n\nTop-10 valuable items (session totals):"
        for item_name in self._TOP_VALUABLE_ITEMS:
            msg += f"\n  {item_name}: {self._valuable_item_counts[item_name]}"
        if len(self._fg_item_totals) > 0:
            msg += "\n\nFG tracker (session totals):"
            sorted_fg_totals = sorted(self._fg_item_totals.items(), key=lambda x: x[1], reverse=True)
            for fg_name, fg_total in sorted_fg_totals:
                count = self._fg_item_counts.get(fg_name, 0)
                msg += f"\n  {fg_name}: {count}x, {fg_total:.1f} fg"
        msg += f"\n\nGold (session totals):"
        msg += f"\n  Total stashed: {self._format_gold(self._gold_stashed_total)}"
        msg += f"\n  In stash now: {self._format_gold(self._gold_in_stash)}"

        with open(file=f"log/stats/{self._stats_filename}", mode="w+", encoding="utf-8") as f:
            f.write(msg)

    def _save_mini_stats_to_file(self):
        top_items = sorted(
            self._fg_item_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "session_seconds": round(time.time() - self._start_time, 2),
            "games": self._game_counter,
            "run_counter": self._run_counter,
            "runs_failed_total": self._runs_failed,
            "runs_failed_consecutive": self._consecutive_runs_failed,
            "current_level": self._current_lvl if self._current_lvl > 0 else None,
            "current_exp": self._current_exp if self._current_exp > 0 else None,
            "runes_kept": self._location_stats["totals"]["runes"],
            "estimated_fg_total": round(self._location_stats["totals"]["fg_estimated"], 1),
            "gold_stashed_total": self._gold_stashed_total,
            "gold_in_stash": self._gold_in_stash,
            "current_location": self._location,
            "top_fg_items": [
                {
                    "item": item_name,
                    "count": self._fg_item_counts.get(item_name, 0),
                    "fg_total": round(fg_total, 1),
                }
                for item_name, fg_total in top_items
            ],
        }
        with open(file=f"log/stats/{self._mini_stats_filename}", mode="w+", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _save_session_report(self):
        """Save a session report to log/runs/ with date-based rotation."""
        os.makedirs("log/runs", exist_ok=True)
        elapsed_time = time.time() - self._start_time
        elapsed_time_str = hms(elapsed_time)
        good_games_count = self._game_counter - self._runs_failed
        good_games_time = elapsed_time - self._failed_game_time
        if good_games_count == 0:
            good_games_count = 1
        avg_length = good_games_time / float(good_games_count)
        avg_length_str = hms(avg_length)

        curr_lvl = get_level(self._current_lvl) if self._current_lvl > 0 else {"lvl": 0, "exp": 0, "xp_to_next": 0}

        lines = []
        lines.append("=" * 50)
        lines.append("BOTTY SESSION REPORT")
        lines.append("=" * 50)
        lines.append(f"Date:       {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Version:    {__version__}")
        lines.append(f"Session:    {elapsed_time_str}")
        lines.append(f"Games:      {self._game_counter}")
        lines.append(f"Failed:     {self._runs_failed}")
        lines.append(f"Avg Game:   {avg_length_str}")
        lines.append(f"Level:      {curr_lvl['lvl'] if curr_lvl['lvl'] > 0 else 'n/a'}")
        lines.append(f"Runes:      {self._location_stats['totals']['runes']}")
        lines.append(f"Est FG:     {self._location_stats['totals']['fg_estimated']:.1f}")
        lines.append(f"Gold Stashed (Session): {self._format_gold(self._location_stats['totals']['gold_stashed'])}")
        lines.append(f"Gold In Stash:          {self._format_gold(self._gold_in_stash)}")
        lines.append(f"Deaths:     {self._death_counter}")
        lines.append(f"Chickens:   {self._chicken_counter}")
        lines.append(f"Merc Deaths:{self._merc_death_counter}")
        if self._last_failure_reason:
            lines.append(f"Last Failure: {self._last_failure_reason}")

        if curr_lvl["lvl"] > 0 and curr_lvl["lvl"] < 99 and self._current_exp > 0:
            gained_exp = self._current_exp - self._starting_exp
            if good_games_time > 0:
                exp_per_hour = round((gained_exp / good_games_time) * 3600, 1)
                lines.append(f"XP Gained:  {gained_exp:,}")
                lines.append(f"XP/Hour:    {exp_per_hour:,}")

        lines.append("")
        lines.append("Per-Run Stats:")
        lines.append(f"{'Run':<20} {'Items':>6} {'Chick':>5} {'Death':>5} {'MercD':>5} {'Fail':>4} {'Gold':>14}")
        lines.append("-" * 60)
        for location in self._location_stats:
            if location == "totals":
                continue
            stats = self._location_stats[location]
            lines.append(f"{location:<20} {len(stats['items']):>6} {stats['chickens']:>5} {stats['deaths']:>5} {stats['merc_deaths']:>5} {stats['failed_runs']:>4} {self._format_gold(stats.get('gold_stashed', 0)):>14}")
        totals = self._location_stats["totals"]
        total_items = sum(len(self._location_stats[loc]["items"]) for loc in self._location_stats if loc != "totals")
        lines.append("-" * 60)
        lines.append(f"{'TOTAL':<20} {total_items:>6} {totals['chickens']:>5} {totals['deaths']:>5} {totals['merc_deaths']:>5} {totals['failed_runs']:>4} {self._format_gold(totals['gold_stashed']):>14}")

        if len(self._fg_item_totals) > 0:
            lines.append("")
            lines.append("FG Tracker (Session Totals):")
            sorted_fg = sorted(self._fg_item_totals.items(), key=lambda x: x[1], reverse=True)
            for fg_name, fg_total in sorted_fg:
                count = self._fg_item_counts.get(fg_name, 0)
                lines.append(f"  {fg_name}: {count}x, {fg_total:.1f} fg")

        lines.append("")
        lines.append("=" * 50)

        report_content = "\n".join(lines)

        # Save with date-based filename
        report_filename = f"run_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = f"log/runs/{report_filename}"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        Logger.info(f"Session report saved to {report_path}")

        # Also save a JSON version for easy parsing
        json_payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "version": __version__,
            "session_seconds": round(elapsed_time, 2),
            "games": self._game_counter,
            "runs_failed": self._runs_failed,
            "avg_game_length": round(avg_length, 2),
            "current_level": self._current_lvl if self._current_lvl > 0 else None,
            "runes_kept": self._location_stats["totals"]["runes"],
            "estimated_fg": round(self._location_stats["totals"]["fg_estimated"], 1),
            "gold_stashed_total": self._gold_stashed_total,
            "gold_in_stash": self._gold_in_stash,
            "deaths": self._death_counter,
            "chickens": self._chicken_counter,
            "merc_deaths": self._merc_death_counter,
            "xp_gained": self._current_exp - self._starting_exp if self._current_exp > 0 else 0,
            "last_failure_reason": self._last_failure_reason,
            "locations": {}
        }
        for location in self._location_stats:
            if location == "totals":
                continue
            stats = self._location_stats[location]
            json_payload["locations"][location] = {
                "items": len(stats["items"]),
                "chickens": stats["chickens"],
                "deaths": stats["deaths"],
                "merc_deaths": stats["merc_deaths"],
                "failed_runs": stats["failed_runs"],
                "gold_stashed": stats.get("gold_stashed", 0)
            }
        json_path = f"log/runs/{report_filename.replace('.txt', '.json')}"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2)


if __name__ == "__main__":
    game_stats = GameStats()
    game_stats.log_item_keep("rune_12", True)
    game_stats._save_stats_to_file()
