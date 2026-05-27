#!/usr/bin/env python3
"""
fg_daily_report.py — Generate FG earnings report for the last 8 hours.

Usage:
    python tools/fg_daily_report.py              # last 8 hours (default)
    python tools/fg_daily_report.py --hours 24    # last 24 hours
    python tools/fg_daily_report.py --today       # today only (00:00 now)
    python tools/fg_daily_report.py --all         # all available data

Outputs a formatted text report to stdout and saves to log/fg_report_<timestamp>.txt.
"""

import argparse
import json
import glob
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# FG prices from config (matches what the bot uses)
# Used both for fg_item_kept events AND to estimate FG from item_kept events
FG_PRICES = {
    "EL RUNE": 0,
    "ELD RUNE": 0,
    "TIR RUNE": 1,
    "NEF RUNE": 1,
    "ETH RUNE": 3,
    "ITH RUNE": 3,
    "RAL RUNE": 6,
    "ORT RUNE": 8,
    "THUL RUNE": 2,
    "AMN RUNE": 10,
    "SHAEL RUNE": 10,
    "BER RUNE": 15,
    "JAH RUNE": 20,
    "KOH RUNE": 25,
    "VEX RUNE": 30,
    "PUL RUNE": 40,
    "UM RUNE": 50,
    "MAL RUNE": 60,
    "LO RUNE": 80,
    "SUR RUNE": 100,
    "ZOD RUNE": 200,
    # Unique/set items
    "SANDER'S RIPRAP": 5,
    "MAGEFIST": 5,
    "FROSTBURN": 3,
    "WANDERER'S SHOES": 3,
    "ARACHNID'S MESH": 50,
    "DEATH'S WEB": 80,
    "GRIFFON'S EYE": 80,
    "DEATH'S FATHOM": 100,
    "HERALD OF ZAKARUM": 100,
    "THE REAPER'S TOLL": 120,
    "HIGH LORD'S WRATH": 150,
    "MARA'S KALEIDOSCOPE": 200,
    "THE STONE OF JORDAN": 200,
    "BUL-KATHOS' WEDDING BAND": 200,
    "WAR TRAVELER": 150,
    "HARLEQUIN CREST": 200,
    "ANDARIEL'S VISAGE": 80,
    "TYRAEL'S MIGHT": 150,
    "RAINBOW FACET": 100,
    "TAL RASHA'S HORADRIC CREST": 10,
    "TAL RASHA's TOQUE": 8,
    "TAL RASHA's HEADDRESS": 10,
    "TAL RASHA's WRATH": 12,
    "TAL RASHA's ADVOCACY": 10,
    "TAL RASHA's GUARDIAN": 8,
    "TAL RASHA's SIGNET": 8,
}


def estimate_fg_for_item(item_name):
    """Estimate FG value for an item name from item_kept events (pre-FG-tracking)."""
    name_upper = item_name.upper()
    # Direct match
    if name_upper in FG_PRICES:
        return FG_PRICES[name_upper]
    # Try matching rune names (e.g. "ETH RUNE" -> "ETH RUNE")
    for fg_name, price in FG_PRICES.items():
        if fg_name.upper() == name_upper:
            return price
    return None


def find_stats_dir():
    """Find the stats directory relative to repo root."""
    # Try relative to script location (tools/../log/stats)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    stats_dir = os.path.join(repo_root, "log", "stats")
    if os.path.isdir(stats_dir):
        return stats_dir
    # Fallback: current directory
    stats_dir = os.path.join(".", "log", "stats")
    if os.path.isdir(stats_dir):
        return stats_dir
    return None


def parse_event_files(stats_dir, start_time, end_time):
    """Parse all event files and filter by time window."""
    files = sorted(glob.glob(os.path.join(stats_dir, "events_*.jsonl")))

    total_fg = 0.0
    runs_finished = 0
    runs_failed = 0
    deaths = 0
    max_game = 0
    item_counts = defaultdict(lambda: {"count": 0, "fg": 0.0})
    all_items_kept = []  # non-FG items
    first_ts = None
    last_ts = None
    locations = defaultdict(int)

    for fpath in files:
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts_str = ev.get("ts", "")
                if not ts_str:
                    continue

                # Parse timestamp
                try:
                    ts = datetime.fromisoformat(ts_str)
                except ValueError:
                    continue

                # Filter by time window
                if ts < start_time or ts > end_time:
                    continue

                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts

                event = ev.get("event", "")

                if event == "fg_item_kept":
                    fg_val = ev.get("fg_value", 0)
                    fg_name = ev.get("fg_name", "Unknown")
                    total_fg += fg_val
                    # Normalize key to uppercase for dedup with item_kept
                    key = fg_name.upper()
                    item_counts[key]["count"] += 1
                    item_counts[key]["fg"] += fg_val

                elif event == "item_kept":
                    # Non-FG tracked item kept (pre-fg_item_kept events)
                    item_name = ev.get("item_name", "Unknown")
                    all_items_kept.append(item_name)
                    # Estimate FG for items we know the price of
                    est_fg = estimate_fg_for_item(item_name)
                    if est_fg is not None and est_fg > 0:
                        total_fg += est_fg
                        key = item_name.upper()
                        item_counts[key]["count"] += 1
                        item_counts[key]["fg"] += est_fg

                elif event == "item_kept_filtered":
                    # Item was kept but filtered out (gems, skulls, etc.)
                    pass

                elif event == "run_finished":
                    runs_finished += 1
                    loc = ev.get("location", "Unknown")
                    locations[loc] += 1
                    if ev.get("failed"):
                        runs_failed += 1

                elif event == "run_started":
                    loc = ev.get("location", "Unknown")
                    # Track location from run_started too
                    pass

                elif event == "game_started":
                    g = ev.get("game", 0)
                    if g > max_game:
                        max_game = g

                elif event == "death":
                    deaths += 1

    return {
        "total_fg": total_fg,
        "runs_finished": runs_finished,
        "runs_failed": runs_failed,
        "deaths": deaths,
        "max_game": max_game,
        "item_counts": dict(item_counts),
        "all_items_kept": all_items_kept,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "locations": dict(locations),
    }


def format_report(data, period_label):
    """Format the data as a human-readable report."""
    lines = []
    lines.append(f"{'='*55}")
    lines.append(f"  FG EARNINGS REPORT: {period_label}")
    lines.append(f"{'='*55}")

    if not data["first_ts"]:
        lines.append("  No data found for this period.")
        return "\n".join(lines)

    # Time span
    t1 = data["first_ts"]
    t2 = data["last_ts"]
    duration_h = (t2 - t1).total_seconds() / 3600 if t2 else 0
    duration_str = f"{duration_h:.1f}h" if duration_h > 0 else "N/A"

    lines.append(f"  Period: {t1.strftime('%Y-%m-%d %H:%M')} - {t2.strftime('%Y-%m-%d %H:%M')} ({duration_str})")
    lines.append(f"  Games: {data['max_game']}  |  Runs: {data['runs_finished']}  |  Failed: {data['runs_failed']}  |  Deaths: {data['deaths']}")
    lines.append(f"  FG Earned: {data['total_fg']:.0f} FG")
    if duration_h > 0:
        lines.append(f"  FG/Hour: {data['total_fg'] / duration_h:.1f}")
    lines.append("")

    # FG items
    item_counts = data["item_counts"]
    if item_counts:
        lines.append("  FG Items:")
        for name in sorted(item_counts.keys(), key=lambda x: item_counts[x]["fg"], reverse=True):
            c = item_counts[name]
            lines.append(f"    {name}: {c['count']}x = {c['fg']:.0f} FG")
        lines.append("")

    # Non-FG items (top kept)
    all_items = data["all_items_kept"]
    if all_items:
        from collections import Counter
        item_freq = Counter(all_items)
        lines.append("  Other Items Kept:")
        for name, count in item_freq.most_common(10):
            lines.append(f"    {name}: {count}x")
        lines.append("")

    # Location breakdown
    locations = data["locations"]
    if locations:
        lines.append("  Runs by Location:")
        for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"    {loc}: {count}")
        lines.append("")

    lines.append(f"{'='*55}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FG earnings report")
    parser.add_argument("--hours", type=float, default=8, help="Look back N hours (default: 8)")
    parser.add_argument("--today", action="store_true", help="Report for today only")
    parser.add_argument("--all", action="store_true", help="Report for all available data")
    parser.add_argument("--output", type=str, default=None, help="Save report to file")
    args = parser.parse_args()

    stats_dir = find_stats_dir()
    if not stats_dir:
        print("ERROR: Could not find log/stats directory")
        sys.exit(1)

    now = datetime.now()

    if args.all:
        start_time = datetime(2020, 1, 1)
        end_time = now
        period_label = "ALL DATA"
    elif args.today:
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
        period_label = f"TODAY ({now.strftime('%Y-%m-%d')})"
    else:
        start_time = now - timedelta(hours=args.hours)
        end_time = now
        period_label = f"LAST {args.hours:.0f} HOURS"

    data = parse_event_files(stats_dir, start_time, end_time)
    report = format_report(data, period_label)

    # Save report
    if args.output:
        output_path = args.output
    else:
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        repo_root = os.path.dirname(stats_dir)  # log/stats -> log
        report_dir = os.path.join(repo_root, "fg_reports")
        os.makedirs(report_dir, exist_ok=True)
        output_path = os.path.join(report_dir, f"fg_report_{timestamp}.txt")

    with open(output_path, "w") as f:
        f.write(report + "\n")

    print(report)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
