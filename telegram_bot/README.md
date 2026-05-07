# MoneyTracker Telegram Bot 🤖

Бот для автоматической продажи и управления лицензионными ключами MoneyTracker.

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd telegram_bot
pip install -r requirements.txt
```

### 2. Настройка

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=123456789,987654321
```

### 3. Запуск

```bash
python bot.py
```

## 📋 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/admin` | Панель администратора |
| `/help` | Справка |

## 🔧 Функционал

### Для пользователей:
- 🛒 Покупка ключей
- 🔑 Активация ключей
- 📜 Просмотр своих ключей
- ✅ Проверка лицензии

### Для администраторов:
- 📊 Статистика продаж
- 🔑 Генерация ключей
- 👥 Управление пользователями
- 🎁 Создание промокодов
- 📢 Рассылки

## 💳 Интеграция с платежами

### Telegram Payments (рекомендуется)
1. Получите токен платежей от @BotFather
2. Добавьте `PROVIDER_TOKEN` в `.env`
3. Бот автоматически предложит оплату через Telegram

### ЮKassa (альтернатива)
Для интеграции с ЮKassa добавьте:
```python
import yookassa
yookassa.Configuration.account_id = "your_account_id"
yookassa.Configuration.secret_key = "your_secret_key"
```

## 🔐 Безопасность

- HWID-привязка к оборудованию
- Защита от брутфорса ключей
- Блокировка пользователей
- Логирование всех действий

## 📁 Структура файлов

```
telegram_bot/
├── bot.py              # Основной код бота
├── bot_database.db    # SQLite база данных (создается автоматически)
├── requirements.txt   # Зависимости
├── .env.example      # Пример конфигурации
└── README.md         # Этот файл
```

## 🚀 Деплой

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

### VPS (Linux)
```bash
screen -S mtracker-bot
python bot.py
# Ctrl+A, D для выхода
```

### Windows Task Scheduler
```batch
@echo off
cd /d %~dp0
python bot.py
```

## 📞 Поддержка

- Telegram: @MoneyTrackerSupport
- Email: support@moneytracker.ru

---

© 2024-2026 MoneyTracker
