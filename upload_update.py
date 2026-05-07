import requests
import sys
import os

SERVER_URL = "https://dargon-52si.onrender.com"
UPLOAD_URL = f"{SERVER_URL}/api/upload_update"
ADMIN_KEY = "dargon_admin_secret_2024"

def upload_update(exe_path, version="1.0.4", is_updater=False):
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
    
    # Path to the single self-updating EXE
    exe_path = os.path.join(f"Release_v{VERSION}_Single", "MoneyTracker.exe")
    
    if os.path.exists(exe_path):
        # In the new architecture, we only need to upload the main app
        # because the updater is integrated via PowerShell script.
        upload_update(exe_path, VERSION, is_updater=False)
    else:
        print(f"Main EXE not found at {exe_path}")
