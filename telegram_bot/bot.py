"""
MoneyTracker Bot - Telegram Bot for License Key Management
Integrated with Firebase Firestore
"""

import os
import sys
import logging
import requests
import secrets
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.exceptions import AiogramError

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Firebase Config
FIREBASE_API_KEY = "AIzaSyAps_XRnofsuusFDXD6cxDWTnk0bJ0kUaE"
FIREBASE_PROJECT_ID = "generatormail-e478c"
FIREBASE_BASE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Key prices
PRICES = {
    "1": {"name": "1 День", "days": 1, "price": 30},
    "3": {"name": "3 Дня", "days": 3, "price": 70},
    "7": {"name": "1 Неделя", "days": 7, "price": 120},
    "30": {"name": "1 Месяц", "days": 30, "price": 199},
    "90": {"name": "3 Месяца", "days": 90, "price": 449},
    "180": {"name": "6 Месяцев", "days": 180, "price": 699},
    "lifetime": {"name": "Навсегда", "days": 36500, "price": 1999},
}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class FirebaseDB:
    @staticmethod
    def generate_key(key_type: str) -> Optional[str]:
        """Generate a key in Firebase"""
        key_str = '-'.join([secrets.token_hex(2).upper() for _ in range(4)])
        days = PRICES.get(key_type, PRICES["30"])["days"]
        
        doc_data = {
            "fields": {
                "duration_days": {"integerValue": days},
                "is_active": {"booleanValue": True},
                "hwid": {"nullValue": None},
                "rebind_count": {"integerValue": 0},
                "last_rebind_at": {"nullValue": None},
                "created_at": {"timestampValue": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")},
                "telegram_user_id": {"nullValue": None},
            }
        }
        
        url = f"{FIREBASE_BASE_URL}/keys?documentId={key_str}&key={FIREBASE_API_KEY}"
        try:
            resp = requests.post(url, json=doc_data)
            if resp.status_code == 200:
                return key_str
            else:
                logger.error(f"Firebase error: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Firebase exception: {e}")
            return None

    @staticmethod
    def get_key(key: str) -> Optional[Dict]:
        """Get key info from Firebase"""
        url = f"{FIREBASE_BASE_URL}/keys/{key}?key={FIREBASE_API_KEY}"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data = resp.json()
                fields = data.get("fields", {})
                return {
                    "key": key,
                    "duration_days": fields.get("duration_days", {}).get("integerValue", 0),
                    "is_active": fields.get("is_active", {}).get("booleanValue", False),
                    "hwid": fields.get("hwid", {}).get("stringValue"),
                    "rebind_count": fields.get("rebind_count", {}).get("integerValue", 0),
                    "telegram_user_id": fields.get("telegram_user_id", {}).get("integerValue"),
                }
            return None
        except Exception as e:
            logger.error(f"Get key error: {e}")
            return None

    @staticmethod
    def activate_key(key: str, hwid: str, telegram_user_id: int) -> tuple[bool, str]:
        """Activate a key in Firebase"""
        key_data = FirebaseDB.get_key(key)
        
        if not key_data:
            return False, "❌ Ключ не найден"
        
        if not key_data["is_active"]:
            return False, "❌ Ключ заблокирован"
        
        if key_data["hwid"]:
            return False, "❌ Ключ уже активирован"
        
        # Calculate expiry
        duration = key_data["duration_days"]
        expires = datetime.utcnow() + timedelta(days=duration)
        expires_str = expires.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Update in Firebase
        url = f"{FIREBASE_BASE_URL}/keys/{key}?key={FIREBASE_API_KEY}"
        update_data = {
            "fields": {
                "hwid": {"stringValue": hwid},
                "telegram_user_id": {"integerValue": telegram_user_id},
                "activated_at": {"timestampValue": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")},
                "expires_at": {"stringValue": expires_str},
            }
        }
        
        try:
            resp = requests.patch(url, json=update_data)
            if resp.status_code == 200:
                return True, f"✅ Ключ активирован!\n\n📅 Действителен до: {expires.strftime('%d.%m.%Y')}"
            return False, "❌ Ошибка активации"
        except Exception as e:
            logger.error(f"Activate error: {e}")
            return False, f"❌ Ошибка: {e}"

    @staticmethod
    def get_user_keys(telegram_user_id: int) -> List[Dict]:
        """Get all keys for a user"""
        url = f"{FIREBASE_BASE_URL}/keys?key={FIREBASE_API_KEY}&orderBy=telegram_user_id"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data = resp.json()
                documents = data.get("documents", [])
                user_keys = []
                for doc in documents:
                    fields = doc.get("fields", {})
                    tid = fields.get("telegram_user_id", {}).get("integerValue")
                    if tid == telegram_user_id and fields.get("hwid", {}).get("stringValue"):
                        expires_str = fields.get("expires_at", {}).get("stringValue", "")
                        if expires_str == "Lifetime":
                            expiry_display = "∞ Навсегда"
                        elif expires_str:
                            try:
                                exp = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                                days_left = (exp - datetime.now()).days
                                expiry_display = f"{exp.strftime('%d.%m.%Y')} ({days_left} дн.)"
                            except:
                                expiry_display = expires_str
                        else:
                            expiry_display = "N/A"
                        
                        user_keys.append({
                            "key": doc["name"].split("/")[-1],
                            "expires": expiry_display,
                            "hwid": fields.get("hwid", {}).get("stringValue"),
                        })
                return user_keys
            return []
        except Exception as e:
            logger.error(f"Get user keys error: {e}")
            return []

    @staticmethod
    def get_key_by_hwid(hwid: str) -> Optional[Dict]:
        """Check if any key is active for this HWID"""
        url = f"{FIREBASE_BASE_URL}/keys?key={FIREBASE_API_KEY}&orderBy=hwid"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data = resp.json()
                documents = data.get("documents", [])
                for doc in documents:
                    fields = doc.get("fields", {})
                    key_hwid = fields.get("hwid", {}).get("stringValue")
                    if key_hwid == hwid:
                        expires_str = fields.get("expires_at", {}).get("stringValue", "")
                        is_active = fields.get("is_active", {}).get("booleanValue", False)
                        
                        if is_active and expires_str != "Lifetime" and expires_str:
                            try:
                                exp = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                                if exp < datetime.now():
                                    return None  # Expired
                                days_left = (exp - datetime.now()).days
                                expiry = f"Осталось {days_left} дн."
                            except:
                                expiry = expires_str
                        elif expires_str == "Lifetime":
                            expiry = "∞ Навсегда"
                        else:
                            expiry = "Активирован"
                        
                        return {
                            "key": doc["name"].split("/")[-1],
                            "expiry": expiry,
                        }
                return None
            return None
        except Exception as e:
            logger.error(f"Check HWID error: {e}")
            return None


# Router
router = Router()


def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить ключ", callback_data="buy")],
        [InlineKeyboardButton(text="🔑 Активировать", callback_data="activate")],
        [InlineKeyboardButton(text="📜 Мои ключи", callback_data="mykeys")],
        [InlineKeyboardButton(text="✅ Проверить HWID", callback_data="check")],
        [InlineKeyboardButton(text="📋 Информация", callback_data="info")],
    ])


def get_buy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 День — 30₽", callback_data="p_1")],
        [InlineKeyboardButton(text="3 Дня — 70₽", callback_data="p_3")],
        [InlineKeyboardButton(text="1 Неделя — 120₽", callback_data="p_7")],
        [InlineKeyboardButton(text="1 Месяц — 199₽", callback_data="p_30")],
        [InlineKeyboardButton(text="3 Месяца — 449₽", callback_data="p_90")],
        [InlineKeyboardButton(text="6 Месяцев — 699₽", callback_data="p_180")],
        [InlineKeyboardButton(text="Навсегда — 1999₽", callback_data="p_lifetime")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
    ])


def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Создать ключи", callback_data="admin_create")],
        [InlineKeyboardButton(text="📋 Список HWID", callback_data="admin_hwid_list")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_ban")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
    ])


@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome = """
🏆 <b>MoneyTracker Bot</b>

Добро пожаловать! Здесь вы можете:
• 🛒 Купить лицензионный ключ
• 🔑 Активировать ключ
• 📜 Посмотреть ваши ключи

Выберите действие:
"""
    await message.answer(welcome, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    await message.answer("⚙️ <b>Админ-панель</b>", parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())


@router.callback_query(F.data == "back")
async def back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🏠 <b>Главное меню</b>", parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    text = """
🛒 <b>Выберите тариф:</b>

После оплаты напишите @Aleksandr_Kaniv (ADMIN) для получения ключа
"""
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_buy_keyboard())
    await callback.answer()


@router.callback_query(F.data == "activate")
async def activate(callback: CallbackQuery, state: FSMContext):
    text = """
🔑 <b>Активация ключа</b>

Введите ваш лицензионный ключ в формате:
<code>XXXX-XXXX-XXXX-XXXX</code>

📝 Также вам нужно будет указать HWID программы
"""
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())
    await state.set_state("waiting_key")
    await callback.answer()


@router.message(StateFilter("waiting_key"))
async def process_key(message: Message, state: FSMContext):
    key_input = message.text.strip().upper()
    
    if len(key_input) != 19 or key_input.count("-") != 3:
        await message.answer("❌ Неверный формат ключа. Пример: ABCD-1234-EFGH-5678")
        return
    
    # Ask for HWID
    await state.update_data(key=key_input)
    
    text = """
🔧 <b>Введите ваш HWID</b>

Чтобы узнать HWID:
1. Запустите MoneyTracker
2. Нажмите <code>Shift + Ctrl + H</code>
3. Или в настройках: Настройки → О программе
4. Скопируйте Hardware ID
"""
    await message.answer(text, parse_mode=ParseMode.HTML)
    await state.set_state("waiting_hwid")


@router.message(StateFilter("waiting_hwid"))
async def process_hwid(message: Message, state: FSMContext):
    hwid = message.text.strip()
    
    if len(hwid) < 10:
        await message.answer("❌ HWID слишком короткий")
        return
    
    data = await state.get_data()
    key = data["key"]
    
    success, msg = FirebaseDB.activate_key(key, hwid, message.from_user.id)
    
    await state.clear()
    
    if success:
        await message.answer(f"✅ <b>Ключ активирован!</b>\n\n{msg}\n\n🎮 Запустите MoneyTracker!", parse_mode=ParseMode.HTML)
    else:
        await message.answer(msg)
    
    await message.answer("🏠 <b>Главное меню</b>", parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())


@router.callback_query(F.data == "mykeys")
async def my_keys(callback: CallbackQuery):
    keys = FirebaseDB.get_user_keys(callback.from_user.id)
    
    if not keys:
        text = "📜 <b>У вас нет ключей</b>\n\nКупите ключ, чтобы начать!"
    else:
        text = "📜 <b>Ваши ключи:</b>\n\n"
        for k in keys:
            text += f"🔑 <code>{k['key']}</code>\n⏰ {k['expires']}\n\n"
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "check")
async def check(callback: CallbackQuery, state: FSMContext):
    text = """
🔍 <b>Проверка HWID</b>

Введите ваш HWID для проверки лицензии:

📝 HWID можно узнать в программе: Shift + Ctrl + H
"""
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())
    await state.set_state("check_hwid")
    await callback.answer()


@router.message(StateFilter("check_hwid"))
async def do_check(message: Message, state: FSMContext):
    hwid = message.text.strip()
    
    result = FirebaseDB.get_key_by_hwid(hwid)
    
    await state.clear()
    
    if result:
        await message.answer(
            f"✅ <b>Лицензия активна!</b>\n\n"
            f"🔑 Ключ: <code>{result['key']}</code>\n"
            f"⏰ {result['expiry']}",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            "❌ <b>Лицензия не найдена</b>\n\n"
            "• Ключ не активирован\n"
            "• Срок действия истёк\n"
            "• HWID неверный",
            parse_mode=ParseMode.HTML
        )
    
    await message.answer("🏠 <b>Главное меню</b>", parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())


@router.callback_query(F.data == "info")
async def info(callback: CallbackQuery):
    text = """
📋 <b>Информация</b>

🏆 <b>MoneyTracker</b>
🎮 GTA 5 RP Financial Manager

<b>Возможности:</b>
• 📊 Учёт финансов
• 📦 Управление инвентарём
• 🎣 Рыбалка, добыча, фарм
• 📈 Аналитика и графики
• 🔒 Защита HWID

<b>Тарифы:</b>
• 1 День — 30₽
• 3 Дня — 70₽
• 1 Неделя — 120₽
• 1 Месяц — 199₽
• 3 Месяца — 449₽
• 6 Месяцев — 699₽
• Навсегда — 1999₽

💬 Поддержка: @Aleksandr_Kaniv
"""
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())
    await callback.answer()


# Admin handlers
@router.callback_query(F.data == "admin_create")
async def admin_create(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """
🔢 <b>Создание ключей</b>

Выберите тип:
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 День", callback_data="gk_1")],
        [InlineKeyboardButton(text="3 Дня", callback_data="gk_3")],
        [InlineKeyboardButton(text="1 Неделя", callback_data="gk_7")],
        [InlineKeyboardButton(text="1 Месяц", callback_data="gk_30")],
        [InlineKeyboardButton(text="3 Месяца", callback_data="gk_90")],
        [InlineKeyboardButton(text="6 Месяцев", callback_data="gk_180")],
        [InlineKeyboardButton(text="Навсегда", callback_data="gk_lifetime")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("gk_"))
async def generate_keys(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    key_type = callback.data.replace("gk_", "")
    info = PRICES.get(key_type, PRICES["30"])
    
    await state.update_data(key_type=key_type)
    
    text = f"""
📦 Тип: <b>{info['name']}</b>

Введите количество ключей для генерации:
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 шт", callback_data=f"mk_1")],
        [InlineKeyboardButton(text="5 шт", callback_data=f"mk_5")],
        [InlineKeyboardButton(text="10 шт", callback_data=f"mk_10")],
        [InlineKeyboardButton(text="25 шт", callback_data=f"mk_25")],
        [InlineKeyboardButton(text="50 шт", callback_data=f"mk_50")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_create")],
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("mk_"))
async def make_keys(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    count = int(callback.data.replace("mk_", ""))
    data = await state.get_data()
    key_type = data.get("key_type", "30")
    info = PRICES.get(key_type, PRICES["30"])
    
    generated = []
    errors = 0
    
    for _ in range(count):
        key = FirebaseDB.generate_key(key_type)
        if key:
            generated.append(key)
        else:
            errors += 1
    
    await state.clear()
    
    if generated:
        keys_text = "\n".join([f"<code>{k}</code>" for k in generated])
        text = f"✅ <b>Создано {len(generated)} ключей</b> ({info['name']})\n\n{keys_text}"
        
        if errors:
            text += f"\n\n❌ Ошибок: {errors}"
    else:
        text = "❌ Не удалось создать ключи"
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_hwid_list")
async def admin_hwid_list(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """
📋 <b>Введите HWID</b>

Вставьте HWID пользователя для поиска:
"""
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())
    await state.set_state("admin_check_hwid")
    await callback.answer()


@router.message(StateFilter("admin_check_hwid"))
async def do_admin_check(message: Message, state: FSMContext):
    hwid = message.text.strip()
    
    result = FirebaseDB.get_key_by_hwid(hwid)
    
    await state.clear()
    
    if result:
        await message.answer(
            f"✅ <b>Найден:</b>\n\n"
            f"🔑 {result['key']}\n"
            f"⏰ {result['expiry']}",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer("❌ Не найдено", parse_mode=ParseMode.HTML)
    
    await message.answer("⚙️ <b>Админ-панель</b>", parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())


@router.callback_query(F.data == "admin_ban")
async def admin_ban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """
🚫 <b>Блокировка ключа</b>

Введите ключ для блокировки:
"""
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())
    await state.set_state("admin_ban_key")
    await callback.answer()


@router.message(StateFilter("admin_ban_key"))
async def do_ban(message: Message, state: FSMContext):
    key = message.text.strip().upper()
    
    # Ban in Firebase
    url = f"{FIREBASE_BASE_URL}/keys/{key}?key={FIREBASE_API_KEY}"
    data = {
        "fields": {
            "is_active": {"booleanValue": False}
        }
    }
    
    try:
        resp = requests.patch(url, json=data)
        if resp.status_code == 200:
            await message.answer(f"✅ Ключ <code>{key}</code> заблокирован", parse_mode=ParseMode.HTML)
        else:
            await message.answer("❌ Ключ не найден", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", parse_mode=ParseMode.HTML)
    
    await state.clear()
    await message.answer("⚙️ <b>Админ-панель</b>", parse_mode=ParseMode.HTML, reply_markup=get_admin_keyboard())


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    logger.info("Starting MoneyTracker Bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
