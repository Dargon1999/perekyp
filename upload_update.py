import requests
import sys
import os

SERVER_URL = "https://dargon-52si.onrender.com"
UPLOAD_URL = f"{SERVER_URL}/api/upload_update"
ADMIN_KEY = "dargon_admin_secret_2024"

def upload_update(exe_path, version="7.2.0", is_updater=False):
    # 2. Upload with Header
    if not os.path.exists(exe_path):
        print(f"File not found: {exe_path}")
        return False
        
    type_str = "updater" if is_updater else "main app"
    print(f"Uploading {exe_path} ({type_str}, Version {version}) using Admin Key...")
    
    headers = {
        "X-Admin-Key": ADMIN_KEY
    }
    
    with open(exe_path, 'rb') as f:
        files = {'file': (os.path.basename(exe_path), f)}
        data = {'version': version, 'is_updater': 'true' if is_updater else 'false'}
        try:
            resp = requests.post(UPLOAD_URL, files=files, data=data, headers=headers)
        except Exception as e:
            print(f"Connection error: {e}")
            return False
        
    if resp.status_code == 200:
        print(f"{type_str.capitalize()} upload successful!")
        print(resp.json())
        return True
    else:
        print(f"{type_str.capitalize()} upload failed: {resp.status_code}")
        print(resp.text)
        return False

if __name__ == "__main__":
    from version import VERSION
    
    # 1. Upload updater first
    updater_path = os.path.join("dist", "updater.exe")
    if os.path.exists(updater_path):
        upload_update(updater_path, VERSION, is_updater=True)
    else:
        print(f"Warning: updater.exe not found at {updater_path}")

    # 2. Upload main app
    exe_path = os.path.join("Release_9.0.1", "MoneyTracker.exe")
    if os.path.exists(exe_path):
        upload_update(exe_path, VERSION, is_updater=False)
    else:
        # Fallback to dist
        dist_path = os.path.join("dist", "MoneyTracker.exe")
        if os.path.exists(dist_path):
            upload_update(dist_path, VERSION, is_updater=False)
        else:
             print(f"Main EXE not found at {exe_path} or {dist_path}")
