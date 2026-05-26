import argparse
import re
import time
import webbrowser
from html import unescape
from pathlib import Path


BASE_URL = "https://forums.d2jsp.org"


def parse_topic_links(html: str) -> list[str]:
    matches = []
    matches.extend(re.findall(r'href="(/topic\.php\?t=\d+[^"]*)"', html))
    matches.extend(re.findall(r'href="(https?://forums\.d2jsp\.org/topic\.php\?t=\d+[^"]*)"', html))
    out = []
    seen = set()
    for m in matches:
        href = unescape(m)
        url = href if href.startswith("http") else f"{BASE_URL}{href}"
        # Canonicalize by topic id to avoid duplicate entries like &v=1.
        topic_id_match = re.search(r"[?&]t=(\d+)", url)
        topic_id = topic_id_match.group(1) if topic_id_match else url
        canonical = f"{BASE_URL}/topic.php?t={topic_id}&f=271"
        if canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return out


def collect_from_dir(offline_dir: Path) -> list[str]:
    files = sorted(list(offline_dir.glob("*.html")) + list(offline_dir.glob("*.htm")))
    urls = []
    seen = set()
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for url in parse_topic_links(text):
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def main():
    parser = argparse.ArgumentParser(description="Extract d2jsp topic URLs from saved forum listing HTML.")
    parser.add_argument("--offline-dir", default="data/d2jsp_pages", help="Directory containing saved listing HTML")
    parser.add_argument("--out", default="data/d2jsp_topic_urls.txt", help="Output text file for topic URLs")
    parser.add_argument("--open", action="store_true", help="Open extracted topic URLs in browser tabs")
    parser.add_argument("--limit", type=int, default=0, help="Max URLs to output/open (0 = all)")
    parser.add_argument("--batch-size", type=int, default=20, help="Open tabs in batches")
    parser.add_argument("--batch-delay-s", type=float, default=8.0, help="Delay between batches")
    args = parser.parse_args()

    offline_dir = Path(args.offline_dir)
    if not offline_dir.exists() or not offline_dir.is_dir():
        raise RuntimeError(f"offline-dir does not exist or is not a directory: {offline_dir}")

    urls = collect_from_dir(offline_dir)
    if args.limit > 0:
        urls = urls[: args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")
    print(f"Extracted {len(urls)} topic URLs -> {out_path}")

    if args.open and urls:
        total = len(urls)
        for idx, url in enumerate(urls, start=1):
            webbrowser.open_new_tab(url)
            if idx % max(1, args.batch_size) == 0 and idx < total:
                print(f"Opened {idx}/{total} tabs. Waiting {args.batch_delay_s:.1f}s before next batch...")
                time.sleep(args.batch_delay_s)
        print(f"Finished opening {total} topic tabs.")


if __name__ == "__main__":
    main()
