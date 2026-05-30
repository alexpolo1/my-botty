#!/bin/bash
# Run FG price scrape pipeline: playwright scrape -> offline parse -> DB update
cd /c/Users/alex/Downloads/my-botty

# Step 1: Scrape d2jsp with Playwright (bypasses Cloudflare)
/c/Python313/python tools/playwright_fg_scraper.py
SCRAPER_EXIT=$?
if [ $SCRAPER_EXIT -ne 0 ]; then
    echo "ERROR: Playwright scraper failed (exit $SCRAPER_EXIT)"
    exit 1
fi

# Step 2: Parse saved HTML into price estimates
/c/Python313/python tools/fg_market_scraper.py --offline-dir data/d2jsp_pages --ladder-start-date 2026-05-12 --days 21
PARSER_EXIT=$?
if [ $PARSER_EXIT -ne 0 ]; then
    echo "ERROR: Offline parser failed (exit $PARSER_EXIT)"
    exit 1
fi

# Step 3: Update SQLite database
/c/Python313/python tools/update_fg_db.py
