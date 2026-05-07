@echo off
echo ========================================
echo MoneyTracker PWA - Windows Build Script
echo ========================================
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10 or higher.
    pause
    exit /b 1
)

REM Проверяем наличие PyInstaller
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Устанавливаем зависимости
echo Installing dependencies...
pip install -r requirements.txt
pip install flask flask-login flask-sqlalchemy flask-socketio pillow requests

REM Создаем иконку если её нет
if not exist "icon.ico" (
    echo Creating icon...
    python -c "from PIL import Image, ImageDraw; img = Image.new('RGBA', (256, 256), (10, 14, 23, 255)); draw = ImageDraw.Draw(img); draw.ellipse([20, 20, 236, 236], fill=(59, 130, 246, 255)); img.save('icon.ico', format='ICO', sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])"
)

REM Создаем version_info.txt если его нет
if not exist "version_info.txt" (
    echo Creating version_info.txt...
    (
        # UTF-8
        VSVersionInfo(
          ffi=FixedFileInfo(
            filevers=(9, 3, 0, 0),
            prodvers=(9, 3, 0, 0),
            mask=0x3f,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0)
            ),
          kids=[
            StringFileInfo(
              [
                StringTable(
                  u'040904B0',
                  [StringStruct(u'CompanyName', u'MoneyTracker'),
                   StringStruct(u'FileDescription', u'MoneyTracker - Finance Management'),
                   StringStruct(u'FileVersion', u'9.3.0.0'),
                   StringStruct(u'InternalName', u'MoneyTracker'),
                   StringStruct(u'LegalCopyright', u'Copyright (c) 2026'),
                   StringStruct(u'OriginalFilename', u'MoneyTracker.exe'),
                   StringStruct(u'ProductName', u'MoneyTracker'),
                   StringStruct(u'ProductVersion', u'9.3.0.0')])
              ]), 
            VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
          ]
        )
    ) > version_info.txt
)

REM Очищаем предыдущие сборки
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist\MoneyTracker" rmdir /s /q dist\MoneyTracker

REM Собираем EXE
echo.
echo Building MoneyTracker PWA Desktop...
echo.

pyinstaller --onefile --windowed ^
    --name MoneyTracker ^
    --icon icon.ico ^
    --version-file version_info.txt ^
    --add-data "web;web" ^
    --add-data "data_manager.py;." ^
    --add-data "database_manager.py;." ^
    --add-data "utils.py;." ^
    --add-data "version.py;." ^
    --add-data "event_bus.py;." ^
    --add-data "plugin_manager.py;." ^
    --hidden-import flask ^
    --hidden-import flask_login ^
    --hidden-import flask_sqlalchemy ^
    --hidden-import flask_socketio ^
    --hidden-import socketio ^
    --hidden-import engineio ^
    --hidden-import engineio.async_drivers.threading ^
    --hidden-import sqlalchemy ^
    --hidden-import sqlalchemy.orm ^
    --hidden-import PIL ^
    --hidden-import dns.resolver ^
    --hidden-import werkzeug ^
    --hidden-import jinja2 ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --noconsole ^
    launcher.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Output file: dist\MoneyTracker.exe
echo.
echo To distribute:
echo 1. Copy dist\MoneyTracker.exe to target PC
echo 2. Run MoneyTracker.exe
echo 3. App will start at http://localhost:5100
echo.
pause