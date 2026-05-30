#!/usr/bin/env python
"""Improve FG daily estimates by filtering spam/outliers and computing trimmed statistics.

The d2jsp forum scraper produces noisy data because:
1. Spam posts with "3 FG" for everything pull down medians
2. Some posts list multiple items at once, causing false matches
3. Multi-item topics distribute prices incorrectly

This script re-processes the saved HTML files with better filtering:
- Remove prices < 5 FG (likely spam)
- Use trimmed mean (remove bottom 20% and top 20%)
- Only count prices from the actual poster, not random mentions
"""
import argparse
import datetime as dt
import json
import re
import statistics
import sys
from collections import defaultdict
from html import unescape
from pathlib import Path

# Import from existing scraper
sys.path.insert(0, str(Path(__file__).parent))
from fg_market_scraper import (
    ITEM_PATTERNS, normalize_text, parse_prices, is_blocked_page, is_topic_page,
    extract_posters_with_prices, parse_topic_title, parse_topic_datetime
)


def trimmed_mean(values, trim_frac=0.2):
    """Compute mean after removing top and bottom trim_frac of values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n < 3:
        return statistics.mean(sorted_vals)
    trim_count = max(1, int(n * trim_frac))
    trimmed = sorted_vals[trim_count:n - trim_count]
    return statistics.mean(trimmed) if trimmed else statistics.mean(sorted_vals)


def trimmed_median(values, trim_frac=0.2):
    """Compute median after removing top and bottom trim_frac of values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n < 3:
        return statistics.median(sorted_vals)
    trim_count = max(1, int(n * trim_frac))
    trimmed = sorted_vals[trim_count:n - trim_count]
    return statistics.median(trimmed) if trimmed else statistics.median(sorted_vals)


def reprocess_offline(offline_dir, ladder_start, days):
    """Re-process saved HTML files with improved filtering."""
    offline_path = Path(offline_dir)
    html_files = sorted(list(offline_path.glob("*.html")) + list(offline_path.glob("*.htm")))
    
    if not html_files:
        return {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "mode": "offline-improved",
            "offline_dir": str(offline_path),
            "ladder_start_date": ladder_start.isoformat(),
            "days": days,
            "topics_scanned": 0,
            "estimates": {f"day_{d}": {} for d in range(1, days + 1)},
            "warning": "No HTML files found",
        }
    
    # Collect per-day per-item prices
    # Structure: {day_idx: {item_name: [price_values]}}
    buckets = {d: defaultdict(list) for d in range(1, days + 1)}
    # Also track per-user prices for dedup
    user_prices = {d: defaultdict(lambda: defaultdict(list)) for d in range(1, days + 1)}
    
    processed = 0
    skipped_blocked = 0
    skipped_no_topic = 0
    skipped_no_date = 0
    skipped_no_item = 0
    skipped_no_price = 0
    
    for html_file in html_files:
        try:
            html = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        if is_blocked_page(html):
            skipped_blocked += 1
            continue
        if not is_topic_page(html):
            skipped_no_topic += 1
            continue
        
        # Use file modification time as the collection date
        post_dt = dt.datetime.fromtimestamp(html_file.stat().st_mtime)
        day_idx = (post_dt.date() - ladder_start).days + 1
        if day_idx < 1 or day_idx > days:
            skipped_no_date += 1
            continue
        
        processed += 1
        
        text = normalize_text(html)
        title = parse_topic_title(html)
        
        # Detect items
        items_found = set()
        for name, patterns in ITEM_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    items_found.add(name)
                    break
            if name in items_found:
                break
        for name, patterns in ITEM_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, title, re.IGNORECASE):
                    items_found.add(name)
                    break
            if name in items_found:
                break
        
        if not items_found:
            # Try filename
            stem_item = None
            for name, patterns in ITEM_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, html_file.stem.replace("-", " "), re.IGNORECASE):
                        stem_item = name
                        break
                if stem_item:
                    break
            if stem_item:
                items_found.add(stem_item)
            else:
                skipped_no_item += 1
                continue
        
        # Extract per-user prices (more accurate than global text scan)
        user_blocks = extract_posters_with_prices(html, str(html_file))
        
        # Also try global price extraction as fallback
        global_prices = parse_prices(text)
        if not global_prices:
            global_prices = parse_prices(title)
        
        # Filter out spam prices (too low)
        min_valid_price = 5.0  # Filter out 1-3 FG spam
        
        for item in items_found:
            # Use per-user prices if available
            item_prices = []
            for ub in user_blocks:
                for p in ub["prices"]:
                    if p >= min_valid_price:
                        item_prices.append(p)
                        user_prices[day_idx][item][ub["user"]].append(p)
            
            # If no per-user prices, use global (filtered)
            if not item_prices:
                for p in global_prices:
                    if p >= min_valid_price:
                        item_prices.append(p)
            
            if item_prices:
                buckets[day_idx][item].extend(item_prices)
    
    # Build results with trimmed statistics
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "offline-improved",
        "offline_dir": str(offline_path),
        "ladder_start_date": ladder_start.isoformat(),
        "days": days,
        "topics_scanned": processed,
        "skipped": {
            "blocked": skipped_blocked,
            "no_topic": skipped_no_topic,
            "no_date": skipped_no_date,
            "no_item": skipped_no_item,
        },
        "filters": {
            "min_price_fg": min_valid_price,
            "trim_fraction": 0.2,
        },
        "estimates": {},
    }
    
    for day_idx in range(1, days + 1):
        day_key = f"day_{day_idx}"
        result["estimates"][day_key] = {}
        for item, prices in buckets[day_idx].items():
            if not prices:
                continue
            # Remove duplicates from same user (keep one per user)
            user_dedup = {}
            for user, uprices in user_prices[day_idx][item].items():
                if uprices:
                    user_dedup[user] = min(uprices)  # Take cheapest per user
            
            # Use user-deduped prices if available, otherwise all prices
            effective_prices = list(user_dedup.values()) if user_dedup else prices
            
            if len(effective_prices) < 2:
                continue
            
            result["estimates"][day_key][item] = {
                "median_fg": round(float(statistics.median(effective_prices)), 1),
                "avg_fg": round(float(statistics.mean(effective_prices)), 1),
                "trimmed_mean_fg": round(float(trimmed_mean(effective_prices, 0.2)), 1),
                "trimmed_median_fg": round(float(trimmed_median(effective_prices, 0.2)), 1),
                "min_fg": round(float(min(effective_prices)), 1),
                "max_fg": round(float(max(effective_prices)), 1),
                "samples": len(effective_prices),
                "raw_samples": len(prices),
            }
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Improve FG daily estimates with spam filtering")
    parser.add_argument("--ladder-start-date", default="2026-05-20", help="Ladder start date")
    parser.add_argument("--days", type=int, default=21, help="Number of days")
    parser.add_argument("--offline-dir", default="data/d2jsp_pages", help="Offline HTML dir")
    parser.add_argument("--out", default="config/fg_daily_estimates.json", help="Output file")
    args = parser.parse_args()
    
    ladder_start = dt.date.fromisoformat(args.ladder_start_date)
    data = reprocess_offline(args.offline_dir, ladder_start, args.days)
    
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote to {out_path} (topics_scanned={data['topics_scanned']})")
    
    # Show summary
    for dk in sorted(data["estimates"].keys()):
        items = data["estimates"][dk]
        if items:
            print(f"\n{dk}: {len(items)} items")
            for name in sorted(items.keys()):
                d = items[name]
                print(f"  {name:<30} med={d['median_fg']:>7} avg={d['avg_fg']:>7} trim_med={d['trimmed_median_fg']:>7} trim_avg={d['trimmed_mean_fg']:>7} min={d['min_fg']:>6} max={d['max_fg']:>7} n={d['samples']:>4}")


if __name__ == "__main__":
    main()
