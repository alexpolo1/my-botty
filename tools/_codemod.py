"""Code-mod helpers for botty route scaffolding."""
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


def insert_into_do_runs(bot_path, name):
    text = _read(bot_path)
    needle = Q2 + "run_" + name + Q2
    if needle in text:
        return False
    m = re.search(r'(self\._do_runs = \{.*?)(\s*\})', text, re.DOTALL)
    if not m:
        raise ValueError("Cannot find self._do_runs dict")
    before = m.group(1)
    last_line = before.rstrip().rsplit(NL, 1)[-1]
    indent = " " * (len(last_line) - len(last_line.lstrip()))
    entry = NL + indent + Q2 + "run_" + name + Q2
    entry += ": Config().routes.get(" + Q2 + "run_" + name + Q2 + ")," + chr(10)
    result = text[:m.start(2)] + entry + m.group(2) + text[m.end():]
    _write(bot_path, result)
    return True


def undo_do_runs(bot_path, name):
    text = _read(bot_path)
    en = re.escape(name)
    pat = r"\s*" + Q2 + "run_" + en + Q2 + ": Config\(\)\.routes\.get\(" + Q2 + "run_" + en + Q2 + "\),\s*" + NL
    t = re.sub(pat, "", text)
    if t == text:
        return False
    _write(bot_path, t)
    return True


def insert_instantiation(bot_path, name, class_name):
    text = _read(bot_path)
    if "self._" + name + " = " in text:
        return False
    pat = r'(\s+self\._[a-z_]+ = [A-Z][a-zA-Z]*\(self\._pather, self\._town_manager[^\)]+\))' + NL
    matches = list(re.finditer(pat, text))
    if not matches:
        raise ValueError("Cannot find run instantiation pattern")
    last = matches[-1]
    indent = last.group(1)[:len(last.group(1)) - len(last.group(1).lstrip())]
    new_line = indent + "self._" + name + " = " + class_name + "(self._pather, self._town_manager, self._char, self._pickit, self._do_runs)" + NL
    result = text[:last.end()] + new_line + text[last.end():]
    _write(bot_path, result)
    return True


def undo_instantiation(bot_path, name):
    text = _read(bot_path)
    pat = r'\s+self\._' + re.escape(name) + r'\s*=\s*[A-Za-z_]+\([^\)]+\)\s*' + NL
    t = re.sub(pat, "", text)
    if t == text:
        return False
    _write(bot_path, t)
    return True


def insert_state(bot_path, name):
    text = _read(bot_path)
    sm = re.search(r'self\._states\s*=\s*\[([^\]]*)\]', text)
    if sm and Q1 + name + Q1 in sm.group(1):
        return False
    m = re.search(r'(self\._states\s*=\s*\[.*?)(\])', text, re.DOTALL)
    if not m:
        raise ValueError("Cannot find self._states list")
    inner = m.group(1)
    if inner.rstrip().endswith(","):
        inner = inner + Q1 + name + Q1
    else:
        inner = inner + ", " + Q1 + name + Q1
    result = text[:m.start(1)] + inner + m.group(2) + text[m.end():]
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


def insert_transitions(bot_path, name):
    text = _read(bot_path)
    if Q1 + "trigger" + Q1 + ": " + Q1 + "run_" + name + Q1 in text:
        return False
    marker = "# End run / game"
    if marker not in text:
        raise ValueError("Cannot find # End run / game")
    idx = text.index(marker)
    ls = text.rfind(NL, 0, idx) + 1
    indent = text[ls:idx]
    tl = indent + LB + " " + Q1 + "trigger" + Q1 + ": " + Q1 + "run_" + name + Q1 + ", " + Q1 + "source" + Q1 + ": " + Q1 + "town" + Q1 + ", " + Q1 + "dest" + Q1 + ": " + Q1 + name + Q1 + ", " + Q1 + "before" + Q1 + ": " + Q2 + "on_run_" + name + Q2 + " " + RB + ","
    tl += NL
    text = text[:idx] + tl + text[idx:]
    m = re.search(r"('trigger': 'end_run', 'source': \[)([^\]]+)(\])", text, re.DOTALL)
    if m:
        s = m.group(2).strip()
        s = s + ("" if s.endswith(",") else ",") + " " + Q1 + name + Q1
        text = text[:m.start(2)] + s + text[m.end(2):]
    m = re.search(r"('trigger': 'end_game', 'source': \[)([^\]]+)(\])", text, re.DOTALL)
    if m:
        s = m.group(2).strip()
        s = s + ("" if s.endswith(",") else ",") + " " + Q1 + name + Q1
        text = text[:m.start(2)] + s + text[m.end(2):]
    _write(bot_path, text)
    return True


def undo_transitions(bot_path, name):
    text = _read(bot_path)
    changed = False
    en = re.escape(name)
    pat = re.compile(
        r'\s*' + LB + r'\s*' + Q1 + 'trigger' + Q1 + ':\s*' + Q1 + 'run_' + en
        + Q1 + '.*?' + Q1 + 'before' + Q1 + ':\s*' + Q2 + 'on_run_' + en + Q2 + '\s*' + RB + r',\s*' + NL,
        re.DOTALL,
    )
    t = pat.sub("", text)
    if t != text:
        text = t
        changed = True
    for trigger in ['end_run', 'end_game']:
        pat2 = r"('trigger':\s*" + trigger + r"',\s*'source':\s*)\[([^\]]*)\]"
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
    h = []
    h.append("")
    h.append("    def on_run_" + name + "(self):")
    h.append("        res = False")
    h.append('        self._do_runs[' + Q2 + 'run_' + name + Q2 + '] = False')
    h.append('        self._game_stats.update_location(' + Q2 + short + Q2 + ')')
    h.append("        self._curr_loc = self._" + name + ".approach(self._curr_loc)")
    h.append("        if self._curr_loc:")
    h.append("            set_pause_state(False)")
    h.append("            res = self._" + name + ".battle(not self._pre_buffed)")
    h.append("        self._ending_run_helper(res)")
    handler = NL.join(h) + NL
    result = text[:last.end()] + handler + text[last.end():]
    _write(bot_path, result)
    return True


def undo_handler(bot_path, name):
    text = _read(bot_path)
    pat = re.compile(r'\n\s*def on_run_' + re.escape(name) + r'\(self\):.*?_ending_run_helper\(res\)\n', re.DOTALL)
    t = pat.sub("", text)
    if t == text:
        return False
    _write(bot_path, t)
    return True


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

