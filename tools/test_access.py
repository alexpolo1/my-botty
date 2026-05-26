import requests
import time
from http.cookiejar import MozillaCookieJar

def main():
    session = requests.Session()
    cookiejar = MozillaCookieJar("cookies.txt")
    cookiejar.load(ignore_discard=True, ignore_expires=True)
    session.cookies = cookiejar
    
    headers = {
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
    
    print("Step 1: Hitting root...")
    r1 = session.get("https://forums.d2jsp.org/", headers=headers, timeout=20)
    print(f"Status: {r1.status_code}, Length: {len(r1.text)}")
    
    if r1.status_code == 200:
        print("Step 2: Hitting forum...")
        r2 = session.get("https://forums.d2jsp.org/forum.php?f=271", headers=headers, timeout=20)
        print(f"Status: {r2.status_code}, Length: {len(r2.text)}")
        if "Just a moment..." in r2.text:
            print("Blocked by Cloudflare challenge.")
        else:
            print("Access granted!")
    else:
        print("Root hit failed.")

if __name__ == "__main__":
    main()
