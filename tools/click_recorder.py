#!/usr/bin/env python
"""
Click recorder and playback tool for D2R.

Records mouse click events with timestamps, then replays them with
human-like timing.

Usage:
    python tools/click_recorder.py record    (stop with ESC or Ctrl+C)
    python tools/click_recorder.py playback  (stop with Ctrl+C)
    python tools/click_recorder.py playback -r 5 -s 1.5  (repeat 5x at 1.5x speed)

Default save/load: recordings/clicks.json

REQUIRES: run from within the 'botty' conda environment.
"""

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

import keyboard
import mouse as _mouse

RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"


# ─── Record ───────────────────────────────────────────────────────────────────

def record(output_path: str):
    """Record clicks until ESC is pressed."""
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path)

    print("=" * 50)
    print("  CLICK RECORDER")
    print("=" * 50)
    print("Press F11 to START recording...")
    print("Press F12 to exit.")
    print()

    # Wait for F11 to begin
    keyboard.wait("f11", suppress=True)

    events: list[dict] = []
    t_start = time.perf_counter()
    done = False

    print("RECORDING - click around in D2R...")
    print("  Press F11 to STOP  |  F12 to EXIT")
    print("-" * 50)

    def on_click(event):
        if event.event_type != "down":
            return
        elapsed = round(time.perf_counter() - t_start, 3)
        x, y = _mouse.get_position()
        btn = event.button
        events.append({"t": elapsed, "x": x, "y": y, "btn": btn, "evt": "down"})
        print(f"  [{len(events):3d}] {btn:8s} ({x:5d}, {y:5d})  t={elapsed:.3f}s")

    def stop():
        nonlocal done
        done = True

    keyboard.on_click(on_click)
    keyboard.add_hotkey("f11", stop, suppress=True)
    keyboard.add_hotkey("f12", lambda: sys.exit(0), suppress=True)

    while not done:
        time.sleep(0.02)

    print("-" * 50)
    print(f"Recorded {len(events)} click(s) over {time.perf_counter() - t_start:.2f}s")
    print(f"Saving to {path}...")

    with open(path, "w") as f:
        json.dump(events, f, indent=2)

    print("Done.\n")


# ─── Playback ─────────────────────────────────────────────────────────────────

def playback(input_path: str, repeats: int = 1, speed: float = 1.0, delay: float = 1.0):
    """Replay recorded clicks."""
    path = Path(input_path)
    if not path.exists():
        print(f"File not found: {path}")
        return

    with open(path) as f:
        events = json.load(f)

    if not events:
        print("No events to play.")
        return

    duration = events[-1]["t"]
    print("=" * 50)
    print("  CLICK PLAYBACK")
    print("=" * 50)
    print(f"Events:   {len(events)}")
    print(f"Duration: {duration:.2f}s (at {speed}x speed = {duration / speed:.2f}s)")
    print(f"Repeats:  {repeats}")
    print(f"Pause:    {delay}s between repeats")
    print("-" * 50)
    print("Press Ctrl+C to abort.\n")

    # Let Ctrl+C interrupt the sleep loops
    abort = False

    def handle_int(sig, frame):
        nonlocal abort
        abort = True
    signal.signal(signal.SIGINT, handle_int)

    for rep in range(1, repeats + 1):
        if repeats > 1:
            print(f"--- Repeat {rep}/{repeats} ---")

        t0 = time.perf_counter()

        for ev in events:
            if abort:
                print("\nAborted.")
                return

            # Target time (adjusted for speed multiplier)
            target = ev["t"] / speed
            elapsed = time.perf_counter() - t0
            wait = target - elapsed

            if wait > 0:
                while wait > 0.01 and not abort:
                    time.sleep(min(0.02, wait))
                    wait = target - (time.perf_counter() - t0)

            # Move and click
            _mouse.move(ev["x"], ev["y"], duration=0.05)
            _mouse.press(ev["btn"])
            _mouse.release(ev["btn"])

        if rep < repeats and not abort:
            print(f"  ... {delay}s pause ...")
            pause_left = delay
            while pause_left > 0 and not abort:
                time.sleep(min(0.1, pause_left))
                pause_left -= 0.1

    print("\nPlayback complete.\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Click recorder / playback for D2R",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="Record clicks (F11=start/stop, F12=exit)")
    rec.add_argument("-o", "--output", default="recordings/clicks.json",
                     help="Output file (default: recordings/clicks.json)")

    play = sub.add_parser("playback", help="Replay recorded clicks")
    play.add_argument("-i", "--input", default="recordings/clicks.json",
                      help="Input file (default: recordings/clicks.json)")
    play.add_argument("-r", "--repeats", type=int, default=1,
                      help="Repeat count (default: 1)")
    play.add_argument("-s", "--speed", type=float, default=1.0,
                      help="Speed multiplier (default: 1.0)")
    play.add_argument("-d", "--delay", type=float, default=1.0,
                      help="Pause between repeats (default: 1.0s)")

    args = parser.parse_args()

    if args.cmd == "record":
        record(args.output)
    else:
        playback(args.input, args.repeats, args.speed, args.delay)


if __name__ == "__main__":
    main()
