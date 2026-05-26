# Hermes (Qwen) Takeover Guide

This is a practical handoff guide for continuing Botty development with minimal regressions.

## 1) Working model

- Treat Botty as a **state machine app** with side effects across:
  - D2R UI automation
  - OCR parsing
  - inventory/sell/stash routines
  - messaging (Discord/webhooks)
- Prefer **small, production-safe patches** over broad refactors.
- Prioritize runtime stability: avoid failing full runs because one subsystem is flaky.

## 2) Daily workflow (the one currently used)

1. Reproduce from fresh logs:
   - `log/log.txt`
   - `log/stats/events_*.jsonl`
   - `log/stats/stats_*.log`
2. Confirm failure path in code with `rg`.
3. Patch narrowly with `apply_patch`.
4. Validate:
   - `python -m compileall <changed files>`
   - targeted pytest where available
5. Commit with clear message and push to `main`.

## 3) Core debug commands

From repo root:

```powershell
rg -n "ERROR|WARNING|Failed to log exp|Discord|repair|sell" log/log.txt
Get-Content log/log.txt | Select-Object -Last 200
rg -n "<keyword>" src
python -m compileall src
python -m pytest -q test/test_discord_embeds.py
```

Use `rg` first; it is the fastest way to localize faults.

## 4) High-risk areas and current behavior

## 4.1 Repair/vendor flow stability

- A5 Larzuk detection is noisy and can fail.
- Current behavior:
  - A5 repair attempts normal flow.
  - Fallback to direct Larzuk template click.
  - If still failing, fallback attempt to Act 4 repair path.
  - For native-teleport builds, maintenance is best-effort (don’t always kill run on repair failure).

Files:
- `src/town/a5.py`
- `src/town/town_manager.py`
- `src/bot.py`

## 4.2 Discord messaging

Known historic issue:
- `Error sending Discord embed: 'NoneType' object has no attribute 'to_dict'`

Current fix:
- In `src/messages/discord_embeds.py`, `_send_embed` only passes `file` when attachment exists.
- If embed send fails, plain text fallback is attempted.

Configurable event toggles:
- `config/params.ini` -> `[discord_events]`
- Loaded in `src/config.py`
- Gated in `src/messages/messenger.py`

## 4.3 Selling safety

Current protections:
- Sell logs include item names (not only click position).
- `protect_shields_from_sell=1` blocks selling items whose detected name includes `shield`.

Files:
- `src/inventory/personal.py`
- `config/params.ini`
- `src/config.py`

## 4.4 XP logging

Two separate concerns exist:

1. OCR extraction:
- `src/ui/player_bar.py`
- parser now handles OCR ambiguity (`I/l/|` to `1`, `O/o` to `0`)

2. XP status projection math:
- `src/game_stats.py` `_create_msg()`
- edge cases now guarded (zero denominators => `n/a` instead of warning spam)

## 5) Testing strategy by change type

## 5.1 Messaging changes

- Run:
  - `python -m pytest -q test/test_discord_embeds.py`
- Optional live smoke:
  - instantiate `DiscordEmbeds` and call `send_message(...)` with local env webhook.

## 5.2 Config parsing changes

- Validate compile for `src/config.py`.
- Confirm app boot and key detection still works.
- Verify defaults in `params.ini` do not break existing users.

## 5.3 Inventory/sell logic

- Validate:
  - no exceptions in `inspect_items` / `transfer_items`.
  - log outputs now include item names.
- Prefer dry functional checks from logs before broad gameplay runs.

## 6) Git hygiene expected in this repo

- Keep personal files untracked:
  - `.env` (tracked template: `.env.example`)
  - `config/custom.ini` and local variants
  - logs/screenshots
- Do not revert unrelated user changes.
- Commit frequently with single-purpose messages.

## 7) CI and dependency expectations

- Windows is primary runtime target today.
- `tools/check_dependencies.ps1` + installer scripts are expected to pass on Win10/11.
- Linux support is planned (see `docs/linux_port_plan.md`) but not feature-complete.

## 8) “Done” checklist for a fix

- Reproduced from logs
- Root cause identified
- Patch applied in smallest reasonable scope
- Compile checks pass
- Target tests pass (or explicitly state why unavailable)
- Commit + push completed
- Behavior documented in README/params when user-visible

## 9) Fast triage mapping

- Repeating `Discord embed` errors:
  - check `discord_embeds.py` send kwargs, webhook validity, `[discord_events]`.
- Repeating repair fail loops:
  - inspect `a5.py` + `town_manager.py` fallback path and `bot.py` maintenance behavior.
- “Failed to log exp”:
  - separate OCR extraction (`ui/player_bar.py`) from status math (`game_stats.py`).
- Suspected accidental sell:
  - inspect `transfer_items` logs for item-name sells and shield-block warnings.

---

If you need to continue immediately, start from latest `main`, run a short bot session, and inspect only the newest 200-300 log lines before changing anything.
