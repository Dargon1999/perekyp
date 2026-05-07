"""
Admin Panel for MoneyTracker Bot
Console-based key management
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta
import uuid
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")

PRICES = {
    "1_month": {"name": "1 месяц", "days": 30, "price": 149},
    "3_months": {"name": "3 месяца", "days": 90, "price": 349},
    "6_months": {"name": "6 месяцев", "days": 180, "price": 599},
    "1_year": {"name": "1 год", "days": 365, "price": 999},
    "lifetime": {"name": "Навсегда", "days": 9999, "price": 1999},
}

KEY_TYPES = list(PRICES.keys())


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    clear_screen()
    print("=" * 60)
    print("       MONEYTRACKER BOT - ADMIN PANEL")
    print("=" * 60)
    print()


def connect_db():
    if not os.path.exists(DB_PATH):
        print("❌ База данных не найдена. Запустите бота хотя бы раз.")
        input()
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def main_menu(conn):
    while True:
        print_header()
        print("📋 Главное меню:")
        print()
        print("  [1] 📊 Статистика")
        print("  [2] 🔑 Управление ключами")
        print("  [3] 👥 Пользователи")
        print("  [4] 🎁 Промокоды")
        print("  [5] 💾 Экспорт ключей")
        print("  [0] 🚪 Выход")
        print()
        
        choice = input("Выберите действие: ").strip()
        
        if choice == "1":
            show_stats(conn)
        elif choice == "2":
            keys_menu(conn)
        elif choice == "3":
            users_menu(conn)
        elif choice == "4":
            promo_menu(conn)
        elif choice == "5":
            export_keys(conn)
        elif choice == "0":
            print("👋 До свидания!")
            break


def show_stats(conn):
    print_header()
    print("📊 СТАТИСТИКА")
    print("-" * 40)
    
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    print(f"👥 Пользователей: {users}")
    
    cursor.execute("SELECT COUNT(*) FROM keys WHERE is_used = 1")
    used = cursor.fetchone()[0]
    print(f"✅ Активировано ключей: {used}")
    
    cursor.execute("SELECT COUNT(*) FROM keys WHERE is_used = 0")
    available = cursor.fetchone()[0]
    print(f"📦 Доступно ключей: {available}")
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE status = 'completed'")
    revenue = cursor.fetchone()[0] or 0
    print(f"💰 Доход: {revenue}₽")
    
    print()
    input("Нажмите Enter для продолжения...")


def keys_menu(conn):
    while True:
        print_header()
        print("🔑 УПРАВЛЕНИЕ КЛЮЧАМИ")
        print("-" * 40)
        print()
        print("  [1] 🔢 Сгенерировать ключи")
        print("  [2] 📋 Список всех ключей")
        print("  [3] 🔍 Найти ключ")
        print("  [4] ❌ Заблокировать ключ")
        print("  [5] ✅ Разблокировать ключ")
        print("  [0] ◀️ Назад")
        print()
        
        choice = input("Выберите действие: ").strip()
        
        if choice == "1":
            generate_keys(conn)
        elif choice == "2":
            list_keys(conn)
        elif choice == "3":
            search_key(conn)
        elif choice == "4":
            ban_key(conn)
        elif choice == "5":
            unban_key(conn)
        elif choice == "0":
            break


def generate_keys(conn):
    print_header()
    print("🔢 ГЕНЕРАЦИЯ КЛЮЧЕЙ")
    print("-" * 40)
    print()
    
    print("Типы ключей:")
    for i, (key_type, info) in enumerate(PRICES.items(), 1):
        print(f"  [{i}] {info['name']} ({info['price']}₽)")
    print()
    
    type_choice = input("Выберите тип [1-5]: ").strip()
    try:
        type_index = int(type_choice) - 1
        key_type = KEY_TYPES[type_index]
    except (ValueError, IndexError):
        print("❌ Неверный выбор")
        input()
        return
    
    try:
        count = int(input("Количество ключей: "))
        if count < 1 or count > 1000:
            print("❌ Количество должно быть от 1 до 1000")
            input()
            return
    except ValueError:
        print("❌ Неверный формат")
        input()
        return
    
    cursor = conn.cursor()
    generated = []
    
    for _ in range(count):
        key_id = f"MT-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
        cursor.execute(
            "INSERT INTO keys (key_id, key_type, is_used) VALUES (?, ?, 0)",
            (key_id, key_type)
        )
        generated.append(key_id)
    
    conn.commit()
    
    print()
    print(f"✅ Сгенерировано {count} ключей!")
    print()
    print("Ключи:")
    for key in generated[:20]:  # Показываем первые 20
        print(f"  {key}")
    
    if count > 20:
        print(f"  ... и ещё {count - 20} ключей")
    
    # Сохраняем в файл
    filename = f"keys_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write(f"# MoneyTracker Keys - {datetime.now()}\n")
        f.write(f"# Type: {PRICES[key_type]['name']}\n\n")
        for key in generated:
            f.write(f"{key}\n")
    
    print()
    print(f"💾 Сохранено в файл: {filename}")
    input()


def list_keys(conn):
    print_header()
    print("📋 СПИСОК КЛЮЧЕЙ")
    print("-" * 40)
    print()
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT key_id, key_type, is_used, is_banned, owner_id, used_at 
        FROM keys 
        ORDER BY rowid DESC 
        LIMIT 100
    """)
    
    keys = cursor.fetchall()
    
    if not keys:
        print("❌ Ключей не найдено")
    else:
        for key in keys:
            status = "✅" if key[2] else "📦"
            banned = "🚫" if key[3] else ""
            owner = f"→ {key[4]}" if key[4] else ""
            used = f"[{key[5][:10]}]" if key[5] else ""
            print(f"{status}{banned} {key[0]} | {key[1]} | {owner} {used}")
    
    print()
    input("Нажмите Enter для продолжения...")


def search_key(conn):
    print_header()
    print("🔍 ПОИСК КЛЮЧА")
    print("-" * 40)
    print()
    
    search = input("Введите ключ или ID пользователя: ").strip().upper()
    
    if not search:
        return
    
    cursor = conn.cursor()
    
    # Search by key
    cursor.execute("SELECT * FROM keys WHERE key_id LIKE ?", (f"%{search}%",))
    key = cursor.fetchone()
    
    if key:
        print()
        print(f"🔑 {key[0]}")
        print(f"   Тип: {key[1]}")
        print(f"   Статус: {'Активирован' if key[6] else 'Доступен'}")
        print(f"   Заблокирован: {'Да' if key[7] else 'Нет'}")
        if key[4]:
            print(f"   Владелец: {key[4]}")
        if key[8]:
            print(f"   Активирован: {key[8][:19]}")
        if key[9]:
            print(f"   HWID: {key[9]}")
    else:
        # Search by user
        cursor.execute("SELECT * FROM users WHERE user_id LIKE ?", (f"%{search}%",))
        user = cursor.fetchone()
        
        if user:
            print()
            print(f"👤 Пользователь: {user[0]}")
            print(f"   Username: {user[1]}")
            print(f"   Имя: {user[2]}")
            print(f"   Зарегистрирован: {user[3][:19]}")
            print(f"   Заблокирован: {'Да' if user[4] else 'Нет'}")
        else:
            print("❌ Ничего не найдено")
    
    print()
    input("Нажмите Enter для продолжения...")


def ban_key(conn):
    print_header()
    print("❌ БЛОКИРОВКА КЛЮЧА")
    print("-" * 40)
    print()
    
    key_id = input("Введите ключ: ").strip().upper()
    
    cursor = conn.cursor()
    cursor.execute("UPDATE keys SET is_banned = 1 WHERE key_id = ?", (key_id,))
    
    if cursor.rowcount:
        conn.commit()
        print("✅ Ключ заблокирован")
    else:
        print("❌ Ключ не найден")
    
    input()


def unban_key(conn):
    print_header()
    print("✅ РАЗБЛОКИРОВКА КЛЮЧА")
    print("-" * 40)
    print()
    
    key_id = input("Введите ключ: ").strip().upper()
    
    cursor = conn.cursor()
    cursor.execute("UPDATE keys SET is_banned = 0 WHERE key_id = ?", (key_id,))
    
    if cursor.rowcount:
        conn.commit()
        print("✅ Ключ разблокирован")
    else:
        print("❌ Ключ не найден")
    
    input()


def users_menu(conn):
    print_header()
    print("👥 ПОЛЬЗОВАТЕЛИ")
    print("-" * 40)
    print()
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 50")
    users = cursor.fetchall()
    
    if not users:
        print("❌ Пользователей не найдено")
    else:
        for user in users:
            banned = "🚫" if user[4] else ""
            print(f"{banned} {user[0]} | {user[2]} | {user[3][:10]}")
    
    print()
    input("Нажмите Enter для продолжения...")


def promo_menu(conn):
    while True:
        print_header()
        print("🎁 УПРАВЛЕНИЕ ПРОМОКОДАМИ")
        print("-" * 40)
        print()
        print("  [1] ➕ Создать промокод")
        print("  [2] 📋 Список промокодов")
        print("  [0] ◀️ Назад")
        print()
        
        choice = input("Выберите действие: ").strip()
        
        if choice == "1":
            create_promo(conn)
        elif choice == "2":
            list_promos(conn)
        elif choice == "0":
            break


def create_promo(conn):
    print_header()
    print("➕ СОЗДАНИЕ ПРОМОКОДА")
    print("-" * 40)
    print()
    
    code = input("Код промокода: ").strip().upper()
    if not code:
        print("❌ Код не может быть пустым")
        input()
        return
    
    try:
        discount = int(input("Скидка (%): "))
        max_uses = int(input("Макс. использований: "))
        days = int(input("Действителен (дней): "))
    except ValueError:
        print("❌ Неверный формат")
        input()
        return
    
    expires = datetime.now() + timedelta(days=days)
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO promo_codes (code, discount_percent, max_uses, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (code, discount, max_uses, expires.isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    print(f"✅ Промокод {code} создан!")
    print(f"   Скидка: {discount}%")
    print(f"   Действителен до: {expires.strftime('%d.%m.%Y')}")
    input()


def list_promos(conn):
    print_header()
    print("📋 СПИСОК ПРОМОКОДОВ")
    print("-" * 40)
    print()
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
    promos = cursor.fetchall()
    
    if not promos:
        print("❌ Промокодов не найдено")
    else:
        for promo in promos:
            print(f"🎁 {promo[0]} | {promo[1]}% | {promo[2]}/{promo[3]} | {promo[4][:10]}")
    
    print()
    input("Нажмите Enter для продолжения...")


def export_keys(conn):
    print_header()
    print("💾 ЭКСПОРТ КЛЮЧЕЙ")
    print("-" * 40)
    print()
    
    cursor = conn.cursor()
    cursor.execute("SELECT key_id, key_type FROM keys WHERE is_used = 0 ORDER BY key_type")
    keys = cursor.fetchall()
    
    if not keys:
        print("❌ Нет доступных ключей")
        input()
        return
    
    # Group by type
    by_type = {}
    for key in keys:
        if key[1] not in by_type:
            by_type[key[1]] = []
        by_type[key[1]].append(key[0])
    
    filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# MoneyTracker Keys Export\n")
        f.write(f"# Date: {datetime.now()}\n")
        f.write(f"# Total: {len(keys)} keys\n\n")
        
        for key_type, key_list in by_type.items():
            f.write(f"\n## {PRICES[key_type]['name']} ({len(key_list)} шт)\n")
            for key in key_list:
                f.write(f"{key}\n")
    
    print(f"✅ Экспортировано {len(keys)} ключей в {filename}")
    input()


if __name__ == "__main__":
    conn = connect_db()
    try:
        main_menu(conn)
    finally:
        conn.close()
