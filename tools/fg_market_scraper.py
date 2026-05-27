import argparse
import datetime as dt
import json
import re
import statistics
import time
from html import unescape
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import requests


BASE_URL = "https://forums.d2jsp.org"
FORUM_PATH = "/forum.php?f=271"


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-DK,en;q=0.9,da-DK;q=0.8,da;q=0.7,en-GB;q=0.6,en-US;q=0.5",
    "Referer": "https://www.google.com/",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "cross-site",
    "sec-fetch-user": "?1",
}


def make_session(cookie_path: str = "") -> requests.Session:
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    if cookie_path and Path(cookie_path).exists():
        cookiejar = MozillaCookieJar(cookie_path)
        cookiejar.load(ignore_discard=True, ignore_expires=True)
        session.cookies = cookiejar
    return session


ITEM_PATTERNS = {
    "Cham Rune": [r"\bcham\b"],
    "Lo Rune": [r"\blo\b"],
    "Ohm Rune": [r"\bohm\b"],
    "Vex Rune": [r"\bvex\b"],
    "Gul Rune": [r"\bgul\b"],
    "Ist Rune": [r"\bist\b"],
    "Mal Rune": [r"\bmal\b"],
    "Um Rune": [r"\bum\b"],
    "Pul Rune": [r"\bpul\b"],
    "Lem Rune": [r"\blem\b"],
    "Ber Rune": [r"\bber\b"],
    "Jah Rune": [r"\bjah\b"],
    "Koh Rune": [r"\bkoh\b"],
    "Unid Anni": [r"\bunid\s+anni\b", r"\bunid\s+annihilus\b"],
    "Unid Torch": [r"\bunid\s+(diab?olos|mephistos|baalos|torch)\b", r"\bunid\s+torch\b"],
    "Sorc Torch": [r"\bsorc\s+torch\b", r"\bsorc\s+torc?h\b"],
    "Pala Torch": [r"\bpala\s+torch\b"],
    "Griffon": [r"\bgriffon"],
    "Shako": [r"\bshako\b", r"\bharlequin crest\b"],
    "Mara": [r"\bmara\b"],
    "Highlord": [r"\bhighlord\b"],
    "BK Ring": [r"\bbk\b", r"\bbul[\s\-']*kathos"],
    "War Traveler": [r"\bwar traveler\b"],
    "Death's Fathom": [r"\bdeath'?s fathom\b"],
    "Arach": [r"\barach", r"\barachnid mesh\b"],
    "5/5 Facet": [r"\b5\s*/\s*5\b.*\bfacet\b"],
    "Pcomb SK": [r"\bpcomb\b", r"\bpaladin combat\b"],
    "Cold SK": [r"\bcold sk\b", r"\bcold skills\b"],
    "Java SK": [r"\bjava sk\b", r"\bjavelin\b"],
    "Light SK": [r"\blight sk\b", r"\blightning skills\b"],
    "CTA": [r"\bcta\b", r"\bcall to arms\b"],
    "Stealth RW": [r"\bstealth\b"],
    "Dual Leech Ring": [r"\bdual leech ring\b"],
    "Aldur's Advance": [r"\baldur'?s advance\b"],
    "Viper Gorge": [r"\bviper\b"],
    "Insight": [r"\binsight\b"],
    "Fury": [r"\bfury\b"],
    "Red Tape": [r"\bred tape\b"],
    "Thresher": [r"\bthresher\b"],
    "Conviction": [r"\bconviction\b"],
    "Sanctuary": [r"\bsanctuary\b"],
    "Spirit": [r"\bspirit\b"],
    "Hope's Fall": [r"\bhope'?s fall\b"],
    "Grief": [r"\bgrief\b"],
    "Witching Hour": [r"\bwitching\b"],
    "Crow": [r"\bcrow\b"],
    "Wind": [r"\bwind\b"],
    "Monarch": [r"\bmonarch\b"],
    "Sacred": [r"\bsacred\b"],
    "Guardian's Light": [r"\bguardian\b", r"\blight jewel\b"],
    "Oculus": [r"\boculus\b"],
    "Vampire Gaze": [r"\bvampire gaze\b", r"\bvamp\b"],
    "Hellfire": [r"\bhellfire\b"],
    "Torch of the Fanatic": [r"\btof\b", r"\btorch of the fanatic\b"],
    "Light Jewel": [r"\blight jewel\b"],
    "Omen": [r"\bomen\b"],
    "Enigma": [r"\benigma\b"],
    "Ward": [r"\bward\b"],
    "Crescent": [r"\bcrescent\b"],
    "Night": [r"\bnight\b"],
    "Blessed": [r"\bblessed\b"],
    "Fortitude": [r"\bfortitude\b"],
    "Herod": [r"\bherod\b"],
    "Skin": [r"\bskin\b"],
    "Treachery": [r"\btreachery\b"],
    "Martyr": [r"\bmartyr\b"],
    "Cyclone": [r"\bcyclone\b"],
    "Oath": [r"\boath\b"],
    "Kurtz": [r"\bkurtz\b"],
    "Moser": [r"\bmoser\b"],
    "Mithril": [r"\bmithril\b"],
    "Fist": [r"\bfist\b"],
    "Grave": [r"\bgrave\b"],
    "Troll": [r"\btroll\b"],
    "Honor": [r"\bhonor\b"],
    "Doom": [r"\bdoom\b"],
    "Famine": [r"\bfamine\b"],
    "Pestilence": [r"\bpestilence\b"],
    "Bulwark": [r"\bbulwark\b"],
    "Mjolnir": [r"\bmjolnir\b"],
    "Giant": [r"\bgiant\b"],
    "Manticore": [r"\bmanticore\b"],
    "Spiketh": [r"\bspiketh\b"],
    "Bone": [r"\bbone\b"],
    "Black": [r"\bblack\b"],
    "White": [r"\bwhite\b"],
}


def normalize_text(html_text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_prices(text: str) -> list[float]:
    values: list[float] = []
    for m in re.finditer(r"\b(?:bin\s*)?(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?\s*fg\b", text, flags=re.IGNORECASE):
        raw = m.group(1).replace(",", "")
        try:
            values.append(float(raw))
        except ValueError:
            continue
    return values


def extract_posters_with_prices(topic_html: str) -> list[dict]:
    """Extract username + price pairs from a d2jsp topic page.
    Returns list of {'user': str, 'prices': [float]}.
    d2jsp structure: username appears in a link, followed by 'Member', 'Posts:', then the post body with prices.
    """
    # Remove script/style tags
    clean = re.sub(r"<script.*?</script>", " ", topic_html, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r"<style.*?</style>", " ", clean, flags=re.IGNORECASE | re.DOTALL)

    # Find all username blocks: <a href="/member.php?m=...">username</a> ... Member ... Posts: ...
    # Then capture everything until the next username block as the post content
    user_blocks = []
    # Pattern: member link with username, then the post content until next member link
    parts = re.split(r'(<a\s+href="/member\.php\?m=\d+"[^>]*>([^<]*)</a>)', clean)

    i = 1
    while i < len(parts) - 1:
        # parts[i] = full match, parts[i+1] = href attr, parts[i+2] = username, parts[i+3] = post body
        username = parts[i + 2].strip()
        if i + 3 < len(parts):
            post_body = parts[i + 3]
            # Extract prices from this post's body
            post_text = re.sub(r"<[^>]+>", " ", post_body)
            post_text = unescape(post_text)
            prices = parse_prices(post_text)
            if prices:
                user_blocks.append({"user": username, "prices": prices})
        i += 4

    return user_blocks


def detect_item(text: str) -> str | None:
    lower = text.lower()
    for name, patterns in ITEM_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower, flags=re.IGNORECASE):
                return name
    return None


def is_blocked_page(html_text: str) -> bool:
    lower = (html_text or "").lower()
    return ("just a moment" in lower and "cloudflare" in lower) or "challenge-platform" in lower


def is_topic_page(html_text: str) -> bool:
    lower = (html_text or "").lower()
    if "saved from url=" in lower and "topic.php?t=" in lower:
        return True
    if "<title>" in lower and "- topic - d2jsp" in lower:
        return True
    return False


def parse_forum_topic_links(html_text: str) -> list[str]:
    # d2jsp uses relative paths: href="topic.php?t=123&f=271"
    # also handle absolute paths: href="/topic.php?t=123"
    # Use non-capturing group to avoid findall returning only the group
    links = re.findall(r'href="((?:/)?topic\.php\?t=\d+[^"]*)"', html_text)
    unique = []
    seen = set()
    for link in links:
        # Normalize: strip leading slash, remove &v=1 (view-only variant)
        norm = link.lstrip("/")
        norm = re.sub(r'&v=\d+', '', norm)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return unique


def parse_topic_datetime(topic_html: str) -> dt.datetime | None:
    # Typical d2jsp pages contain explicit date strings in post headers.
    # Support both "Jan 01 2026" and "26 May 2026"
    candidates = re.findall(
        r"\b(?:\d{1,2}\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}(?:\s+\d{1,2}:\d{2})?|"
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}(?:\s+\d{1,2}:\d{2})?",
        topic_html,
        flags=re.IGNORECASE,
    )
    formats = (
        "%b %d %Y, %I:%M %p", "%B %d %Y, %I:%M %p", "%b %d %Y", "%B %d %Y",
        "%d %b %Y %H:%M", "%d %B %Y %H:%M", "%d %b %Y", "%d %B %Y",
        "%b %d %Y %H:%M", "%B %d %Y %H:%M"
    )
    for token in candidates:
        for fmt in formats:
            try:
                return dt.datetime.strptime(token, fmt)
            except ValueError:
                pass
    return None


def parse_topic_title(topic_html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", topic_html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    return normalize_text(m.group(1))


def fallback_item_from_title(title: str) -> str | None:
    cleaned = (title or "").replace(" - Topic - d2jsp", "").strip()
    if not cleaned:
        return None
    # Avoid overly generic buckets.
    if cleaned.lower() in {"d2:r rotw softcore ladder trading - d2jsp", "d2:r rotw softcore ladder trading"}:
        return None
    return f"Topic:{cleaned[:80]}"


def scrape_day_estimates(
    ladder_start: dt.date,
    days: int,
    max_forum_pages: int,
    max_topics: int,
    delay_s: float,
    cookie_path: str = "",
) -> dict:
    session = make_session(cookie_path)

    # Warm up: hit root first to establish Cloudflare session
    try:
        session.get(f"{BASE_URL}/", timeout=20)
    except Exception:
        pass

    topic_urls: list[str] = []
    for page_idx in range(max_forum_pages):
        offset = page_idx * 25
        url = f"{BASE_URL}{FORUM_PATH}&st={offset}"
        r = session.get(url, timeout=20)
        if r.status_code == 403:
            raise RuntimeError(
                "d2jsp returned HTTP 403 Forbidden. "
                "Scraping is blocked from this environment/IP. "
                "Run this tool from a browser-authenticated environment or provide exported topic data."
            )
        if is_blocked_page(r.text):
            raise RuntimeError(
                "d2jsp returned a Cloudflare challenge page. "
                "Your cookies may be stale — export fresh cookies from your browser and rerun."
            )
        r.raise_for_status()
        links = parse_forum_topic_links(r.text)
        for link in links:
            if not link.startswith("/"):
                link = "/" + link
            full = f"{BASE_URL}{link}"
            if full not in topic_urls:
                topic_urls.append(full)
        time.sleep(delay_s)
        if len(topic_urls) >= max_topics:
            break

    topic_urls = topic_urls[:max_topics]
    buckets: dict[int, dict[str, list[float]]] = {d: {} for d in range(1, days + 1)}
    user_cheapest: dict[str, dict] = {}
    processed = 0

    for topic_url in topic_urls:
        try:
            r = session.get(topic_url, timeout=20)
            r.raise_for_status()
        except Exception:
            continue
        html = r.text
        if is_blocked_page(html):
            continue

        # Paginate through all pages of this topic
        all_text = html
        all_html = html
        prev_text = normalize_text(html)
        topic_id_match = re.search(r't=(\d+)', topic_url)
        topic_id = topic_id_match.group(1) if topic_id_match else None
        if topic_id:
            # Fetch subsequent pages (o=25, o=50, etc.)
            for page_offset in range(25, 200, 25):
                next_url = f"{BASE_URL}/topic.php?t={topic_id}&f=271&o={page_offset}"
                try:
                    r2 = session.get(next_url, timeout=20)
                    if r2.status_code != 200:
                        break
                    page_text = normalize_text(r2.text)
                    # Stop if we hit the last page (same content as previous page)
                    if page_text == prev_text:
                        break
                    prev_text = page_text
                    all_text += " " + page_text
                    all_html += " " + r2.text
                    time.sleep(delay_s)
                except Exception:
                    break

        text = normalize_text(all_text)
        title = parse_topic_title(all_html)
        post_dt = parse_topic_datetime(all_html)
        processed += 1
        time.sleep(delay_s)

        if not post_dt:
            continue

        day_idx = (post_dt.date() - ladder_start).days + 1
        if day_idx < 1 or day_idx > days:
            continue

        # Detect ALL items in this topic (multi-item topics are common)
        items_found = set()
        # Check body text
        for name, patterns in ITEM_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    items_found.add(name)
                    break
        # Check title
        for name, patterns in ITEM_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, title, re.IGNORECASE):
                    items_found.add(name)
                    break
        # Check filename stem for generic titles
        if not items_found:
            # Try to detect from title keywords (only specific, non-generic terms)
            title_lower = title.lower()
            for kw, item_name in [
                ('sorc torch', 'Sorc Torch'),
                ('pala torch', 'Unid Torch'), ('torch', 'Unid Torch'),
                ('annihilus', 'Unid Anni'), ('anni', 'Unid Anni'),
                ('shako', 'Shako'), ('griffon', 'Griffon'), ('arach', 'Arach'),
                ('mara', 'Mara'), ('highlord', 'Highlord'),
                ('war traveler', 'War Traveler'),
                ('cta', 'CTA'), ('call to arms', 'CTA'),
                ('stealth', 'Stealth RW'), ('leech ring', 'Dual Leech Ring'),
                ('aldur', "Aldur's Advance"), ('facet', '5/5 Facet'),
                ('pcomb', 'Pcomb SK'), ('cold sk', 'Cold SK'),
                ('java', 'Java SK'), ('light sk', 'Light SK'),
                ('viper', 'Viper Gorge'), ('insight', 'Insight'),
                ('fury', 'Fury'), ('red tape', 'Red Tape'),
                ('thresher', 'Thresher'), ('conviction', 'Conviction'),
                ('sanctuary', 'Sanctuary'), ('spirit', 'Spirit'),
                ("hope's fall", "Hope's Fall"), ('hopes fall', "Hope's Fall"),
                ('grief', 'Grief'), ('witching', 'Witching Hour'),
                ('crow', 'Crow'), ('wind', 'Wind'),
                ('monarch', 'Monarch'), ('sacred', 'Sacred'),
                ('guardian', "Guardian's Light"), ('light jewel', 'Light Jewel'),
                ('oculus', 'Oculus'), ('vampire', 'Vampire Gaze'),
                ('hellfire', 'Hellfire'), ('tof', 'Torch of the Fanatic'),
                ('omen', 'Omen'), ('enigma', 'Enigma'),
                ('ward', 'Ward'), ('crescent', 'Crescent'),
                ('night', 'Night'), ('blessed', 'Blessed'),
                ('fortitude', 'Fortitude'), ('herod', 'Herod'),
                ('treachery', 'Treachery'), ('martyr', 'Martyr'),
                ('cyclone', 'Cyclone'), ('oath', 'Oath'),
                ('kurtz', 'Kurtz'), ('moser', 'Moser'),
                ('mithril', 'Mithril'), ('fist', 'Fist'),
                ('grave', 'Grave'), ('troll', 'Troll'),
                ('honor', 'Honor'), ('doom', 'Doom'),
                ('famine', 'Famine'), ('pestilence', 'Pestilence'),
                ('bulwark', 'Bulwark'), ('mjolnir', 'Mjolnir'),
                ('giant', 'Giant'), ('manticore', 'Manticore'),
                ('spiketh', 'Spiketh'), ('bone', 'Bone'),
                ('black', 'Black'), ('white', 'White'),
            ]:
                if kw in title_lower:
                    items_found.add(item_name)
                    break

        # Parse all FG prices and extract per-user data
        prices = parse_prices(text)
        user_prices = extract_posters_with_prices(all_html)

        if not items_found or not prices:
            continue

        # Distribute prices across all detected items
        for item in items_found:
            if item not in buckets[day_idx]:
                buckets[day_idx][item] = []
            # Keep first few prices per item per topic
            buckets[day_idx][item].extend(prices[:3])

            # Also track per-user cheapest prices
            for up in user_prices:
                for p in up["prices"][:3]:
                    user_key = f"{item}__{up['user']}"
                    if user_key not in user_cheapest:
                        user_cheapest[user_key] = {"item": item, "user": up["user"], "price": p}
                    elif p < user_cheapest[user_key]["price"]:
                        user_cheapest[user_key]["price"] = p

    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ladder_start_date": ladder_start.isoformat(),
        "days": days,
        "topics_scanned": processed,
        "estimates": {},
        "sellers": [],
    }

    for day_idx in range(1, days + 1):
        day_key = f"day_{day_idx}"
        result["estimates"][day_key] = {}
        for item, samples in buckets[day_idx].items():
            if not samples:
                continue
            median_fg = statistics.median(samples)
            result["estimates"][day_key][item] = {
                "median_fg": round(float(median_fg), 1),
                "samples": len(samples),
            }

    # Deduplicate sellers: keep cheapest per (item, user)
    seller_list = list(user_cheapest.values())
    seller_list.sort(key=lambda s: s["price"])
    result["sellers"] = seller_list
    return result


def scrape_day_estimates_offline(
    offline_dir: str,
    ladder_start: dt.date,
    days: int,
) -> dict:
    offline_path = Path(offline_dir)
    if not offline_path.exists() or not offline_path.is_dir():
        raise RuntimeError(f"Offline dir does not exist or is not a directory: {offline_dir}")

    html_files = sorted(list(offline_path.glob("*.html")) + list(offline_path.glob("*.htm")))
    if not html_files:
        return {
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "mode": "offline",
            "offline_dir": str(offline_path),
            "ladder_start_date": ladder_start.isoformat(),
            "days": days,
            "topics_scanned": 0,
            "warning": "No .html/.htm files found in offline dir. Save forum/topic pages into this folder and rerun.",
            "estimates": {f"day_{d}": {} for d in range(1, days + 1)},
        }

    buckets: dict[int, dict[str, list[float]]] = {d: {} for d in range(1, days + 1)}
    processed = 0

    for html_file in html_files:
        try:
            html = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if is_blocked_page(html):
            continue
        if not is_topic_page(html):
            continue
        text = normalize_text(html)
        title = parse_topic_title(html)
        item = (
            detect_item(text)
            or detect_item(title)
            or detect_item(html_file.stem.replace("-", " "))
            or fallback_item_from_title(title)
        )
        prices = parse_prices(text)
        if not prices:
            prices = parse_prices(title)
        # Offline mode uses file save timestamp as authoritative collection time.
        # Page content may contain many unrelated historical dates that pollute parsing.
        post_dt = dt.datetime.fromtimestamp(html_file.stat().st_mtime)
        processed += 1

        if not item or not prices or not post_dt:
            continue

        day_idx = (post_dt.date() - ladder_start).days + 1
        if day_idx < 1 or day_idx > days:
            continue

        if item not in buckets[day_idx]:
            buckets[day_idx][item] = []
        buckets[day_idx][item].extend(prices[:3])

    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "offline",
        "offline_dir": str(offline_path),
        "ladder_start_date": ladder_start.isoformat(),
        "days": days,
        "topics_scanned": processed,
        "estimates": {},
    }

    for day_idx in range(1, days + 1):
        day_key = f"day_{day_idx}"
        result["estimates"][day_key] = {}
        for item, samples in buckets[day_idx].items():
            if not samples:
                continue
            median_fg = statistics.median(samples)
            result["estimates"][day_key][item] = {
                "median_fg": round(float(median_fg), 1),
                "samples": len(samples),
            }
    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape d2jsp ladder forum and estimate day-by-day FG prices.")
    parser.add_argument("--ladder-start-date", required=True, help="Ladder start date in YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=14, help="Number of ladder days to aggregate (default: 14)")
    parser.add_argument("--max-forum-pages", type=int, default=40, help="How many forum pages to scan (25 topics/page)")
    parser.add_argument("--max-topics", type=int, default=800, help="Hard cap for topic pages to fetch")
    parser.add_argument("--delay-s", type=float, default=0.35, help="Delay between requests (seconds)")
    parser.add_argument("--offline-dir", default="", help="Parse local saved .html files instead of live scraping")
    parser.add_argument("--cookie-path", default="cookies.txt", help="Path to Netscape cookie jar file (default: cookies.txt)")
    parser.add_argument("--out", default="config/fg_daily_estimates.json", help="Output JSON path")
    args = parser.parse_args()

    ladder_start = dt.date.fromisoformat(args.ladder_start_date)
    if args.offline_dir:
        data = scrape_day_estimates_offline(
            offline_dir=args.offline_dir,
            ladder_start=ladder_start,
            days=args.days,
        )
    else:
        data = scrape_day_estimates(
            ladder_start=ladder_start,
            days=args.days,
            max_forum_pages=args.max_forum_pages,
            max_topics=args.max_topics,
            delay_s=args.delay_s,
            cookie_path=args.cookie_path,
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote FG daily estimates to {out_path} (topics_scanned={data['topics_scanned']})")
    if "warning" in data:
        print(f"WARNING: {data['warning']}")


if __name__ == "__main__":
    main()
