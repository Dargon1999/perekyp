#!/usr/bin/env python3
"""
MoneyTracker - Сборка всех платформ
Создает:
1. EXE для Windows
2. APK для Android (через Capacitor)
3. PWA пакет для iOS
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
BUILD_DIR = BASE_DIR / "build_output"
DIST_DIR = BASE_DIR / "dist"

def run_command(cmd, cwd=None, description=""):
    """Выполнить команду"""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}")
    
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return False
    
    print(f"SUCCESS: {description} completed")
    return True

def clean_build_dirs():
    """Очистка директорий сборки"""
    print("Cleaning build directories...")
    
    for dir_path in [BUILD_DIR, DIST_DIR, BASE_DIR / "build", BASE_DIR / "dist"]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Removed: {dir_path}")
    
    BUILD_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)

def build_windows_exe():
    """Сборка EXE для Windows"""
    print("\n" + "="*60)
    print("BUILDING WINDOWS EXE")
    print("="*60)
    
    # Устанавливаем PyInstaller
    run_command(
        "pip install pyinstaller",
        description="Installing PyInstaller"
    )
    
    # Собираем EXE
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "MoneyTracker",
        "--icon", "icon.ico",
        "--add-data", "web;web",
        "--add-data", "*.py;.",
        "--hidden-import", "flask",
        "--hidden-import", "flask_login",
        "--hidden-import", "flask_sqlalchemy",
        "--hidden-import", "flask_socketio",
        "--hidden-import", "PIL",
        "--hidden-import", "socketio",
        "--hidden-import", "engineio",
        "--exclude-module", "tkinter",
        "--noconsole",
        "launcher.py"
    ]
    
    success = run_command(
        " ".join(cmd),
        description="Building Windows EXE"
    )
    
    if success:
        exe_path = DIST_DIR / "MoneyTracker.exe"
        if exe_path.exists():
            # Копируем в build_output
            shutil.copy(exe_path, BUILD_DIR / "MoneyTracker_Windows.exe")
            print(f"\nWindows EXE created: {BUILD_DIR / 'MoneyTracker_Windows.exe'}")
            return True
    
    return False

def create_pwa_package():
    """Создание PWA пакета для установки на мобильные устройства"""
    print("\n" + "="*60)
    print("CREATING PWA PACKAGE")
    print("="*60)
    
    pwa_dir = BUILD_DIR / "PWA"
    pwa_dir.mkdir(exist_ok=True)
    
    # Копируем все веб-файлы
    web_src = BASE_DIR / "web"
    web_dst = pwa_dir / "web"
    
    if web_src.exists():
        shutil.copytree(web_src, web_dst, dirs_exist_ok=True)
        print(f"Copied web files to {web_dst}")
    
    # Копируем серверные файлы
    server_files = [
        "run_server.py",
        "launcher.py",
        "requirements.txt",
        "data_manager.py",
        "database_manager.py",
        "utils.py",
        "version.py",
        "event_bus.py",
        "plugin_manager.py",
    ]
    
    for file in server_files:
        src = BASE_DIR / file
        if src.exists():
            shutil.copy(src, pwa_dir / file)
            print(f"Copied: {file}")
    
    # Создаем README с инструкциями
    readme_content = """# MoneyTracker PWA - Установка на мобильные устройства

## iOS (iPhone/iPad)

### Способ 1: Установка через Safari (Рекомендуется)
1. Откройте Safari на iPhone/iPad
2. Перейдите на адрес сервера (например: http://192.168.1.100:5000)
3. Нажмите кнопку "Поделиться" (квадрат со стрелкой внизу)
4. Прокрутите вниз и выберите "На экран «Домой»"
5. Нажмите "Добавить"

### Способ 2: Установка через браузер
1. Откройте Chrome на iPhone/iPad
2. Перейдите на адрес сервера
3. Нажмите "Установить приложение" или "Добавить на главный экран"

## Android

### Способ 1: Установка через Chrome (Рекомендуется)
1. Откройте Chrome на Android устройстве
2. Перейдите на адрес сервера (например: http://192.168.1.100:5000)
3. Дождитесь появления баннера "Установить приложение"
4. Нажмите "Установить"

### Способ 2: Добавление на главный экран
1. Откройте Chrome
2. Перейдите на адрес сервера
3. Нажмите меню (три точки)
4. Выберите "Установить приложение" или "Добавить на главный экран"

## Запуск сервера

### Windows
1. Запустите `MoneyTracker_Windows.exe` или `launcher.py`
2. Сервер запустится на http://localhost:5100
3. Откройте браузер и перейдите на этот адрес

### Python (все платформы)
```bash
pip install -r requirements.txt
python run_server.py
```

## Настройка сети для синхронизации

Чтобы получить доступ с мобильного устройства:

1. Узнайте IP-адрес вашего компьютера:
   - Windows: `ipconfig` (ищите "IPv4 Address")
   - Linux/Mac: `ifconfig` или `ip a`

2. Запустите сервер:
   ```bash
   python run_server.py
   ```

3. На мобильном устройстве перейдите по адресу:
   ```
   http://<ВАШ_IP>:5000
   ```
   Например: `http://192.168.1.100:5000`

4. Войдите в систему и используйте страницу синхронизации (`/sync`)

## Требования

- Python 3.10+ (для запуска сервера)
- Веб-браузер (Chrome, Safari, Firefox)

## Поддержка

При возникновении проблем:
1. Проверьте логи в `~/MoneyTracker/logs/`
2. Убедитесь, что порт 5000 не занят
3. Проверьте firewall настройки
"""
    
    with open(pwa_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Создаем简易启动ные скрипты
    # Windows batch file
    batch_content = """@echo off
echo Starting MoneyTracker PWA Server...
echo.
echo After server starts, open browser and go to:
echo   http://localhost:5000
echo   or
echo   http://127.0.0.1:5000
echo.
echo To access from phone:
echo 1. Find your PC IP address (ipconfig)
echo 2. Open on phone: http://YOUR_IP:5000
echo.
python run_server.py
pause
"""
    
    with open(pwa_dir / "start_server.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    # Unix shell script
    shell_content = """#!/bin/bash
echo "Starting MoneyTracker PWA Server..."
echo ""
echo "After server starts, open browser and go to:"
echo "  http://localhost:5000"
echo "  or"
echo "  http://127.0.0.1:5000"
echo ""
echo "To access from phone:"
echo "1. Find your PC IP address (ifconfig)"
echo "2. Open on phone: http://YOUR_IP:5000"
echo ""
python3 run_server.py
"""
    
    shell_script = pwa_dir / "start_server.sh"
    with open(shell_script, "w", encoding="utf-8") as f:
        f.write(shell_content)
    shell_script.chmod(0o755)
    
    # Архивируем PWA пакет
    shutil.make_archive(
        BUILD_DIR / "MoneyTracker_PWA",
        "zip",
        BUILD_DIR,
        "PWA"
    )
    
    print(f"\nPWA package created: {BUILD_DIR / 'MoneyTracker_PWA.zip'}")
    return True

def create_apk_wrapper():
    """Создание обертки APK для Android"""
    print("\n" + "="*60)
    print("CREATING ANDROID APK WRAPPER")
    print("="*60)
    
    android_dir = BUILD_DIR / "Android"
    android_dir.mkdir(exist_ok=True)
    
    # Создаем структуру TWA (Trusted Web Activity)
    # Это самый простой способ упаковать PWA в APK
    
    twa_content = """{
  "name": "MoneyTracker",
  "packageId": "com.moneytracker.app",
  "webManifestUrl": "http://localhost:5000/static/manifest.json",
  "launcherName": "MoneyTracker",
  "defaultLocale": "ru",
  "icon": "ic_launcher.png",
  "splashScreenFadeoutDuration": 300,
  "themeColor": "#3b82f6",
  "backgroundColor": "#0a0e17",
  "enableNotifications": true,
  "isPlayBillingEnabled": false,
  "isLocationEnabled": false,
  "isContactSharingEnabled": false
}"""
    
    with open(android_dir / "twa-manifest.json", "w", encoding="utf-8") as f:
        f.write(twa_content)
    
    # Инструкции по созданию APK
    instructions = """# MoneyTracker Android APK

## Способ 1: Использование PWA Builder (Онлайн)

1. Перейдите на https://www.pwabuilder.com/
2. Введите URL вашего сервера (например: https://yourdomain.com)
3. Нажмите "Package for stores"
4. Выберите "Android"
5. Скачайте APK

## Способ 2: Использование Bubblewrap (Командная строка)

### Установка:
```bash
npm install -g @aspect-build/aspect-cli
npm install -g @nickvdh/nicern
```

### Создание APK:
```bash
twa-manifest-parser ./twa-manifest.json | bubblewrap init
bubblewrap build
```

## Способ 3: Использование Capacitor

### Установка:
```bash
npm install @capacitor/core @capacitor/cli
npm install @capacitor/android
```

### Настройка:
```javascript
// capacitor.config.json
{
  "appId": "com.moneytracker.app",
  "appName": "MoneyTracker",
  "webDir": "www",
  "server": {
    "url": "http://YOUR_SERVER:5000",
    "cleartext": true
  }
}
```

### Сборка:
```bash
npx cap add android
npx cap sync
npx cap open android
```

Затем в Android Studio: Build → Generate Signed Bundle/APK

## Способ 4: Готовое решение APK

1. Установите APK Builder: https://play.google.com/store/apps/details?id=com.theapkbuilder.app
2. Введите URL вашего PWA
3. Сгенерируйте APK

## Установка APK на телефон

### Через USB:
1. Подключите телефон к ПК
2. Включите "Отладку по USB" в настройках разработчика
3. Скопируйте APK на телефон
4. Установите APK

### Через облако:
1. Загрузите APK в Google Drive
2. Откройте на телефоне
3. Установите APK

## Требования

- Сервер должен быть доступен по HTTP/HTTPS
- Для публикации в Google Play нужна подпись APK
"""
    
    with open(android_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(instructions)
    
    print(f"\nAndroid wrapper created: {android_dir}")
    return True

def main():
    """Основная функция"""
    print("="*60)
    print("MoneyTracker - Multi-Platform Build Tool")
    print("="*60)
    print(f"Build directory: {BUILD_DIR}")
    print(f"Output directory: {DIST_DIR}")
    
    # Очистка
    clean_build_dirs()
    
    results = {
        "Windows EXE": False,
        "PWA Package": False,
        "Android Wrapper": False
    }
    
    # Сборка Windows EXE
    try:
        results["Windows EXE"] = build_windows_exe()
    except Exception as e:
        print(f"Windows build failed: {e}")
    
    # Создание PWA пакета
    try:
        results["PWA Package"] = create_pwa_package()
    except Exception as e:
        print(f"PWA package creation failed: {e}")
    
    # Создание Android обертки
    try:
        results["Android Wrapper"] = create_apk_wrapper()
    except Exception as e:
        print(f"Android wrapper creation failed: {e}")
    
    # Итоги
    print("\n" + "="*60)
    print("BUILD SUMMARY")
    print("="*60)
    
    for platform, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{platform}: {status}")
    
    print("\n" + "="*60)
    print("OUTPUT FILES")
    print("="*60)
    
    # Список созданных файлов
    for item in BUILD_DIR.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(BUILD_DIR)
            size = item.stat().st_size
            size_str = f"{size/1024/1024:.1f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            print(f"  {rel_path} ({size_str})")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    
    print("""
1. WINDOWS:
   - Run: build_output/MoneyTracker_Windows.exe
   - Or use PWA: Extract PWA zip and run start_server.bat

2. ANDROID:
   - Use PWA Builder (https://pwabuilder.com)
   - Or extract Android wrapper for Capacitor setup

3. iOS:
   - Use Safari to install PWA from your server
   - Follow instructions in PWA README.md

4. ALL PLATFORMS:
   - Start server: python run_server.py
   - Access from any device on same network
   - Use /sync page for data synchronization
""")

if __name__ == "__main__":
    main()