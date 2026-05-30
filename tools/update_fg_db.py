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
        scrape_seq INTEGER,
        day INTEGER,
        item TEXT,
        median_fg REAL,
        avg_fg REAL,
        min_fg REAL,
        max_fg REAL,
        samples INTEGER,
        scraped_at TEXT,
        PRIMARY KEY (scrape_seq, item)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sellers (
        scrape_seq INTEGER,
        item TEXT,
        user TEXT,
        price REAL,
        post_link TEXT,
        scraped_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # Assign a sequential scrape number
    scraped_at = data['generated_at']
    row = c.execute('SELECT MAX(scrape_seq) FROM prices').fetchone()
    scrape_seq = (row[0] or 0) + 1

    # Remove old data from this scrape run (idempotent)
    c.execute('DELETE FROM prices WHERE scrape_seq = ?', (scrape_seq,))
    c.execute('DELETE FROM sellers WHERE scrape_seq = ?', (scrape_seq,))

    # Insert prices
    for day_key, items in data.get('estimates', {}).items():
        day_num = int(day_key.replace('day_', ''))
        for item, info in items.items():
            c.execute(
                'INSERT OR REPLACE INTO prices (scrape_seq, day, item, median_fg, avg_fg, min_fg, max_fg, samples, scraped_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (scrape_seq, day_num, item, info.get('median_fg', 0), info.get('avg_fg', 0), info.get('min_fg', 0), info.get('max_fg', 0), info['samples'], scraped_at)
            )

    # Insert sellers
    for seller in data.get('sellers', []):
        c.execute(
            'INSERT INTO sellers (scrape_seq, item, user, price, post_link, scraped_at) VALUES (?, ?, ?, ?, ?, ?)',
            (scrape_seq, seller.get('item', ''), seller.get('user', ''), seller.get('price', 0), seller.get('post_link', ''), scraped_at)
        )

    # Update meta
    for key in ['generated_at', 'ladder_start_date', 'days', 'topics_scanned']:
        if key in data:
            c.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', (key, str(data[key])))

    conn.commit()

    # Report
    price_count = c.execute('SELECT COUNT(*) FROM prices').fetchone()[0]
    seller_count = c.execute('SELECT COUNT(*) FROM sellers').fetchone()[0]
    print(f"\nDatabase updated (scrape_seq={scrape_seq}): {price_count} price entries, {seller_count} seller entries")

    print("\n=== TOP 10 MOST EXPENSIVE ===")
    for row in c.execute("SELECT item, median_fg, avg_fg, min_fg, max_fg, samples FROM prices WHERE scrape_seq=? ORDER BY median_fg DESC LIMIT 10", (scrape_seq,)):
        print(f"  {row[0]:<25} med={row[1]:>7.0f} avg={row[2]:>7.0f} min={row[3]:>5.0f} max={row[4]:>6.0f}  n={row[5]}")

    print("\n=== CHEAPEST SELLERS PER ITEM ===")
    for row in c.execute(
        "SELECT item, user, price, post_link FROM sellers WHERE scrape_seq=? ORDER BY item, price",
        (scrape_seq,)
    ):
        print(f"  {row[0]}: {row[1]} @ {row[2]} FG - {row[3]}")

    print("\n=== ITEMS WITH MOST SELLERS ===")
    for row in c.execute(
        "SELECT item, COUNT(*) as cnt FROM sellers WHERE scrape_seq=? GROUP BY item ORDER BY cnt DESC LIMIT 10",
        (scrape_seq,)
    ):
        print(f"  {row[0]}: {row[1]} sellers")

    # Price changes vs previous scrape
    prev_seq = c.execute(
        "SELECT MAX(scrape_seq) FROM prices WHERE scrape_seq < ?", (scrape_seq,)
    ).fetchone()[0]
    if prev_seq is not None:
        print(f"\n=== PRICE CHANGES VS SCRAPE #{prev_seq} ===")
        for row in c.execute(
            "SELECT p1.item, p1.median_fg, p2.median_fg, p1.samples, p2.samples FROM prices p1 JOIN prices p2 ON p1.item=p2.item WHERE p1.scrape_seq=? AND p2.scrape_seq=? ORDER BY p2.median_fg - p1.median_fg",
            (prev_seq, scrape_seq)
        ):
            diff = row[2] - row[1]
            if abs(diff) > 0:
                sign = '+' if diff > 0 else ''
                print(f"  {row[0]:<25} {row[1]:>7.0f} -> {row[2]:>7.0f} FG ({sign}{diff:.0f})  n={row[3]}->{row[4]}")

    conn.close()


if __name__ == "__main__":
    main()
