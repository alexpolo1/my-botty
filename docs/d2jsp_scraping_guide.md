# d2jsp Semi-Automated Scraping Guide

Due to Cloudflare's aggressive bot protection, fully automated scraping is currently restricted. This project uses a **Semi-Automated (Offline) Workflow** that leverages your authenticated browser session to safely collect market data.

## Prerequisites

1.  **Python Dependencies:** Ensure `keyboard` and `requests` are installed (included in `requirements.txt`).
2.  **Browser:** Google Chrome is recommended.
3.  **Authentication:** Be logged into [forums.d2jsp.org](https://forums.d2jsp.org/) in your browser.

---

## The Workflow

### 1. Initial Directory Setup
Before running the automation, you must set the default "Save As" path in your browser:
1.  Open any topic on d2jsp.
2.  Press `Ctrl + S`.
3.  Navigate to your bot folder: `data/d2jsp_pages/`.
4.  Save the file. Your browser will now remember this location as the default.

### 2. Collect Topic URLs
If you don't have a fresh list of URLs, run the collector on a saved forum listing page:
```powershell
python tools/d2jsp_topic_collector.py --offline-dir data/d2jsp_pages --out data/d2jsp_topic_urls.txt
```

### 3. Run Browser Automation
This script will open the first 20 topics from your list, wait for Cloudflare to pass, and simulate the save command.
```powershell
python tools/browser_auto_save.py
```
**Important:** 
*   Keep your browser as the active window.
*   Do not move the mouse or type while the script is running.
*   It will automatically `Ctrl + S` -> `Enter` -> `Ctrl + W` for each tab.

### 4. Generate Price Estimates
Once the HTML files are saved in `data/d2jsp_pages/`, run the offline scraper to update your bot's configuration:
```powershell
python tools/fg_market_scraper.py --ladder-start-date 2026-05-20 --offline-dir data/d2jsp_pages --out config/fg_daily_estimates.json
```

---

## Troubleshooting

### Cloudflare "Just a Moment" Loop
If the automation is too fast and hits a "Just a Moment" screen that doesn't resolve:
1.  Increase the `time.sleep(8)` value in `tools/browser_auto_save.py`.
2.  Manually solve one challenge in the browser to "warm up" the IP clearance.

### Files Not Saving to Correct Folder
If files are saving to your "Downloads" folder instead of `data/d2jsp_pages`, the browser's default path was reset. Repeat **Step 1** to fix it.

### Date Parsing Errors
If the scraper reports 0 topics scanned or dates are missing, ensure your browser language isn't translating the page, as the scraper expects English month names (Jan, Feb, Mar, etc.).
