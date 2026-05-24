"""
Run-selector GUI — opened via hotkey from the botty console.
Lets the user pick character and boss/farm runs.
Updates Config() in-memory; no file changes. Takes effect on the next game.
"""
import tkinter as tk
from tkinter import messagebox

# ── Character options ────────────────────────────────────────────────────────
CHAR_OPTIONS = [
    ("blizz_sorc",  "Blizzard Sorceress"),
    ("fohdin",      "Fist of Heavens Paladin"),
    ("hammerdin",   "Hammerdin"),
]

# ── Boss / farm run options ──────────────────────────────────────────────────
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

# ── Colours ──────────────────────────────────────────────────────────────────
BG_DARK   = "#1a1a2e"
BG_MID    = "#16213e"
BG_RADIO  = "#0f3460"
FG_GOLD   = "#e2b96e"
FG_LIGHT  = "#d4d4d4"
FG_DIM    = "#888888"
RED       = "#e63946"
RED_HOV   = "#c1121f"
GREY      = "#444444"
GREY_HOV  = "#333333"


def _currently_enabled_runs(config) -> set:
    enabled = set()
    for key, _ in ALL_RUNS:
        internal = _ROUTE_ALIASES.get(key, key)
        if config.routes.get(key) or config.routes.get(internal):
            enabled.add(key)
        if internal in config.routes_order or key in config.routes_order:
            enabled.add(key)
    return enabled


def _current_char(config) -> str:
    """Return the char type key from config, defaulting to the first option."""
    current = config.char.get("type", "")
    known = {k for k, _ in CHAR_OPTIONS}
    return current if current in known else CHAR_OPTIONS[0][0]


def open_run_selector(config) -> None:
    """
    Open the selector window (blocks the hotkey callback thread via mainloop).
    Mutates config.char["type"], config.routes, and config.routes_order on Apply.
    """
    currently_on   = _currently_enabled_runs(config)
    current_char   = _current_char(config)

    root = tk.Tk()
    root.title("Botty — Character & Runs")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    def section_label(parent, text):
        tk.Label(
            parent, text=text,
            bg=BG_DARK, fg=FG_GOLD,
            font=("Segoe UI", 10, "bold"),
            anchor="w", padx=4,
        ).pack(fill=tk.X, pady=(6, 2))

    # ── Header ───────────────────────────────────────────────────────────────
    header = tk.Frame(root, bg=BG_DARK, pady=8)
    header.pack(fill=tk.X)
    tk.Label(
        header, text="Botty Setup",
        bg=BG_DARK, fg=FG_GOLD,
        font=("Segoe UI", 14, "bold"),
    ).pack()
    tk.Label(
        header, text="(takes effect on next game)",
        bg=BG_DARK, fg=FG_DIM,
        font=("Segoe UI", 8),
    ).pack()

    # ── Body ─────────────────────────────────────────────────────────────────
    body = tk.Frame(root, bg=BG_DARK, padx=16, pady=4)
    body.pack(fill=tk.BOTH)

    # ── Character section ─────────────────────────────────────────────────────
    section_label(body, "Character")
    char_frame = tk.Frame(body, bg=BG_MID, padx=12, pady=8)
    char_frame.pack(fill=tk.X)

    char_var = tk.StringVar(value=current_char)
    for key, label in CHAR_OPTIONS:
        rb = tk.Radiobutton(
            char_frame, text=label, variable=char_var, value=key,
            bg=BG_MID, fg=FG_LIGHT, selectcolor=BG_RADIO,
            activebackground=BG_MID, activeforeground=FG_GOLD,
            font=("Segoe UI", 10),
            anchor="w",
        )
        rb.pack(fill=tk.X, pady=1)

    # ── Runs section ──────────────────────────────────────────────────────────
    section_label(body, "Boss / Farm Runs")
    runs_frame = tk.Frame(body, bg=BG_MID, padx=12, pady=8)
    runs_frame.pack(fill=tk.X)

    run_vars: list[tuple[str, tk.BooleanVar]] = []
    for key, label in ALL_RUNS:
        var = tk.BooleanVar(value=(key in currently_on))
        cb = tk.Checkbutton(
            runs_frame, text=label, variable=var,
            bg=BG_MID, fg=FG_LIGHT, selectcolor=BG_RADIO,
            activebackground=BG_MID, activeforeground=FG_GOLD,
            font=("Segoe UI", 10),
            anchor="w",
        )
        cb.pack(fill=tk.X, pady=1)
        run_vars.append((key, var))

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(root, bg=BG_DARK, pady=10)
    btn_frame.pack(fill=tk.X)

    def on_apply():
        selected_runs = [k for k, v in run_vars if v.get()]
        if not selected_runs:
            messagebox.showwarning("No runs selected", "Please select at least one run.", parent=root)
            return

        # Apply character
        chosen_char = char_var.get()
        config.char["type"] = chosen_char

        # Apply routes
        new_routes = {}
        new_order = []
        for key in selected_runs:
            new_routes[key] = True
            internal = _ROUTE_ALIASES.get(key, key)
            new_routes[internal] = True
            if internal not in new_order:
                new_order.append(internal)
        config.routes = new_routes
        config.routes_order = new_order

        char_label  = next(l for k, l in CHAR_OPTIONS if k == chosen_char)
        run_labels  = [l for k, l in ALL_RUNS if k in selected_runs]
        print(f"\n[Selector] Character : {char_label}")
        print(f"[Selector] Runs      : {', '.join(run_labels)}")
        print("(takes effect on next game)\n")

        root.destroy()

    def on_cancel():
        root.destroy()

    tk.Button(
        btn_frame, text="Apply", command=on_apply,
        bg=RED, fg="white", activebackground=RED_HOV,
        font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=16, pady=4,
    ).pack(side=tk.RIGHT, padx=12)

    tk.Button(
        btn_frame, text="Cancel", command=on_cancel,
        bg=GREY, fg="white", activebackground=GREY_HOV,
        font=("Segoe UI", 10), relief=tk.FLAT, padx=12, pady=4,
    ).pack(side=tk.RIGHT, padx=4)

    root.mainloop()
