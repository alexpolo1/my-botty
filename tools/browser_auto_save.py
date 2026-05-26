import webbrowser
import time
import keyboard
import os
from pathlib import Path

def main():
    url_file = Path("data/d2jsp_topic_urls.txt")
    if not url_file.exists():
        print("Error: data/d2jsp_topic_urls.txt not found.")
        return

    urls = url_file.read_text().splitlines()
    urls = [u.strip() for u in urls if u.strip()][:20] # Limit to 20 as requested

    print(f"Starting auto-save for {len(urls)} topics.")
    print("!!! IMPORTANT !!!")
    print("1. Ensure your browser is the active window.")
    print("2. Save ONE page manually to the 'data/d2jsp_pages' folder first to set the default path.")
    print("3. Do not touch your keyboard/mouse until finished.")
    print("Starting in 5 seconds...")
    time.sleep(5)

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Opening: {url}")
        webbrowser.open_new_tab(url)
        
        # Wait for page to load and Cloudflare to pass
        time.sleep(8) 
        
        # Press Ctrl+S
        keyboard.press_and_release('ctrl+s')
        time.sleep(2)
        
        # Press Enter to confirm save
        keyboard.press_and_release('enter')
        time.sleep(3)
        
        # Press Ctrl+W to close tab
        keyboard.press_and_release('ctrl+w')
        time.sleep(1)

    print("\nFinished! Now you can run the scraper:")
    print("python tools/fg_market_scraper.py --ladder-start-date 2026-05-20 --offline-dir data/d2jsp_pages --out config/fg_daily_estimates.json")

if __name__ == "__main__":
    main()
