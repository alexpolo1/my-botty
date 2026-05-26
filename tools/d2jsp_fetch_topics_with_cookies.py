import argparse
import re
import time
from pathlib import Path
from http.cookiejar import MozillaCookieJar

import requests


def topic_id_from_url(url: str) -> str:
    m = re.search(r"[?&]t=(\d+)", url)
    return m.group(1) if m else "unknown"


def load_urls(url_file: Path, limit: int) -> list[str]:
    urls = []
    for line in url_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    if limit > 0:
        urls = urls[:limit]
    return urls


def main():
    parser = argparse.ArgumentParser(description="Fetch d2jsp topic pages using exported cookies.txt")
    parser.add_argument("--cookies-file", required=True, help="Path to Netscape cookies.txt export")
    parser.add_argument("--url-file", default="data/d2jsp_topic_urls.txt", help="Text file with topic URLs")
    parser.add_argument("--out-dir", default="data/d2jsp_pages", help="Output directory for saved HTML pages")
    parser.add_argument("--limit", type=int, default=0, help="Max number of topic URLs to fetch (0=all)")
    parser.add_argument("--delay-s", type=float, default=0.6, help="Delay between requests")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing topic HTML files")
    args = parser.parse_args()

    cookies_path = Path(args.cookies_file)
    if not cookies_path.exists():
        raise RuntimeError(f"cookies-file not found: {cookies_path}")

    url_path = Path(args.url_file)
    if not url_path.exists():
        raise RuntimeError(f"url-file not found: {url_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    urls = load_urls(url_path, args.limit)
    if not urls:
        raise RuntimeError("No URLs found in url-file")

    cookiejar = MozillaCookieJar()
    cookiejar.load(str(cookies_path), ignore_discard=True, ignore_expires=True)

    session = requests.Session()
    session.cookies = cookiejar
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-DK,en;q=0.9,da-DK;q=0.8,da;q=0.7,en-GB;q=0.6,en-US;q=0.5",
            "Referer": "https://forums.d2jsp.org/forum.php?f=271",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        }
    )

    ok = 0
    failed = 0
    for idx, url in enumerate(urls, start=1):
        topic_id = topic_id_from_url(url)
        out_file = out_dir / f"topic_{topic_id}.html"
        if out_file.exists() and not args.overwrite:
            print(f"[{idx}/{len(urls)}] skip existing {out_file.name}")
            continue
        try:
            r = session.get(url, timeout=25)
            status = r.status_code
            if status == 200 and len(r.text) > 2000:
                out_file.write_text(r.text, encoding="utf-8", errors="ignore")
                ok += 1
                print(f"[{idx}/{len(urls)}] OK {topic_id} ({len(r.text)} bytes)")
            else:
                failed += 1
                print(f"[{idx}/{len(urls)}] FAIL {topic_id} status={status} len={len(r.text)}")
                if status == 403:
                    debug_file = out_dir / f"debug_403_{topic_id}.html"
                    debug_file.write_text(r.text, encoding="utf-8", errors="ignore")
                    print(f"      Cloudflare block detected. Saved response to {debug_file}")
                    if "Just a moment..." in r.text:
                        print("      INFO: This is a Cloudflare 'Just a moment' challenge.")
                        print("      To fix: You must find the 'cf_clearance' cookie in your browser's Network tab and add it.")
        except Exception as e:
            failed += 1
            print(f"[{idx}/{len(urls)}] ERROR {topic_id}: {e}")
        time.sleep(args.delay_s)

    print(f"Done. saved={ok}, failed={failed}, out_dir={out_dir}")


if __name__ == "__main__":
    main()
