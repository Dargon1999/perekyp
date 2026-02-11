import requests
import json

SERVER_URL = "http://localhost:5000"
ADMIN_SECRET = "admin123"

def generate_key(key_type, count=1):
    try:
        response = requests.post(
            f"{SERVER_URL}/admin/generate",
            headers={"X-Admin-Secret": ADMIN_SECRET, "Accept": "application/json"},
            json={"type": key_type, "count": count}
        )
        if response.status_code == 200:
            result = response.json().get("keys", [])
            if not result:
                print(f"DEBUG: Empty keys. Response: {response.text}")
            return result
        else:
            print(f"Error: {response.status_code} {response.text}")
            return []
    except Exception as e:
        print(f"Connection failed: {e}")
        return []

with open("generated_keys.txt", "w", encoding="utf-8") as f:
    f.write("--- GENERATED KEYS ---\n")
    f.write("Lifetime (Пожизненный):\n")
    for k in generate_key("lifetime", 1):
        f.write(f"  {k}\n")

    f.write("\n1 Month (Месяц):\n")
    for k in generate_key("1_month", 1):
        f.write(f"  {k}\n")
        
    f.write("\n1 Week (Неделя):\n")
    for k in generate_key("1_week", 1):
        f.write(f"  {k}\n")
print("Keys written to generated_keys.txt")
