"""
Run-selector GUI — opened via hotkey from the botty console.
Updates Config().routes and Config().routes_order in-memory; no file changes.
Takes effect on the next game (Bot is re-created each game in run_bot()).
"""
import tkinter as tk
from tkinter import messagebox

# All supported runs in display order, with friendly labels
ALL_RUNS = [
    ("run_pindle",         "Pindleskin (A5)"),
    ("run_eldritch_shenk", "Eldritch + Shenk (A5)"),
    ("run_nihlathak",      "Nihlathak (A5)"),
    ("run_trav",           "Travincal (A3)"),
    ("run_mephisto",       "Mephisto (A3)"),
    ("run_arcane",         "Arcane Sanctuary (A2)"),
    ("run_vizier",         "Vizier (A4 CS)"),
    ("run_diablo",         "Diablo (A4 CS)"),
    ("run_andariel",       "Andariel (A1)"),
    ("run_countess",       "Countess (A1)"),
    ("run_baal",           "Baal (A5)"),
]

# Internal key aliases: eldritch_shenk maps to shenk in routes_order
_ROUTE_ALIASES = {
    "run_eldritch_shenk": "run_shenk",
    "run_eldritch":       "run_shenk",
}


def _currently_enabled(config) -> set:
    """Return the set of display-keys (from ALL_RUNS) that are currently active."""
    enabled = set()
    for key, _ in ALL_RUNS:
        internal = _ROUTE_ALIASES.get(key, key)
        if config.routes.get(key) or config.routes.get(internal):
            enabled.add(key)
        if internal in config.routes_order or key in config.routes_order:
            enabled.add(key)
    return enabled


def open_run_selector(config) -> None:
    """
    Open the run-selector window (non-blocking from the hotkey perspective —
    tkinter mainloop blocks the calling thread, which is fine since the hotkey
    callback runs in its own thread via the keyboard library).

    Mutates config.routes and config.routes_order on confirmation and prints
    the new selection to the console.
    """
    currently_on = _currently_enabled(config)

    root = tk.Tk()
    root.title("Botty — Select Runs")
    root.resizable(False, False)
    # Keep the window on top so it's visible over D2R
    root.attributes("-topmost", True)

    # ── header ──────────────────────────────────────────────────────────────
    header = tk.Frame(root, bg="#1a1a2e", pady=8)
    header.pack(fill=tk.X)
    tk.Label(
        header, text="Select boss / farm runs",
        bg="#1a1a2e", fg="#e2b96e",
        font=("Segoe UI", 13, "bold"),
    ).pack()
    tk.Label(
        header, text="(takes effect on next game)",
        bg="#1a1a2e", fg="#888",
        font=("Segoe UI", 8),
    ).pack()

    # ── checkboxes ──────────────────────────────────────────────────────────
    body = tk.Frame(root, bg="#16213e", padx=20, pady=12)
    body.pack(fill=tk.BOTH)

    vars_: list[tuple[str, tk.BooleanVar]] = []
    for key, label in ALL_RUNS:
        var = tk.BooleanVar(value=(key in currently_on))
        cb = tk.Checkbutton(
            body, text=label, variable=var,
            bg="#16213e", fg="#d4d4d4", selectcolor="#0f3460",
            activebackground="#16213e", activeforeground="#e2b96e",
            font=("Segoe UI", 10),
            anchor="w",
        )
        cb.pack(fill=tk.X, pady=1)
        vars_.append((key, var))

    # ── buttons ─────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(root, bg="#1a1a2e", pady=8)
    btn_frame.pack(fill=tk.X)

    def on_apply():
        selected_keys = [k for k, v in vars_ if v.get()]
        if not selected_keys:
            messagebox.showwarning("No runs selected", "Please select at least one run.", parent=root)
            return

        # Build new routes dict and order list
        new_routes = {}
        new_order = []
        for key in selected_keys:
            new_routes[key] = True
            internal = _ROUTE_ALIASES.get(key, key)
            new_routes[internal] = True
            if internal not in new_order:
                new_order.append(internal)

        config.routes = new_routes
        config.routes_order = new_order

        friendly = [label for k, label in ALL_RUNS if k in selected_keys]
        print(f"\n[Run Selector] Runs updated: {', '.join(friendly)}")
        print("(takes effect on next game)\n")

        root.destroy()

    def on_cancel():
        root.destroy()

    tk.Button(
        btn_frame, text="Apply", command=on_apply,
        bg="#e63946", fg="white", activebackground="#c1121f",
        font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=16, pady=4,
    ).pack(side=tk.RIGHT, padx=12)

    tk.Button(
        btn_frame, text="Cancel", command=on_cancel,
        bg="#444", fg="white", activebackground="#333",
        font=("Segoe UI", 10), relief=tk.FLAT, padx=12, pady=4,
    ).pack(side=tk.RIGHT, padx=4)

    root.mainloop()
