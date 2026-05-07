import PyInstaller.__main__
import os
import sys
import shutil

# Путь к основному файлу приложения
main_script = "main.py"
hotkey_script = "mem_reduct_hotkeys.py"

# Название выходного файла
app_name = "MoneyTracker"
hotkey_app_name = "mem_reduct"

# Сначала собираем updater.exe если его нет
updater_src = "dist/updater.exe"
mem_reduct_src = "dist/mem_reduct.exe"

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

# Собираем mem_reduct.exe
print("Building mem_reduct.exe...")
mem_reduct_params = [
    hotkey_script,
    "--name", hotkey_app_name,
    "--onefile",
    "--noconsole",
    "--clean",
]
if os.path.exists("icon.ico"):
    mem_reduct_params.extend(["--icon", "icon.ico"])

PyInstaller.__main__.run(mem_reduct_params)
print("mem_reduct.exe built.")

# Сборка списка ресурсов (иконки, ассеты)
# Формат: (путь_в_проекте, путь_в_exe)
added_data = [
    ("gui/assets", "gui/assets"),
    ("data.json", "."),
]

# Добавляем бинарные файлы (они будут доступны в _MEIPASS)
if os.path.exists(updater_src):
    added_data.append((updater_src, "."))
if os.path.exists(mem_reduct_src):
    added_data.append((mem_reduct_src, "."))

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

# Копируем updater.exe рядом с MoneyTracker.exe для удобства распространения
if os.path.exists(updater_src):
    print(f"Files in dist/:")
    for f in os.listdir("dist"):
        print(f"  - {f}")
    print(f"updater.exe is at: {os.path.abspath(updater_src)}")
    print(f"mem_reduct.exe is at: {os.path.abspath(mem_reduct_src)}")
    print(f"MoneyTracker.exe is at: {os.path.abspath('dist/MoneyTracker.exe')}")
else:
    print("WARNING: updater.exe not found in dist/!")
