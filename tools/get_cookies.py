import browser_cookie3
from http.cookiejar import MozillaCookieJar
import sys
from pathlib import Path

def save_cookies(cj, filename):
    mj = MozillaCookieJar(filename)
    for cookie in cj:
        mj.set_cookie(cookie)
    mj.save(ignore_discard=True, ignore_expires=True)

def main():
    domain = 'forums.d2jsp.org'
    found = False
    
    browsers = [
        ('Chrome', browser_cookie3.chrome),
        ('Edge', browser_cookie3.edge),
        ('Firefox', browser_cookie3.firefox),
        ('Opera', browser_cookie3.opera),
        ('Brave', browser_cookie3.brave),
    ]
    
    print(f"Searching for {domain} cookies...")
    
    for name, func in browsers:
        try:
            print(f"Trying {name}...", end=' ', flush=True)
            cj = func(domain_name=domain)
            count = len(list(cj))
            print(f"found {count} cookies.")
            if count > 0:
                save_cookies(cj, 'cookies.txt')
                print(f"Successfully saved {count} cookies from {name} to cookies.txt")
                found = True
                break
        except Exception as e:
            print(f"failed: {e}")
            
    if not found:
        print("\nCould not find any d2jsp cookies automatically.")
        print("Please ensure you are logged in to forums.d2jsp.org in one of your browsers.")
        sys.exit(1)

if __name__ == "__main__":
    main()
