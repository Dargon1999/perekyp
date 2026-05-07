import PyInstaller.__main__
import os

def build_updater():
    print("--- Building updater.exe ---")
    
    # Путь к иконке
    icon_path = "icon.ico"
    
    args = [
        'updater.py',           # Исходный файл
        '--onefile',            # В один файл
        '--windowed',           # Без консоли
        '--name=updater',       # Имя файла
        '--clean',              # Очистка кэша
    ]
    
    if os.path.exists(icon_path):
        args.append(f'--icon={icon_path}')
        
    PyInstaller.__main__.run(args)
    print("--- Updater build finished! ---")

if __name__ == "__main__":
    build_updater()
