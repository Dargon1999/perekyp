@echo off
title MoneyTracker Bot
cd /d "%~dp0"

echo ========================================
echo    MoneyTracker Telegram Bot
echo ========================================
echo.

:: Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Copy .env.example to .env and set your BOT_TOKEN
    pause
    exit /b 1
)

echo Starting bot...
echo.

python bot.py

pause
