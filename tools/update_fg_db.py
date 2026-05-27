#!/usr/bin/env python
"""Update fg_prices.db from the latest fg_daily_estimates.json scrape results."""
import json
import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "config" / "fg_prices.db"
JSON_PATH = PROJECT_DIR / "config" / "fg_daily_estimates.json"


def main():
    # Load results
    if not JSON_PATH.exists():
        print(f"ERROR: {JSON_PATH} not found — run the scraper first")
        return

    with open(JSON_PATH) as f:
        data = json.load(f)

    print(f"Topics scanned: {data['topics_scanned']}")
    print(f"Sellers found: {len(data.get('sellers', []))}")

    # Update database
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Ensure tables exist
    c.execute('''CREATE TABLE IF NOT EXISTS prices (
        day INTEGER,
        item TEXT,
        median_fg REAL,
        samples INTEGER,
        scraped_at TEXT,
        PRIMARY KEY (day, item, scraped_at)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sellers (
        item TEXT,
        user TEXT,
        price REAL,
        scraped_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # Remove old data from this scrape run (idempotent)
    scraped_at = data['generated_at']
    c.execute('DELETE FROM prices WHERE scraped_at = ?', (scraped_at,))
    c.execute('DELETE FROM sellers WHERE scraped_at = ?', (scraped_at,))

    # Insert prices
    for day_key, items in data.get('estimates', {}).items():
        day_num = int(day_key.replace('day_', ''))
        for item, info in items.items():
            c.execute(
                'INSERT OR REPLACE INTO prices (day, item, median_fg, samples, scraped_at) VALUES (?, ?, ?, ?, ?)',
                (day_num, item, info['median_fg'], info['samples'], scraped_at)
            )

    # Insert sellers
    for seller in data.get('sellers', []):
        c.execute(
            'INSERT INTO sellers (item, user, price, scraped_at) VALUES (?, ?, ?, ?)',
            (seller['item'], seller['user'], seller['price'], scraped_at)
        )

    # Update meta
    for key in ['generated_at', 'ladder_start_date', 'days', 'topics_scanned']:
        if key in data:
            c.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', (key, str(data[key])))

    conn.commit()

    # Report
    price_count = c.execute('SELECT COUNT(*) FROM prices').fetchone()[0]
    seller_count = c.execute('SELECT COUNT(*) FROM sellers').fetchone()[0]
    print(f"\nDatabase updated: {price_count} price entries, {seller_count} seller entries")

    print("\n=== TOP 10 MOST EXPENSIVE ===")
    for row in c.execute("SELECT item, median_fg, samples FROM prices WHERE scraped_at=? ORDER BY median_fg DESC LIMIT 10", (scraped_at,)):
        print(f"  {row[0]}: {row[1]} FG ({row[2]} samples)")

    print("\n=== CHEAPEST SELLERS PER ITEM ===")
    for row in c.execute(
        "SELECT item, user, price FROM sellers WHERE scraped_at=? ORDER BY item, price",
        (scraped_at,)
    ):
        print(f"  {row[0]}: {row[1]} @ {row[2]} FG")

    print("\n=== ITEMS WITH MOST SELLERS ===")
    for row in c.execute(
        "SELECT item, COUNT(*) as cnt FROM sellers WHERE scraped_at=? GROUP BY item ORDER BY cnt DESC LIMIT 10",
        (scraped_at,)
    ):
        print(f"  {row[0]}: {row[1]} sellers")

    # Price changes vs previous scrape
    prev_scrape = c.execute(
        "SELECT DISTINCT scraped_at FROM prices WHERE scraped_at != ? ORDER BY scraped_at DESC LIMIT 1",
        (scraped_at,)
    ).fetchone()
    if prev_scrape:
        print("\n=== PRICE CHANGES VS PREVIOUS SCRAPE ===")
        for row in c.execute(
            "SELECT p1.item, p1.median_fg, p2.median_fg FROM prices p1 JOIN prices p2 ON p1.item=p2.item WHERE p1.scraped_at=? AND p2.scraped_at=? ORDER BY p2.median_fg - p1.median_fg",
            (prev_scrape[0][0], scraped_at)
        ):
            diff = row[2] - row[1]
            sign = '+' if diff > 0 else ''
            print(f"  {row[0]}: {row[1]} -> {row[2]} FG ({sign}{diff})")

    conn.close()


if __name__ == "__main__":
    main()
