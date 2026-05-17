"""Code-mod helpers for botty route scaffolding.

Uses line-based insertion for reliable idempotency and clean undo.
"""
import os
import re
from pathlib import Path


def _read(path):
    return Path(path).read_text()


def _write(path, text):
    Path(path).write_text(text)


NL = chr(10)
Q1 = chr(39)
Q2 = chr(34)
LB = chr(123)
RB = chr(125)


# ─── __init__.py import ───────────────────────────────────────────────

def insert_init_import(init_path, name, class_name):
    text = _read(init_path)
    line = "from ." + name + " import " + class_name
    if line in text:
        return False
    if not text.endswith(NL):
        text += NL
    text += line + NL
    _write(init_path, text)
    return True


def undo_init_import(init_path, name):
    text = _read(init_path)
    ll = text.splitlines(keepends=True)
    new = [l for l in ll if not l.strip().startswith("from ." + name + " import")]
    if len(new) == len(ll):
        return False
    _write(init_path, "".join(new))
    return True


# ─── _do_runs dict ────────────────────────────────────────────────────

def insert_into_do_runs(bot_path, name):
    text = _read(bot_path)
    if Q2 + "run_" + name + Q2 in text:
        return False
    # Find the last "run_XX" entry line before the closing }
    m = re.search(
        r'(self\._do_runs = \{.*?)(\s+"run_\w+":\s*Config\(\)\.routes\.get\([^)]+\),\s*\n)(\s*\})',
        text, re.DOTALL
    )
    if not m:
        raise ValueError("Cannot find last entry in self._do_runs dict")
    last_entry = m.group(2)
    indent = " " * (len(last_entry) - len(last_entry.lstrip()))
    entry = indent + Q2 + "run_" + name + Q2
    entry += ": Config().routes.get(" + Q2 + "run_" + name + Q2 + ")," + NL
    result = text[:m.start(2)] + m.group(2) + entry + m.group(3) + text[m.end():]
    _write(bot_path, result)
    return True


def undo_do_runs(bot_path, name):
    text = _read(bot_path)
    lines = text.split(NL)
    en = name
    new_lines = []
    removed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(Q2 + "run_" + en + Q2 + ":") and "Config().routes.get" in stripped:
            removed = True
            continue
        new_lines.append(line)
    if not removed:
        return False
    _write(bot_path, NL.join(new_lines))
    return True


# ─── instantiation block ──────────────────────────────────────────────

def insert_instantiation(bot_path, name, class_name):
    text = _read(bot_path)
    if "self._" + name + " = " in text:
        return False
    pat = r'(self\._[a-z_]+ = [A-Z][a-zA-Z]*\(self\._pather, self\._town_manager[^)]+\))(\s*\n)'
    matches = list(re.finditer(pat, text))
    if not matches:
        raise ValueError("Cannot find run instantiation pattern")
    last = matches[-1]
    # Extract indentation from the start of the matched line
    before_match = text[:last.start(1)]
    line_start = before_match.rfind(NL) + 1
    indent = before_match[line_start:last.start(1)]
    new_line = indent + "self._" + name + " = " + class_name
    new_line += "(self._pather, self._town_manager, self._char, self._pickit, self._do_runs)" + NL
    result = text[:last.end()] + new_line + text[last.end():]
    _write(bot_path, result)
    return True


def undo_instantiation(bot_path, name):
    text = _read(bot_path)
    lines = text.split(NL)
    new_lines = []
    removed = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("self._" + name + " = ") and "(self._pather" in stripped:
            removed = True
            continue
        new_lines.append(line)
    if not removed:
        return False
    _write(bot_path, NL.join(new_lines))
    return True


# ─── _states list ─────────────────────────────────────────────────────

def insert_state(bot_path, name):
    text = _read(bot_path)
    m = re.search(r'(self\._states\s*=\s*\[)(.*?)(\])', text, re.DOTALL)
    if not m:
        raise ValueError("Cannot find self._states list")
    inner = m.group(2)
    needle = Q1 + name + Q1
    if needle in inner:
        return False
    # Append with comma
    if inner.rstrip().endswith(","):
        inner = inner + " " + needle
    else:
        inner = inner + ", " + needle
    result = text[:m.start(2)] + inner + m.group(3) + text[m.end():]
    _write(bot_path, result)
    return True


def undo_state(bot_path, name):
    text = _read(bot_path)
    m = re.search(r'(self\._states\s*=\s*\[)(.*?)(\])', text, re.DOTALL)
    if not m:
        return False
    inner = m.group(2)
    en = re.escape(name)
    new_inner = re.sub(r',\s*' + Q1 + en + Q1, '', inner)
    new_inner = re.sub(Q1 + en + Q1, '', new_inner)
    if new_inner == inner:
        return False
    text = text[:m.start(2)] + new_inner + text[m.end(2):]
    _write(bot_path, text)
    return True


# ─── _transitions list ────────────────────────────────────────────────

def insert_transitions(bot_path, name):
    text = _read(bot_path)
    if Q1 + "trigger" + Q1 + ": " + Q1 + "run_" + name + Q1 in text:
        return False
    marker = "# End run / game"
    if marker not in text:
        raise ValueError("Cannot find # End run / game")
    idx = text.index(marker)
    # Find the line start for proper indentation — insert BEFORE the comment line
    ls = text.rfind(NL, 0, idx) + 1
    indent = text[ls:idx]
    # Build the new transition row with proper formatting
    tl = indent + LB + " 'trigger': 'run_" + name + "', 'source': 'town', 'dest': '"
    tl += name + "', 'before': " + Q2 + "on_run_" + name + Q2 + " " + RB + ","
    tl += NL
    # Insert at line start, before the comment line (preserving its indentation)
    text = text[:ls] + tl + text[ls:]
    # Add name to end_run source list
    m = re.search(r"('trigger': 'end_run', 'source': \[)([^\]]+)(\])", text, re.DOTALL)
    if m:
        s = m.group(2).strip()
        if not s.endswith(","):
            s += ","
        s += " " + Q1 + name + Q1
        text = text[:m.start(2)] + s + text[m.end(2):]
    # Add name to end_game source list
    m = re.search(r"('trigger': 'end_game', 'source': \[)([^\]]+)(\])", text, re.DOTALL)
    if m:
        s = m.group(2).strip()
        if not s.endswith(","):
            s += ","
        s += " " + Q1 + name + Q1
        text = text[:m.start(2)] + s + text[m.end(2):]
    _write(bot_path, text)
    return True


def undo_transitions(bot_path, name):
    text = _read(bot_path)
    en = name
    changed = False

    # Remove the transition row for this route using line-by-line removal
    lines = text.split(NL)
    new_lines = []
    removed_transition = False
    for line in lines:
        stripped = line.strip()
        # Match lines containing the transition dict for this route
        if (stripped.startswith(LB) and
            f"'run_{en}'" in stripped and
            f"on_run_{en}" in stripped and
            stripped.endswith(RB + ",")):
            removed_transition = True
            changed = True
            continue
        new_lines.append(line)
    if removed_transition:
        text = NL.join(new_lines)

    # Remove name from end_run and end_game source lists
    for trigger in ["end_run", "end_game"]:
        pat2 = r"('trigger': 'end_run', 'source': \[)([^\]]+)(\])" if trigger == "end_run" else r"('trigger': 'end_game', 'source': \[)([^\]]+)(\])"
        m = re.search(pat2, text, re.DOTALL)
        if m:
            sources = m.group(2)
            ns = re.sub(r',\s*' + Q1 + en + Q1, '', sources)
            ns = re.sub(Q1 + en + Q1, '', ns)
            if ns != sources:
                text = text[:m.start(2)] + ns + text[m.end(2):]
                changed = True

    if changed:
        _write(bot_path, text)
    return changed


# ─── on_run_* handler ─────────────────────────────────────────────────

def insert_handler(bot_path, name, display):
    text = _read(bot_path)
    if "def on_run_" + name in text:
        return False
    short = display[:3] if display else name[:3]
    pat = r'(    def on_run_[a-z_]+\(self\):.*?_ending_run_helper\(res\))'
    matches = list(re.finditer(pat, text, re.DOTALL))
    if not matches:
        raise ValueError("Cannot find existing handler pattern")
    last = matches[-1]
    h = [
        "",
        "    def on_run_" + name + "(self):",
        "        res = False",
        "        self._do_runs[" + Q2 + "run_" + name + Q2 + "] = False",
        "        self._game_stats.update_location(" + Q2 + short + Q2 + ")",
        "        self._curr_loc = self._" + name + ".approach(self._curr_loc)",
        "        if self._curr_loc:",
        "            set_pause_state(False)",
        "            res = self._" + name + ".battle(not self._pre_buffed)",
        "        self._ending_run_helper(res)",
    ]
    handler = NL.join(h) + NL
    result = text[:last.end()] + handler + text[last.end():]
    _write(bot_path, result)
    return True


def undo_handler(bot_path, name):
    text = _read(bot_path)
    pat = re.compile(
        r'\n\s*def on_run_' + re.escape(name) + r'\(self\):.*?_ending_run_helper\(res\)\n',
        re.DOTALL
    )
    t = pat.sub("", text)
    if t == text:
        return False
    _write(bot_path, t)
    return True


# ─── batch operations ──────────────────────────────────────────────────

def apply_all(base_dir, name, class_name, display, act, location_id=None):
    bp = os.path.join(base_dir, "src", "bot.py")
    ip = os.path.join(base_dir, "src", "run", "__init__.py")
    actions = []
    if insert_init_import(ip, name, class_name):
        actions.append("init_import")
    if insert_into_do_runs(bp, name):
        actions.append("do_runs")
    if insert_instantiation(bp, name, class_name):
        actions.append("instantiation")
    if insert_state(bp, name):
        actions.append("state")
    if insert_transitions(bp, name):
        actions.append("transitions")
    if insert_handler(bp, name, display):
        actions.append("handler")
    return actions


def undo_all(base_dir, name):
    bp = os.path.join(base_dir, "src", "bot.py")
    ip = os.path.join(base_dir, "src", "run", "__init__.py")
    text = _read(ip)
    m = re.search(r'from \.' + re.escape(name) + r' import ([A-Za-z_]+)', text)
    cn = m.group(1) if m else name.replace("_", " ").title().replace(" ", "")
    actions = []
    if undo_handler(bp, name):
        actions.append("handler")
    if undo_transitions(bp, name):
        actions.append("transitions")
    if undo_state(bp, name):
        actions.append("state")
    if undo_instantiation(bp, name):
        actions.append("instantiation")
    if undo_do_runs(bp, name):
        actions.append("do_runs")
    if undo_init_import(ip, name):
        actions.append("init_import")
    rf = os.path.join(base_dir, "src", "run", name + ".py")
    if os.path.exists(rf):
        os.remove(rf)
        actions.append("removed_run_file")
    return actions
