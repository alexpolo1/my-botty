"""
Playwright-based headless scraper for d2jsp FG market forum.
Saves HTML files to data/d2jsp_pages/ for the offline scraper to process.
"""
import argparse
import http.cookiejar
import os
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "https://forums.d2jsp.org"
FORUM_PATH = "/forum.php?f=271"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept-Language": "en-DK,en;q=0.9,da-DK;q=0.8,da;q=0.7,en-GB;q=0.6,en-US;q=0.5",
}


def sanitize_filename(name: str) -> str:
    """Make a safe filename from a topic title."""
    bad = '<>:"/\\|?*'
    for c in bad:
        name = name.replace(c, "_")
    return name[:120]


def main():
    parser = argparse.ArgumentParser(description="Scrape d2jsp FG market forum and save HTML files.")
    parser.add_argument("--max-forum-pages", type=int, default=40, help="Forum pages to scan (25 topics/page)")
    parser.add_argument("--max-topics", type=int, default=800, help="Max topic pages to save")
    parser.add_argument("--delay-s", type=float, default=0.5, help="Delay between requests")
    parser.add_argument("--out-dir", default="data/d2jsp_pages", help="Output directory for HTML files")
    parser.add_argument("--cookie-path", default="cookies.txt", help="Path to Netscape cookie jar")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=BROWSER_HEADERS["User-Agent"],
            viewport={"width": 1920, "height": 1080},
            locale="en-DK",
        )

        # Load cookies if available
        if Path(args.cookie_path).exists():
            cj = http.cookiejar.MozillaCookieJar(args.cookie_path)
            cj.load(ignore_discard=True, ignore_expires=True)
            for cookie in cj:
                context.add_cookies([{
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                }])

        page = context.new_page()

        # Warm up
        try:
            page.goto(f"{BASE_URL}/", timeout=20000, wait_until="domcontentloaded")
        except Exception:
            pass

        topic_urls = []
        for page_idx in range(args.max_forum_pages):
            offset = page_idx * 25
            url = f"{BASE_URL}{FORUM_PATH}&st={offset}"
            try:
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
            except Exception:
                print(f"Failed to load forum page {page_idx}, stopping.")
                break

            # Check for 403 / Cloudflare
            content = page.content()
            if "Access denied" in content or "Just a moment" in content:
                print("Cloudflare/403 detected, stopping forum scan.")
                break

            # Extract topic links using same regex as fg_market_scraper.py
            links = re.findall(r'href=\"((?:/)?topic\.php\?t=\d+[^\"]*)\"', content)
            seen = set()
            for link in links:
                # Normalize: strip leading slash, remove &v=1
                norm = link.lstrip("/")
                norm = re.sub(r'&v=\d+', '', norm)
                if norm not in seen:
                    seen.add(norm)
                    full = f"{BASE_URL}/{norm}"
                    if full not in topic_urls:
                        topic_urls.append(full)

            time.sleep(args.delay_s)
            if len(topic_urls) >= args.max_topics:
                break

        print(f"Found {len(topic_urls)} topic URLs. Saving HTML files...")

        saved = 0
        skipped = 0
        for i, topic_url in enumerate(topic_urls):
            try:
                page.goto(topic_url, timeout=20000, wait_until="domcontentloaded")
                html = page.content()

                # Check for Cloudflare challenge
                if "Just a moment" in html or "Access denied" in html:
                    print(f"  [{i+1}/{len(topic_urls)}] Cloudflare blocked {topic_url}")
                    skipped += 1
                    continue

                # Get the topic title for filename
                title_el = page.query_selector("h1")
                title = title_el.inner_text().strip() if title_el else f"topic_{i}"
                filename = f"[offering] {title} - Topic - d2jsp.html"
                filename = sanitize_filename(filename)

                filepath = out_dir / filename
                filepath.write_text(html, encoding="utf-8")
                saved += 1
                print(f"  [{i+1}/{len(topic_urls)}] Saved: {filename}")

            except Exception as e:
                print(f"  [{i+1}/{len(topic_urls)}] Error saving {topic_url}: {e}")
                skipped += 1

            time.sleep(args.delay_s)

        browser.close()

    print(f"\nDone! Saved {saved} topics, skipped {skipped}.")
    print(f"Files in {out_dir}")
    print("Now run: python tools/fg_market_scraper.py --ladder-start-date YYYY-MM-DD --days 14 --offline-dir data/d2jsp_pages")


if __name__ == "__main__":
    main()
