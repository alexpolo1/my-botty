#!/usr/bin/env python
"""Scrape daily trade prices from traderie.com for D2R items and merge with FG prices.

Produces a combined daily price report with:
- Traderie barter prices (runes/charms as currency)
- FG prices from d2jsp forum estimates
- Unified daily price comparison

Usage:
    python tools/traderie_price_scraper.py                    # Scrape and save
    python tools/traderie_price_scraper.py --top 20           # Top 20 most expensive
    python tools/traderie_price_scraper.py --item Mara        # Filter by item name
    python tools/traderie_price_scraper.py --currency Jah     # Filter by currency
    python tools/traderie_price_scraper.py --trend            # Price history
    python tools/traderie_price_scraper.py --all              # Show all items

Output:
    config/traderie_prices.json      - Latest traderie scrape
    config/traderie_history.json     - Traderie history
    config/daily_prices.json         - Combined traderie + FG prices
    config/daily_prices_history.json - Combined history
"""
import argparse
import datetime as dt
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import requests

BASE_URL = "https://traderie.com/api/diablo2resurrected/listings"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-DK,en;q=0.9,da-DK;q=0.8",
}

# Rune value ladder (relative to El Rune = 1)
RUNE_VALUES = {
    "el rune": 1, "eld rune": 1, "tir rune": 1, "nef rune": 1,
    "eth rune": 1, "ith rune": 1,
    "tal rune": 2, "ral rune": 3, "ort rune": 4, "amn rune": 5,
    "sol rune": 6, "shael rune": 3, "dol rune": 3, "hel rune": 3,
    "io rune": 4, "ko rune": 4, "lum rune": 4,
    "fal rune": 7, "lem rune": 8, "pul rune": 9, "um rune": 10,
    "mal rune": 12, "ist rune": 15, "gul rune": 18, "vex rune": 22,
    "ohm rune": 25, "lo rune": 30, "cham rune": 35,
    "jah rune": 50, "ber rune": 60, "koh rune": 70,
}

CHARM_VALUES = {
    "small charm": 0.5,
    "medium charm": 1,
    "large charm": 2,
    "grand charm": 5,
}

CURRENCY_VALUES = {**RUNE_VALUES, **CHARM_VALUES}

# Map FG item names (from d2jsp) to traderie item names (from API)
FG_TO_TRADERIE = {
    # Runes (direct match)
    "Cham Rune": "Cham Rune",
    "Lo Rune": "Lo Rune",
    "Ohm Rune": "Ohm Rune",
    "Vex Rune": "Vex Rune",
    "Gul Rune": "Gul Rune",
    "Ist Rune": "Ist Rune",
    "Mal Rune": "Mal Rune",
    "Um Rune": "Um Rune",
    "Pul Rune": "Pul Rune",
    "Lem Rune": "Lem Rune",
    "Ber Rune": "Ber Rune",
    "Jah Rune": "Jah Rune",
    "Koh Rune": "Koh Rune",
    # Unique armor
    "Arach": "Arachnid Mesh",
    "Griffon": "Griffon's Eye",
    "Shako": "Harlequin Crest",
    "Highlord": "Highlord's Wrath",
    "Mara": "Mara's Kaleidoscope",
    "Death's Fathom": "Death's Fathom",
    "War Traveler": "War Traveler",
    # Unique rings
    "BK Ring": "Bul-Kathos' Wedding Band",
    # Unique charms
    "Unid Anni": "Annihilus",
    "Unid Torch": "Hellfire Torch",
    "Sorc Torch": "Hellfire Torch",
    "Pala Torch": "Hellfire Torch",
    # Runewords
    "CTA": "Call to Arms",
    "Stealth RW": "Stealth",
    "Dual Leech Ring": "Dual Leech Ring",
    "Aldur's Advance": "Aldur's Advance",
    "Viper Gorge": "Viper's Gorge",
    "Insight": "Insight",
    "Fury": "Fury",
    "Red Tape": "Red Tape",
    "Thresher": "Thresher",
    "Conviction": "Conviction",
    "Sanctuary": "Sanctuary",
    "Spirit": "Spirit",
    "Hope's Fall": "Hope's Fall",
    "Grief": "Grief",
    "Witching Hour": "Witching Hour",
    "Crow": "Crow",
    "Wind": "Wind",
    "Monarch": "Monarch",
    "Sacred": "Sacred Armor",
    "Guardian's Light": "Guardian's Light",
    "Oculus": "The Oculus",
    "Vampire Gaze": "Vampire Gaze",
    "Hellfire": "Hellfire Torch",
    "Torch of the Fanatic": "Torch of the Fanatic",
    "Light Jewel": "Light Jewel",
    "Omen": "Omen",
    "Enigma": "Enigma",
    "Ward": "Ward",
    "Crescent": "Crescent Moon",
    "Night": "Night",
    "Blessed": "Blessed Helm",
    "Fortitude": "Fortitude",
    "Herod": "Herod's Rancor",
    "Skin": "Skin of the Vipermagi",
    "Treachery": "Treachery",
    "Martyr": "Martyr",
    "Cyclone": "Cyclone",
    "Oath": "Oath",
    "Kurtz": "Kurtzile",
    "Moser": "Moser's",
    "Mithril": "Mithril",
    "Fist": "Fist of the Heavens",
    "Grave": "Grave's in Embrace",
    "Troll": "Troll",
    "Honor": "Honor",
    "Doom": "Doom",
    "Famine": "Famine",
    "Pestilence": "Pestilence",
    "Bulwark": "Bulwark",
    "Mjolnir": "Mjolnir",
    "Giant": "Giant's",
    "Manticore": "Manticore",
    "Spiketh": "Spiketh",
    "Bone": "Bone",
    "Black": "Black",
    "White": "White",
    # Skill tomes
    "Cold SK": "Cold SK",
    "Light SK": "Light SK",
    "Pcomb SK": "Paladin Combat SK",
    "Java SK": "Javelin SK",
    # Gems
    "5/5 Facet": "Rainbow Facet",
    # Keys
    "Key of Terror": "Key of Terror",
    "Key of Destruction": "Key of Destruction",
    "Key of Hate": "Key of Hate",
    "3x3 Key Set": "3x3 Key Set",
}


def scrape_listings(max_pages=20, delay=0.5):
    """Scrape all listings from traderie.com."""
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    all_listings = []
    page = 0
    while page < max_pages:
        params = {
            "selling": "true",
            "auction": "false",
            "page": str(page),
            "completed": "false",
            "active": "all",
        }
        try:
            r = session.get(BASE_URL, params=params, timeout=30)
            if r.status_code != 200:
                print(f"HTTP {r.status_code} on page {page}, stopping")
                break
            data = r.json()
        except Exception as e:
            print(f"Request error on page {page}: {e}")
            break
        listings = data.get("listings") or []
        if not listings:
            break
        all_listings.extend(listings)
        print(f"  Page {page}: {len(listings)} listings (total: {len(all_listings)})")
        if len(listings) < 50:
            break
        page += 1
        time.sleep(delay)
    return all_listings


def normalize_price_value(price_name, quantity):
    """Convert a price to normalized value."""
    name_lower = price_name.lower().strip()
    for rune_name, value in RUNE_VALUES.items():
        if rune_name in name_lower:
            return quantity * value, price_name
    for charm_name, value in CHARM_VALUES.items():
        if charm_name in name_lower:
            return quantity * value, price_name
    if "gold" in name_lower:
        return quantity * 0.001, price_name
    if "flare" in name_lower or "fg" in name_lower:
        return quantity * 100, price_name
    return quantity, price_name


def extract_prices(listing):
    """Extract all prices from a listing."""
    prices = listing.get("prices") or []
    result = []
    for price in prices:
        name = price.get("name", "")
        qty = price.get("quantity", 0)
        if not name or qty <= 0:
            continue
        norm_value = normalize_price_value(name, qty)
        result.append((norm_value[0], norm_value[1], qty))
    return result


def categorize_item(listing):
    """Categorize a listing into a friendly item name."""
    item = listing.get("item") or {}
    item_name = item.get("name", "")
    properties = listing.get("properties") or []
    for prop in properties:
        prop_str = str(prop.get("property", "")).lower()
        prop_string = str(prop.get("string", "")).lower()
        for rw in ["insight", "fury", "red tape", "thresher", "conviction",
                    "sanctuary", "spirit", "hope's fall", "grief", "witching hour",
                    "crow", "wind", "monarch", "sacred", "enigma", "ward",
                    "crescent", "night", "blessed", "fortitude", "herod",
                    "treachery", "martyr", "cyclone", "oath", "kurtz",
                    "moser", "mithril", "fist", "grave", "troll", "honor",
                    "doom", "famine", "pestilence", "bulwark", "mjolnir",
                    "giant", "manticore", "spiketh", "bone", "black", "white"]:
            if rw in prop_str or rw in prop_string:
                return rw.capitalize()
    return item_name


def analyze_prices(listings):
    """Analyze listings and compute statistics per item."""
    item_data = {}
    for listing in listings:
        prices = extract_prices(listing)
        if not prices:
            continue
        item_name = categorize_item(listing)
        if item_name not in item_data:
            item_data[item_name] = []
        for norm_value, currency, qty in prices:
            item_data[item_name].append({
                "normalized": norm_value,
                "currency": currency,
                "quantity": qty,
                "listing_id": listing.get("id"),
                "seller": listing.get("seller", {}).get("username", ""),
            })
    results = {}
    for item_name, entries in sorted(item_data.items()):
        by_currency = {}
        for entry in entries:
            curr = entry["currency"]
            if curr not in by_currency:
                by_currency[curr] = []
            by_currency[curr].append(entry["normalized"])
        stats = {
            "total_listings": len(set(e["listing_id"] for e in entries)),
            "currencies": {},
        }
        for curr, values in by_currency.items():
            stats["currencies"][curr] = {
                "count": len(values),
                "median": round(statistics.median(values), 1),
                "mean": round(statistics.mean(values), 1),
                "min": min(values),
                "max": max(values),
            }
        all_norm = [e["normalized"] for e in entries]
        stats["overall"] = {
            "median": round(statistics.median(all_norm), 1),
            "mean": round(statistics.mean(all_norm), 1),
            "count": len(all_norm),
        }
        results[item_name] = stats
    return results


def load_fg_estimates():
    """Load FG daily estimates from d2jsp scraper (improved version)."""
    config_dir = Path(__file__).parent.parent / "config"
    fg_file = config_dir / "fg_daily_estimates.json"
    if not fg_file.exists():
        return {}
    try:
        with open(fg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Get the latest day with data
        estimates = data.get("estimates", {})
        # Find the last day with actual data
        latest_day = None
        for day_key in sorted(estimates.keys(), reverse=True):
            if estimates[day_key]:
                latest_day = day_key
                break
        if latest_day:
            day_data = estimates[latest_day]
            # Normalize: use trimmed_median if available, else median
            result = {}
            for item, d in day_data.items():
                result[item] = {
                    "median_fg": d.get("trimmed_median_fg", d.get("median_fg", 0)),
                    "avg_fg": d.get("trimmed_mean_fg", d.get("avg_fg", 0)),
                    "min_fg": d.get("min_fg", 0),
                    "max_fg": d.get("max_fg", 0),
                    "samples": d.get("samples", d.get("raw_samples", 0)),
                }
            return result
        return {}
    except Exception:
        return {}


def merge_prices(traderie_results, fg_estimates):
    """Merge traderie barter prices with FG prices into a unified view."""
    merged = {}
    
    # Build reverse lookup: traderie item name -> FG item name
    traderie_to_fg = {v: k for k, v in FG_TO_TRADERIE.items()}
    
    # Add traderie data
    for item_name, stats in traderie_results.items():
        fg_name = traderie_to_fg.get(item_name)
        merged[item_name] = {
            "traderie": stats,
            "fg": None,
            "fg_name": fg_name,
        }
    
    # Add FG data
    for fg_item, fg_data in fg_estimates.items():
        traderie_name = FG_TO_TRADERIE.get(fg_item)
        if traderie_name and traderie_name in merged:
            # Merge into existing entry
            merged[traderie_name]["fg"] = fg_data
            merged[traderie_name]["fg_name"] = fg_item
        elif traderie_name:
            # New entry for FG-only items
            merged[traderie_name] = {
                "traderie": None,
                "fg": fg_data,
                "fg_name": fg_item,
            }
    
    return merged


def save_results(traderie_results, total_listings, fg_estimates):
    """Save results to JSON files."""
    config_dir = Path(__file__).parent.parent / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    
    # Save traderie data
    traderie_output = {
        "scraped_at": now.isoformat(),
        "scrape_date": now.strftime("%Y-%m-%d"),
        "total_listings_scanned": total_listings,
        "items_found": len(traderie_results),
        "prices": traderie_results,
    }
    latest_file = config_dir / "traderie_prices.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(traderie_output, f, indent=2, ensure_ascii=False)
    print(f"Saved traderie prices to {latest_file}")
    
    # Merge with FG
    merged = merge_prices(traderie_results, fg_estimates)
    
    # Save combined daily prices
    daily_output = {
        "generated_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "traderie_listings_scanned": total_listings,
        "traderie_items": len(traderie_results),
        "fg_items": len(fg_estimates),
        "merged_items": len(merged),
        "prices": merged,
    }
    daily_file = config_dir / "daily_prices.json"
    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(daily_output, f, indent=2, ensure_ascii=False)
    print(f"Saved combined daily prices to {daily_file}")
    
    # Append to history
    history_file = config_dir / "daily_prices_history.json"
    history = []
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    existing_dates = {entry.get("date") for entry in history}
    if now.strftime("%Y-%m-%d") not in existing_dates:
        history.append(daily_output)
        if len(history) > 90:
            history = history[-90:]
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"History: {len(history)} entries in {history_file}")
    
    return traderie_output, daily_output


def display_results(traderie_output, daily_output, args):
    """Display results."""
    merged = daily_output.get("prices", {})
    
    if args.item:
        filtered = {k: v for k, v in merged.items() if args.item.lower() in k.lower()}
        if not filtered:
            print(f"No items matching '{args.item}'")
            return
        print(f"\nItems matching '{args.item}':")
        print_merged_table(filtered)
        return
    
    if args.top:
        items_with_traderie = [(k, v) for k, v in merged.items() if v.get("traderie")]
        items_with_traderie.sort(key=lambda x: x[1]["traderie"]["overall"]["median"], reverse=True)
        top_items = dict(items_with_traderie[:args.top])
        print(f"\nTop {args.top} most expensive on traderie.com:")
        print_merged_table(top_items)
        return
    
    if args.currency:
        filtered = {}
        for item, data in merged.items():
            if data.get("traderie"):
                for curr in data["traderie"].get("currencies", {}):
                    if args.currency.lower() in curr.lower():
                        filtered[item] = data
                        break
        if filtered:
            print(f"\nItems priced with '{args.currency}':")
            print_merged_table(filtered)
        else:
            print(f"No items priced with '{args.currency}'")
        return
    
    if args.trend:
        history_file = Path(__file__).parent.parent / "config" / "daily_prices_history.json"
        if not history_file.exists():
            print("No history. Run a scrape first.")
            return
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        print(f"\nDaily price history ({len(history)} snapshots):")
        print(f"{'Date':<12} {'Traderie':>10} {'FG':>8} {'Merged':>8}")
        print("-" * 45)
        for entry in history:
            print(f"{entry['date']:<12} {entry['traderie_items']:>10} {entry['fg_items']:>8} {entry['merged_items']:>8}")
        return
    
    if args.all:
        print(f"\nAll items (scraped {daily_output['generated_at']}):")
        print(f"Traderie listings: {daily_output['traderie_listings_scanned']}, Items: {daily_output['merged_items']}")
        print()
        print_merged_table(merged)
        return
    
    # Default: show top 30
    items_with_traderie = [(k, v) for k, v in merged.items() if v.get("traderie")]
    items_with_traderie.sort(key=lambda x: x[1]["traderie"]["overall"]["median"], reverse=True)
    top_items = dict(items_with_traderie[:30])
    print(f"\nTop 30 items (scraped {daily_output['generated_at']}):")
    print(f"Traderie listings: {daily_output['traderie_listings_scanned']}, Merged items: {daily_output['merged_items']}")
    print()
    print_merged_table(top_items)
    if len(items_with_traderie) > 30:
        print(f"  ... and {len(items_with_traderie) - 30} more items (use --all to see all)")


def print_merged_table(merged):
    """Print a combined price table with traderie + FG prices."""
    print(f"{'Item':<35} {'Trade Price':>20} {'FG Price':>10} {'Currency(s)'}")
    print("-" * 90)
    for item, data in sorted(merged.items(), key=lambda x: (x[1].get("traderie") or {}).get("overall", {}).get("median", 0), reverse=True):
        # Show actual trade price as "1 Jah Rune" or "2 Jah + 1 Ber"
        trade_price = ""
        if data.get("traderie"):
            currencies = data["traderie"].get("currencies", {})
            parts = []
            for curr, info in sorted(currencies.items(), key=lambda x: x[1]["count"], reverse=True):
                qty = round(info["count"])
                parts.append(f"{qty} {curr}")
            trade_price = " + ".join(parts[:3])
            if len(parts) > 3:
                trade_price += f" +{len(parts)-3}"
        fg_med = (data.get("fg") or {}).get("median_fg", "-") if data.get("fg") else "-"
        # Show currency breakdown
        currencies_str = ""
        if data.get("traderie"):
            currencies_str = ", ".join(f"{k}({v['count']})" for k, v in data["traderie"].get("currencies", {}).items())
        print(f"{item:<35} {trade_price:>20} {fg_med:>10} {currencies_str}")


def show_currency_summary(traderie_output):
    """Show currency distribution."""
    prices = traderie_output.get("prices", {})
    currency_counts = Counter()
    for item, stats in prices.items():
        for curr, info in stats.get("currencies", {}).items():
            currency_counts[curr] += info["count"]
    print("\nCurrency distribution:")
    print(f"{'Currency':<25} {'Listings':>10}")
    print("-" * 40)
    for curr, count in currency_counts.most_common():
        print(f"{curr:<25} {count:>10}")


def main():
    parser = argparse.ArgumentParser(description="Scrape D2R trade prices from traderie.com + FG prices")
    parser.add_argument("--top", type=int, default=None, help="Show top N most expensive items")
    parser.add_argument("--item", type=str, default=None, help="Filter by item name")
    parser.add_argument("--currency", type=str, default=None, help="Filter by currency type")
    parser.add_argument("--trend", action="store_true", help="Show price history")
    parser.add_argument("--all", action="store_true", help="Show all items")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to scrape (default 10)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (default 0.5s)")
    args = parser.parse_args()
    
    # If just querying, load existing data
    if any([args.top, args.item, args.currency, args.trend, args.all]):
        daily_file = Path(__file__).parent.parent / "config" / "daily_prices.json"
        if not daily_file.exists():
            print("No price data found. Run a scrape first: python tools/traderie_price_scraper.py")
            sys.exit(1)
        with open(daily_file, "r", encoding="utf-8") as f:
            daily_output = json.load(f)
        traderie_file = Path(__file__).parent.parent / "config" / "traderie_prices.json"
        if traderie_file.exists():
            with open(traderie_file, "r", encoding="utf-8") as f:
                traderie_output = json.load(f)
        else:
            traderie_output = {}
        display_results(traderie_output, daily_output, args)
        show_currency_summary(traderie_output)
        return
    
    # Scrape mode
    print("Scraping traderie.com listings...")
    listings = scrape_listings(args.max_pages, args.delay)
    print(f"\nTotal listings: {len(listings)}")
    if not listings:
        print("No listings found.")
        sys.exit(1)
    
    results = analyze_prices(listings)
    fg_estimates = load_fg_estimates()
    print(f"Loaded FG estimates: {len(fg_estimates)} items")
    
    traderie_output, daily_output = save_results(results, len(listings), fg_estimates)
    
    display_results(traderie_output, daily_output, args)
    show_currency_summary(traderie_output)


if __name__ == "__main__":
    main()
