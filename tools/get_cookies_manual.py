import os
import json
import base64
import sqlite3
import shutil
from pathlib import Path
import win32crypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def get_master_key(user_data_path):
    local_state_path = user_data_path / "Local State"
    if not local_state_path.exists():
        return None
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    # Remove DPAPI prefix
    encrypted_key = encrypted_key[5:]
    master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return master_key

def generate_netscape_cookie(domain, name, value, path, expiry):
    # Netscape cookie format:
    # domain \t TRUE/FALSE \t path \t TRUE/FALSE \t expiry \t name \t value
    return f"{domain}\tTRUE\t{path}\tFALSE\t{expiry}\t{name}\t{value}\n"

def get_firefox_cookies():
    ff_path = Path(os.environ["APPDATA"]) / "Mozilla" / "Firefox" / "Profiles"
    if not ff_path.exists():
        return []
    
    cookies = []
    for profile in ff_path.glob("*"):
        db_path = profile / "cookies.sqlite"
        if not db_path.exists():
            continue
            
        print(f"Searching Firefox profile: {profile.name}...")
        temp_db = f"cookies_temp_ff_{profile.name}.sqlite"
        try:
            shutil.copy(db_path, temp_db)
        except:
            continue
            
        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT host, name, path, expiry, value FROM moz_cookies WHERE host LIKE '%d2jsp.org%'")
            for host, name, path, expiry, value in cursor.fetchall():
                cookies.append(generate_netscape_cookie(host, name, value, path, expiry))
            conn.close()
        except Exception as e:
            print(f"    Error reading Firefox database: {e}")
        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)
    return cookies

def main():
    browsers = [
        ("Chrome", Path(os.environ["USERPROFILE"]) / "AppData" / "Local" / "Google" / "Chrome" / "User Data"),
        ("Edge", Path(os.environ["USERPROFILE"]) / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data"),
    ]
    
    cookies_txt = []
    
    # Try Chromium-based
    for browser_name, user_data_path in browsers:
        if not user_data_path.exists():
            continue
            
        print(f"Searching {browser_name} cookies...")
        
        master_key = get_master_key(user_data_path)
        if not master_key:
            print(f"  {browser_name} master key not found.")
            continue
        
        aes_gcm = AESGCM(master_key)
        profile_dirs = ["Default"] + [p.name for p in user_data_path.glob("Profile *")]
        
        for profile in profile_dirs:
            db_path = user_data_path / profile / "Network" / "Cookies"
            if not db_path.exists():
                db_path = user_data_path / profile / "Cookies"
            if not db_path.exists():
                continue

            print(f"  Checking profile: {profile}...")
            temp_db = f"cookies_temp_{browser_name}_{profile}.db"
            try:
                shutil.copy(db_path, temp_db)
            except Exception as e:
                print(f"    Access denied to {db_path}. Browser is likely open.")
                continue
            
            try:
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                cursor.execute("SELECT host_key, name, path, expires_utc, encrypted_value FROM cookies WHERE host_key LIKE '%d2jsp.org%'")
                
                for host, name, path, expires, encrypted_value in cursor.fetchall():
                    try:
                        if encrypted_value.startswith(b'v10'):
                            decrypted_value = aes_gcm.decrypt(encrypted_value[3:15], encrypted_value[15:], None).decode('utf-8')
                        else:
                            decrypted_value = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8')
                        
                        expiry_seconds = (expires // 1000000) - 11644473600 if expires > 0 else 0
                        cookies_txt.append(generate_netscape_cookie(host, name, decrypted_value, path, int(max(0, expiry_seconds))))
                    except:
                        pass
                conn.close()
            except Exception as e:
                print(f"    Error reading database: {e}")
            finally:
                if os.path.exists(temp_db):
                    os.remove(temp_db)

    # Try Firefox
    cookies_txt.extend(get_firefox_cookies())

    if cookies_txt:
        unique_cookies = {}
        for line in cookies_txt:
            parts = line.split('\t')
            unique_cookies[(parts[0], parts[5])] = line
            
        with open("cookies.txt", "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.writelines(unique_cookies.values())
        print(f"Successfully saved {len(unique_cookies)} cookies to cookies.txt")
    else:
        print("\nNo d2jsp cookies found.")
        print("ACTION REQUIRED: Please CLOSE your browser (Chrome/Edge/Firefox) and run this again, OR log in to d2jsp in your browser.")

if __name__ == "__main__":
    main()
