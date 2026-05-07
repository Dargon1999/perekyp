import os
import requests

images = {
    "med.png": "https://github.com/Dargon1999/taro/blob/main/med.png?raw=true",
    "ohota1.png": "https://github.com/Dargon1999/taro/blob/main/ohota1.png?raw=true",
    "ohota2.jpg": "https://github.com/Dargon1999/taro/blob/main/ohota2.jpg?raw=true",
    "klad1.png": "https://github.com/Dargon1999/taro/blob/main/klad1.png?raw=true",
    "klad2.png": "https://github.com/Dargon1999/taro/blob/main/klad2.png?raw=true"
}

output_dir = "assets/tarot"
os.makedirs(output_dir, exist_ok=True)

for filename, url in images.items():
    print(f"Downloading {filename}...")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(os.path.join(output_dir, filename), "wb") as f:
                f.write(response.content)
            print(f"Saved {filename}")
        else:
            print(f"Failed to download {filename}: {response.status_code}")
    except Exception as e:
        print(f"Error downloading {filename}: {e}")

print("Done.")
