import sqlite3
import shutil
import os
from pathlib import Path

def main():
    paths = [
        ("Chrome", Path(os.environ["USERPROFILE"]) / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Network" / "Cookies"),
        ("Edge", Path(os.environ["USERPROFILE"]) / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Network" / "Cookies"),
    ]
    
    for name, db_path in paths:
        if not db_path.exists():
            print(f"{name} Cookies DB not found.")
            continue

        print(f"\n--- {name} ---")
        temp_db = f"diag_cookies_{name}.db"
        try:
            shutil.copy(db_path, temp_db)
        except Exception as e:
            print(f"Failed to copy: {e}")
            continue

        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%d2jsp.org%'")
            rows = cursor.fetchall()
            if rows:
                print(f"Found {len(rows)} d2jsp cookies. Inspecting first few:")
                for host, name, val in rows[:5]:
                    prefix = val[:3]
                    print(f"  {host} | {name} | prefix={prefix}")
            else:
                print("No d2jsp cookies found.")
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)

if __name__ == "__main__":
    main()
