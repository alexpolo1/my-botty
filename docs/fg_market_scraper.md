# FG Market Scraper (Day 1-14)

This tool estimates FG prices per ladder day by scraping public trade topics from:
- https://forums.d2jsp.org/forum.php?f=271

## Script
- `tools/fg_market_scraper.py`

## What it does
1. Scans forum listing pages for topic links.
2. Fetches topic pages (rate-limited).
3. Detects known item/rune keywords.
4. Extracts `fg` prices from post text.
5. Buckets prices by ladder day index (Day 1..Day N).
6. Writes median estimates + sample counts.

## Usage
From repo root:

```powershell
python tools/fg_market_scraper.py --ladder-start-date 2026-05-23 --days 14
```

Output:
- `config/fg_daily_estimates.json`

## Tuning
- `--max-forum-pages`: listing pages to scan (default 40)
- `--max-topics`: hard cap on fetched topics (default 800)
- `--delay-s`: delay between requests (default 0.35s)

Example heavier run:

```powershell
python tools/fg_market_scraper.py --ladder-start-date 2026-05-23 --days 14 --max-forum-pages 120 --max-topics 2400 --delay-s 0.5
```

## Notes
- This is a heuristic estimator, not a full market engine.
- Accuracy depends on post format quality and keyword matches.
- Keep request rate polite to avoid stressing the forum.
- Some environments/IPs will receive HTTP `403` from d2jsp. In that case use:
  - `config/fg_day_estimates.json` (Day 1-14 estimated multiplier model from Day 3 snapshot),
  - and update `config/fg_prices.json` manually from your current market sample.
