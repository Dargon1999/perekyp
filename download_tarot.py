import os
import requests

images = {
    "Death.png": "https://github.com/Dargon1999/taro/blob/main/Death.png?raw=true",
    "Judgement.png": "https://github.com/Dargon1999/taro/blob/main/Judgement.png?raw=true",
    "Justice.png": "https://github.com/Dargon1999/taro/blob/main/Justice.png?raw=true",
    "Strenght.png": "https://github.com/Dargon1999/taro/blob/main/Strenght.png?raw=true",
    "Temperance.png": "https://github.com/Dargon1999/taro/blob/main/Temperance.png?raw=true",
    "The Chariot.png": "https://github.com/Dargon1999/taro/blob/main/The%20Chariot.png?raw=true",
    "The Devil.png": "https://github.com/Dargon1999/taro/blob/main/The%20Devil.png?raw=true",
    "The Emperor.png": "https://github.com/Dargon1999/taro/blob/main/The%20Emperor.png?raw=true",
    "The Empress.png": "https://github.com/Dargon1999/taro/blob/main/The%20Empress.png?raw=true",
    "The Fool.png": "https://github.com/Dargon1999/taro/blob/main/The%20Fool.png?raw=true",
    "The Hanged Man.png": "https://github.com/Dargon1999/taro/blob/main/The%20Hanged%20Man.png?raw=true",
    "The Hermit.png": "https://github.com/Dargon1999/taro/blob/main/The%20Hermit.png?raw=true",
    "The Hierophant.png": "https://github.com/Dargon1999/taro/blob/main/The%20Hierophant.png?raw=true",
    "The High Priestess.png": "https://github.com/Dargon1999/taro/blob/main/The%20High%20Priestess.png?raw=true",
    "The Lovers.png": "https://github.com/Dargon1999/taro/blob/main/The%20Lovers.png?raw=true",
    "The Magician.png": "https://github.com/Dargon1999/taro/blob/main/The%20Magician.png?raw=true",
    "The Moon.png": "https://github.com/Dargon1999/taro/blob/main/The%20Moon.png?raw=true",
    "The Star.png": "https://github.com/Dargon1999/taro/blob/main/The%20Star.png?raw=true",
    "The Sun.png": "https://github.com/Dargon1999/taro/blob/main/The%20Sun.png?raw=true",
    "The Tower.png": "https://github.com/Dargon1999/taro/blob/main/The%20Tower.png?raw=true",
    "The World.png": "https://github.com/Dargon1999/taro/blob/main/The%20World.png?raw=true",
    "Wheel of Fortune.png": "https://github.com/Dargon1999/taro/blob/main/Wheel%20of%20Fortune.png?raw=true"
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
