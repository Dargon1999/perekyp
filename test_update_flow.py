import requests
import os
import hashlib
import time

BASE_URL = "http://localhost:5000"
ADMIN_KEY = "dargon_admin_secret_2024"

def get_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def test_flow():
    print("--- Starting Update Flow Test ---")
    
    # 1. Upload updater.exe
    print("\n1. Uploading updater.exe...")
    updater_path = "dist/updater.exe"
    if not os.path.exists(updater_path):
        print(f"FAILED: {updater_path} not found. Run build first.")
        return

    with open(updater_path, 'rb') as f:
        files = {'file': f}
        data = {'is_updater': 'true'}
        headers = {'X-Admin-Key': ADMIN_KEY}
        r = requests.post(f"{BASE_URL}/api/upload_update", files=files, data=data, headers=headers)
        print(f"Response: {r.status_code}, {r.json()}")
        if r.status_code != 200: return

    # 2. Upload MoneyTracker.exe
    print("\n2. Uploading MoneyTracker.exe (v9.0.1)...")
    main_exe_path = "Release_9.0.1/MoneyTracker.exe"
    if not os.path.exists(main_exe_path):
        print(f"FAILED: {main_exe_path} not found. Run build first.")
        return

    with open(main_exe_path, 'rb') as f:
        files = {'file': f}
        data = {'version': '9.0.1', 'is_updater': 'false'}
        headers = {'X-Admin-Key': ADMIN_KEY}
        r = requests.post(f"{BASE_URL}/api/upload_update", files=files, data=data, headers=headers)
        print(f"Response: {r.status_code}, {r.json()}")
        if r.status_code != 200: return

    # 3. Check update info
    print("\n3. Checking update info...")
    r = requests.get(f"{BASE_URL}/update_info")
    info = r.json()
    print(f"Response: {info}")
    expected_hash = get_file_hash(main_exe_path)
    if info['version'] == '9.0.1' and info['signature'] == expected_hash:
        print("SUCCESS: Update info matches uploaded file.")
    else:
        print(f"FAILED: Info mismatch. Expected version 9.0.1 and hash {expected_hash}")
        return

    # 4. Download updater.exe
    print("\n4. Downloading updater.exe...")
    r = requests.get(f"{BASE_URL}/download?file=updater.exe", stream=True)
    if r.status_code == 200:
        with open("test_downloaded_updater.exe", 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        orig_hash = get_file_hash(updater_path)
        dl_hash = get_file_hash("test_downloaded_updater.exe")
        if orig_hash == dl_hash:
            print("SUCCESS: Downloaded updater matches original.")
        else:
            print("FAILED: Updater hash mismatch.")
    else:
        print(f"FAILED: Download updater returned {r.status_code}")

    # 5. Download main exe
    print("\n5. Downloading MoneyTracker.exe...")
    r = requests.get(f"{BASE_URL}/download", stream=True)
    if r.status_code == 200:
        with open("test_downloaded_main.exe", 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        orig_hash = get_file_hash(main_exe_path)
        dl_hash = get_file_hash("test_downloaded_main.exe")
        if orig_hash == dl_hash:
            print("SUCCESS: Downloaded main exe matches original.")
        else:
            print("FAILED: Main exe hash mismatch.")
    else:
        print(f"FAILED: Download main exe returned {r.status_code}")

    # Cleanup
    print("\nCleaning up test files...")
    if os.path.exists("test_downloaded_updater.exe"): os.remove("test_downloaded_updater.exe")
    if os.path.exists("test_downloaded_main.exe"): os.remove("test_downloaded_main.exe")
    print("Test Complete.")

if __name__ == "__main__":
    test_flow()
