import PyInstaller.__main__
import os
import sys

# Путь к основному файлу приложения
main_script = "main.py"

# Название выходного файла
app_name = "MoneyTracker"

# Сначала собираем updater.exe если его нет
updater_src = "dist/updater.exe"
updater_dest = "updater.exe"

# Проверяем и собираем updater если нужно
if not os.path.exists(updater_src):
    print("Building updater.exe first...")
    updater_params = [
        "updater.py",
        "--name", "updater",
        "--onefile",
        "--noconsole",
        "--clean",
    ]
    PyInstaller.__main__.run(updater_params)
    print("updater.exe built.")

# Сборка списка ресурсов (иконки, ассеты)
# Формат: (путь_в_проекте, путь_в_exe)
added_data = [
    ("gui/assets", "gui/assets"),
    ("data.json", "."),
    ("updater.py", "."), # Добавляем скрипт обновления
    ("dist/updater.exe", "."), # Включаем updater.exe рядом с MoneyTracker.exe
]

# Иконка для EXE (если есть .ico файл)
icon_file = "icon_v2.ico"
icon_param = []
if os.path.exists(icon_file):
    icon_param = ["--icon", icon_file]

# Параметры PyInstaller
params = [
    main_script,
    "--name", app_name,
    "--onefile",              # Собрать в один EXE файл
    "--noconsole",            # Не показывать консоль при запуске
    "--clean",                # Очистить кэш перед сборкой
    "--hidden-import=PyQt6.QtSvg",  # Добавляем модуль SVG рендеринга
]

# Добавляем данные
for src, dest in added_data:
    if os.path.exists(src):
        params.extend(["--add-data", f"{src}{os.pathsep}{dest}"])

# Добавляем иконку
params.extend(icon_param)

print(f"--- Starting build process for {app_name} ---")
PyInstaller.__main__.run(params)
print(f"--- Build finished! Check the 'dist' folder ---")
