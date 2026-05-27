#!/usr/bin/env python
"""Query FG price database.

Usage:
    python query_fg_prices.py                          # Show all prices
    python query_fg_prices.py Mara                     # Filter by item name
    python query_fg_prices.py --top 10                 # Top 10 most expensive
    python query_fg_prices.py --cheapest Mara          # Cheapest seller for item
    python query_fg_prices.py --trend Mara             # Price history for item
    python query_fg_prices.py --sellers Mara           # All sellers for item
    python query_fg_prices.py --day 1                  # Prices for specific day
    python query_fg_prices.py --min 100                # Items >= 100 FG
    python query_fg_prices.py --max 50                 # Items <= 50 FG
"""
import argparse
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "config" / "fg_prices.db"


def query(db, sql, params=()):
    return db.execute(sql, params).fetchall()


def main():
    parser = argparse.ArgumentParser(description="Query FG price database")
    parser.add_argument("item", nargs="?", default=None, help="Item name (partial match)")
    parser.add_argument("--top", type=int, default=None, help="Show N most expensive items")
    parser.add_argument("--cheapest", type=str, default=None, help="Cheapest seller for item")
    parser.add_argument("--trend", type=str, default=None, help="Price history for item")
    parser.add_argument("--sellers", type=str, default=None, help="All sellers for item")
    parser.add_argument("--day", type=int, default=None, help="Prices for specific day")
    parser.add_argument("--min", type=float, default=None, help="Minimum price in FG")
    parser.add_argument("--max", type=float, default=None, help="Maximum price in FG")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))

    # Top N most expensive
    if args.top:
        rows = query(conn, "SELECT day, item, median_fg, samples FROM prices ORDER BY median_fg DESC LIMIT ?", (args.top,))
        print(f"Top {args.top} most expensive:")
        print(f"{'Day':<5} {'Item':<25} {'Price':>8} {'Samples':>8}")
        print("-" * 50)
        for r in rows:
            print(f"{r[0]:<5} {r[1]:<25} {r[2]:>8.1f} {r[3]:>8}")
        conn.close()
        return

    # Cheapest seller
    if args.cheapest:
        rows = query(conn,
            "SELECT item, user, price FROM sellers WHERE item LIKE ? ORDER BY price ASC LIMIT 5",
            (f"%{args.cheapest}%",))
        if rows:
            print(f"Cheapest sellers for '{args.cheapest}':")
            print(f"{'Item':<25} {'Seller':<20} {'Price':>8}")
            print("-" * 55)
            for r in rows:
                print(f"{r[0]:<25} {r[1]:<20} {r[2]:>8.1f}")
        else:
            print(f"No sellers found for '{args.cheapest}' (seller data may not be populated yet)")
        conn.close()
        return

    # Price trend
    if args.trend:
        rows = query(conn,
            "SELECT scraped_at, median_fg, samples FROM prices WHERE item LIKE ? ORDER BY scraped_at",
            (f"%{args.trend}%",))
        if rows:
            print(f"Price trend for '{args.trend}':")
            print(f"{'Scraped At':<30} {'Price':>8} {'Samples':>8}")
            print("-" * 50)
            for r in rows:
                print(f"{r[0]:<30} {r[1]:>8.1f} {r[2]:>8}")
        else:
            print(f"No price data for '{args.trend}'")
        conn.close()
        return

    # All sellers for item
    if args.sellers:
        rows = query(conn,
            "SELECT item, user, price FROM sellers WHERE item LIKE ? ORDER BY price ASC",
            (f"%{args.sellers}%",))
        if rows:
            print(f"All sellers for '{args.sellers}':")
            print(f"{'Item':<25} {'Seller':<20} {'Price':>8}")
            print("-" * 55)
            for r in rows:
                print(f"{r[0]:<25} {r[1]:<20} {r[2]:>8.1f}")
        else:
            print(f"No sellers found for '{args.sellers}'")
        conn.close()
        return

    # Specific day
    if args.day is not None:
        rows = query(conn,
            "SELECT item, median_fg, samples FROM prices WHERE day = ? ORDER BY median_fg DESC",
            (args.day,))
        if rows:
            print(f"Day {args.day} prices:")
            print(f"{'Item':<25} {'Price':>8} {'Samples':>8}")
            print("-" * 45)
            for r in rows:
                print(f"{r[0]:<25} {r[1]:>8.1f} {r[2]:>8}")
        else:
            print(f"No data for day {args.day}")
        conn.close()
        return

    # Price range filters or item name filter
    conditions = []
    params = []
    if args.min is not None:
        conditions.append("median_fg >= ?")
        params.append(args.min)
    if args.max is not None:
        conditions.append("median_fg <= ?")
        params.append(args.max)
    if args.item:
        conditions.append("item LIKE ?")
        params.append(f"%{args.item}%")

    if not conditions:
        # Default: show all prices sorted by price desc
        rows = query(conn, "SELECT day, item, median_fg, samples FROM prices ORDER BY median_fg DESC")
        print(f"{'Day':<5} {'Item':<25} {'Price':>8} {'Samples':>8}")
        print("-" * 50)
        for r in rows:
            print(f"{r[0]:<5} {r[1]:<25} {r[2]:>8.1f} {r[3]:>8}")
        print(f"\nTotal: {len(rows)} items")
        conn.close()
        return

    where = " AND ".join(conditions)
    rows = query(conn, f"SELECT day, item, median_fg, samples FROM prices WHERE {where} ORDER BY median_fg DESC", params)

    if rows:
        filters = []
        if args.min is not None: filters.append(f">= {args.min} FG")
        if args.max is not None: filters.append(f"<= {args.max} FG")
        if args.item: filters.append(f"like '{args.item}'")
        print(f"Items ({', '.join(filters)}):")
        print(f"{'Day':<5} {'Item':<25} {'Price':>8} {'Samples':>8}")
        print("-" * 50)
        for r in rows:
            print(f"{r[0]:<5} {r[1]:<25} {r[2]:>8.1f} {r[3]:>8}")
        print(f"\nTotal: {len(rows)} items")
    else:
        print("No items found matching criteria")

    conn.close()


if __name__ == "__main__":
    main()
