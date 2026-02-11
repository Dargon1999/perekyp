import requests
import secrets
import json
import datetime

# Config
API_KEY = "AIzaSyAps_XRnofsuusFDXD6cxDWTnk0bJ0kUaE"
PROJECT_ID = "generatormail-e478c"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def generate_key():
    print("\n--- ГЕНЕРАТОР КЛЮЧЕЙ (FIREBASE) ---")
    
    print("Выберите срок действия:")
    print("1. 1 День")
    print("2. 3 Дня")
    print("3. 1 Неделя")
    print("4. 1 Месяц")
    print("5. 3 Месяца")
    print("6. 6 Месяцев")
    print("7. Навсегда")
    
    choice = input("Ваш выбор (1-7): ")
    days = 7
    if choice == '1': days = 1
    elif choice == '2': days = 3
    elif choice == '3': days = 7
    elif choice == '4': days = 30
    elif choice == '5': days = 90
    elif choice == '6': days = 180
    elif choice == '7': days = 36500
    
    count_str = input("Сколько ключей создать? ")
    try:
        count = int(count_str)
    except:
        count = 1
    
    created_keys = []
    
    for _ in range(count):
        # Generate format XXXX-XXXX-XXXX-XXXX
        key_str = '-'.join([secrets.token_hex(2).upper() for _ in range(4)])
        
        # Firestore Document Structure
        doc_data = {
            "fields": {
                "duration_days": {"integerValue": days},
                "is_active": {"booleanValue": True},
                "hwid": {"nullValue": None}, # Empty initially
                "created_at": {"timestampValue": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
            }
        }
        
        # Create Document (ID = key_str)
        url = f"{BASE_URL}/keys?documentId={key_str}&key={API_KEY}"
        resp = requests.post(url, json=doc_data)
        
        if resp.status_code == 200:
            created_keys.append(key_str)
            print(f"[+] Создан ключ: {key_str}")
        else:
            print(f"[-] Ошибка создания {key_str}: {resp.text}")
            
    print(f"\nУспешно создано: {len(created_keys)}")
    if created_keys:
        with open("generated_keys.txt", "a") as f:
            for k in created_keys:
                f.write(f"{k}\n")
        print("Ключи сохранены в generated_keys.txt")

def delete_key():
    print("\n--- УДАЛЕНИЕ КЛЮЧЕЙ ---")
    keys_input = input("Введите ключи для удаления (через пробел): ").strip()
    if not keys_input: return
    
    keys = keys_input.split()
    if not keys: return
    
    print(f"Выбрано ключей: {len(keys)}")
    confirm = input(f"Вы точно хотите УДАЛИТЬ {len(keys)} ключей? (y/n): ")
    if confirm.lower() != 'y': return

    for key in keys:
        url = f"{BASE_URL}/keys/{key}?key={API_KEY}"
        resp = requests.delete(url)
        
        if resp.status_code == 200:
            print(f"Ключ {key} успешно удален из базы.")
        else:
            print(f"Ошибка удаления {key}: {resp.text}")

def ban_key():
    print("\n--- БАН КЛЮЧА ---")
    key = input("Введите ключ для блокировки: ").strip()
    if not key: return
    
    url = f"{BASE_URL}/keys/{key}?key={API_KEY}&updateMask.fieldPaths=is_active"
    data = {
        "fields": {
            "is_active": {"booleanValue": False}
        }
    }
    resp = requests.patch(url, json=data)
    if resp.status_code == 200:
        print(f"Ключ {key} успешно заблокирован.")
    else:
        print(f"Ошибка: {resp.text}")

def extend_key():
    print("\n--- ПРОДЛЕНИЕ КЛЮЧА ---")
    key = input("Введите ключ: ").strip()
    if not key: return
    
    # First get current data to see if it's activated
    get_url = f"{BASE_URL}/keys/{key}?key={API_KEY}"
    resp = requests.get(get_url)
    if resp.status_code != 200:
        print("Ключ не найден.")
        return
        
    fields = resp.json().get("fields", {})
    expires_at_str = fields.get("expires_at", {}).get("stringValue")
    
    print("Выберите действие:")
    print("1. Добавить дни")
    print("2. Установить 'Навсегда'")
    c = input("> ")
    
    new_expire = ""
    
    if c == '2':
        new_expire = "Lifetime"
    else:
        days = int(input("Сколько дней добавить? "))
        if expires_at_str and expires_at_str != "Lifetime":
            try:
                dt = datetime.datetime.fromisoformat(expires_at_str)
                new_dt = dt + datetime.timedelta(days=days)
                new_expire = new_dt.isoformat()
            except:
                 # If parse fails, assume from now
                 new_expire = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        else:
             # If lifetime or not activated yet, we might need to update duration_days instead
             # But if it is lifetime, adding days makes it not lifetime.
             print("Ключ имеет статус 'Навсегда' или не активирован.")
             if expires_at_str == "Lifetime":
                 print("Сбросить Lifetime и установить дату? (y/n)")
                 if input().lower() == 'y':
                      new_expire = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
                 else:
                      return
             else:
                 # Not activated, update duration_days
                 old_dur = int(fields.get("duration_days", {}).get("integerValue", 7))
                 new_dur = old_dur + days
                 
                 url = f"{BASE_URL}/keys/{key}?key={API_KEY}&updateMask.fieldPaths=duration_days"
                 data = {"fields": {"duration_days": {"integerValue": new_dur}}}
                 requests.patch(url, json=data)
                 print(f"Длительность ключа (при активации) увеличена до {new_dur} дней.")
                 return

    # Update expires_at
    url = f"{BASE_URL}/keys/{key}?key={API_KEY}&updateMask.fieldPaths=expires_at"
    data = {"fields": {"expires_at": {"stringValue": new_expire}}}
    resp = requests.patch(url, json=data)
    if resp.status_code == 200:
        print(f"Срок действия обновлен до: {new_expire}")
    else:
        print(f"Ошибка: {resp.text}")

def list_keys():
    url = f"{BASE_URL}/keys?key={API_KEY}&pageSize=100"
    resp = requests.get(url)
    if resp.status_code != 200:
        print("Ошибка получения списка:", resp.text)
        return
        
    data = resp.json()
    documents = data.get("documents", [])
    
    print(f"\nВсего ключей: {len(documents)}")
    print(f"{'КЛЮЧ':<25} | {'СТАТУС':<8} | {'Срок / Истекает':<20} | {'HWID':<30} | {'LOGIN'}")
    print("-" * 100)
    
    for doc in documents:
        # doc["name"] looks like "projects/.../databases/(default)/documents/keys/KEY-VALUE"
        key_val = doc["name"].split("/")[-1]
        fields = doc.get("fields", {})
        
        is_active = fields.get("is_active", {}).get("booleanValue", True)
        hwid = fields.get("hwid", {}).get("stringValue", "-")
        login = fields.get("login", {}).get("stringValue", "-")
        
        expires_at = fields.get("expires_at", {}).get("stringValue")
        duration = fields.get("duration_days", {}).get("integerValue")
        
        time_info = ""
        if expires_at:
            if expires_at == "Lifetime":
                time_info = "Навсегда"
            else:
                try:
                    dt = datetime.datetime.fromisoformat(expires_at)
                    time_info = dt.strftime("%d.%m.%Y")
                except:
                    time_info = expires_at
        elif duration:
            time_info = f"{duration} дн. (не акт.)"
        else:
            time_info = "?"
            
        status = "АКТИВЕН" if is_active else "БАН"
        print(f"{key_val:<25} | {status:<8} | {time_info:<20} | {hwid:<30} | {login}")

if __name__ == "__main__":
    while True:
        print("\n--- FIREBASE ADMIN ---")
        print("1. Создать ключ")
        print("2. Просмотреть все ключи")
        print("3. Банить ключ")
        print("4. Продлевать ключ")
        print("5. Удалить ключ")
        print("6. Выход")
        
        c = input("> ")
        if c == '1': generate_key()
        elif c == '2': list_keys()
        elif c == '3': ban_key()
        elif c == '4': extend_key()
        elif c == '5': delete_key()
        elif c == '6': break
