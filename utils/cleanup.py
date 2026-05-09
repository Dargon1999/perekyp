import os 
import shutil 
import glob 
import ctypes 
import sys 
import logging
from datetime import datetime

# WinAPI Constants
MOVEFILE_DELAY_UNTIL_REBOOT = 0x00000004
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

def is_admin(): 
    """Проверка, запущен ли скрипт от имени администратора.""" 
    try: 
        return ctypes.windll.shell32.IsUserAnAdmin() 
    except: 
        return False 
 
def clean_temp(log_callback=None): 
    """Очистка временных папок пользователя и системы с возвратом статистики.""" 
    temp_user = os.environ.get("TEMP") 
    system_root = os.environ.get("SystemRoot", "C:\\Windows") 
    temp_system = os.path.join(system_root, "TEMP") 
    prefetch = os.path.join(system_root, "Prefetch")
    
    # Расширенные пути (Requirement 8)
    local_app_data = os.environ.get("LOCALAPPDATA")
    app_data = os.environ.get("APPDATA")
    
    # Кэш браузеров (Chrome, Edge)
    chrome_cache = os.path.join(local_app_data, "Google", "Chrome", "User Data", "Default", "Cache", "**", "*")
    edge_cache = os.path.join(local_app_data, "Microsoft", "Edge", "User Data", "Default", "Cache", "**", "*")
    
    # Системные логи и кэш обновлений
    win_logs = os.path.join(system_root, "Logs", "**", "*")
    win_update_cache = os.path.join(system_root, "SoftwareDistribution", "Download", "**", "*")
 
    logging.info("Запуск расширенной очистки временных файлов") 
    if log_callback: log_callback("--- Запуск расширенной очистки временных файлов ---")
    
    total_freed = 0
    total_errors = 0
    total_locked = 0
    total_files = 0
     
    targets = [
        (os.path.join(temp_user, "**", "*"), "User TEMP"),
        (os.path.join(temp_system, "**", "*"), "System TEMP"),
        (os.path.join(prefetch, "**", "*"), "Prefetch"),
        (chrome_cache, "Chrome Cache"),
        (edge_cache, "Edge Cache"),
        (win_logs, "Windows Logs"),
        (win_update_cache, "Windows Update Cache")
    ]

    for pattern, name in targets:
        if log_callback: log_callback(f"Обработка {name}...")
        f, e, l = safe_remove(pattern, log_callback)
        total_freed += f
        total_errors += e
        total_locked += l
        
    return total_freed, total_errors, total_locked

def safe_remove(path_pattern, log_callback=None): 
    """Безопасное удаление файлов и папок по шаблону с расширенной логикой.""" 
    freed = 0
    errors = 0
    locked = 0
    count = 0
    
    # Список исключений для безопасности (Requirement 8)
    critical_exclusions = [
        "System32", "SysWOW64", "WinSxS", "drivers", "config"
    ]
    
    # Используем glob для поиска всех файлов и папок, включая скрытые 
    for path in glob.glob(path_pattern, recursive=True): 
        try: 
            if not os.path.exists(path): continue
            
            # Проверка исключений (безопасность)
            if any(exc in path for exc in critical_exclusions):
                continue
                
            size = 0
            if os.path.isfile(path) or os.path.islink(path): 
                size = os.path.getsize(path)
                os.remove(path) 
                freed += size
                count += 1
                msg = f"Удален файл: {path}"
            elif os.path.isdir(path): 
                shutil.rmtree(path, ignore_errors=False) 
                msg = f"Удалена папка: {path}"
            
            if log_callback: log_callback(msg)
            logging.info(msg)

        except (PermissionError, OSError):
            # Попытка пометить файл для удаления после перезагрузки (Windows)
            if sys.platform == "win32":
                res = kernel32.MoveFileExW(str(path), None, MOVEFILE_DELAY_UNTIL_REBOOT)
                if res:
                    locked += 1
                    msg = f"Заблокирован, помечен для удаления при перезагрузке: {path}"
                else:
                    errors += 1
                    msg = f"Ошибка доступа: {path}"
            else:
                errors += 1
                msg = f"Нет доступа: {path}"
            
            if log_callback: log_callback(msg)
            logging.warning(msg)
        except Exception as e: 
            errors += 1
            msg = f"Ошибка при удалении {path}: {e}"
            if log_callback: log_callback(msg)
            logging.error(msg)
            
    return freed, errors, locked, count

def clean_temp(log_callback=None): 
    """Очистка временных папок пользователя и системы с возвратом статистики.""" 
    import tempfile
    
    # --- Улучшенная логика очистки (Вариант из рекомендаций) ---
    logging.info("Запуск расширенной очистки временных файлов") 
    if log_callback: log_callback("--- Запуск расширенной очистки временных файлов ---")
    
    total_freed = 0
    total_errors = 0
    total_locked = 0
    total_files = 0
    
    # Основные директории
    temp_dirs = [tempfile.gettempdir()]
    
    # Добавляем системные пути, если есть права админа
    system_root = os.environ.get("SystemRoot", "C:\\Windows") 
    temp_system = os.path.join(system_root, "TEMP") 
    if os.path.exists(temp_system):
        temp_dirs.append(temp_system)
        
    # Расширенные пути (Requirement F8)
    local_app_data = os.environ.get("LOCALAPPDATA")
    app_data = os.environ.get("APPDATA")
    
    # Кэш браузеров (Chrome, Edge, Firefox, Yandex)
    browser_targets = []
    if local_app_data:
        browser_targets.extend([
            (os.path.join(local_app_data, "Google", "Chrome", "User Data", "Default", "Cache"), "Chrome Cache"),
            (os.path.join(local_app_data, "Microsoft", "Edge", "User Data", "Default", "Cache"), "Edge Cache"),
            (os.path.join(local_app_data, "Yandex", "YandexBrowser", "User Data", "Default", "Cache"), "Yandex Cache"),
        ])
    if app_data:
        browser_targets.append((os.path.join(app_data, "Mozilla", "Firefox", "Profiles"), "Firefox Profiles"))

    targets = [
        (temp_user, "User TEMP"),
        (temp_system, "System TEMP"),
        (prefetch, "Prefetch"),
    ] + browser_targets

    for base_dir, name in targets:
        if not os.path.exists(base_dir): continue
        if log_callback: log_callback(f"Обработка {name}...")
        
        for root, dirs, files in os.walk(base_dir, topdown=False):
            # Files
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    if not os.path.exists(fpath): continue
                    size = os.path.getsize(fpath)
                    os.remove(fpath)
                    total_freed += size
                    total_files += 1
                except:
                    total_errors += 1
            # Dirs
            for dname in dirs:
                dpath = os.path.join(root, dname)
                try:
                    shutil.rmtree(dpath, ignore_errors=True)
                except: pass
        
    return total_freed, total_errors, total_locked, total_files

def empty_recycle_bin(log_callback=None): 
    """Очистка корзины через Windows API.""" 
    if log_callback: log_callback("--- Очистка корзины ---")
    logging.info("Очистка корзины")
     
    try: 
        # Флаги: SHERB_NOCONFIRMATION (1) | SHERB_NOPROGRESSUI (2) | SHERB_NOSOUND (4) 
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 1 | 2 | 4) 
        if log_callback: log_callback("Корзина успешно очищена.")
        return True
    except Exception as e: 
        msg = f"Ошибка API корзины: {e}"
        if log_callback: log_callback(msg)
        logging.error(msg)
        return False
 
if __name__ == "__main__": 
    if is_admin(): 
        clean_temp() 
        empty_recycle_bin() 
        print("\nОчистка завершена.") 
    else: 
        # Перезапуск скрипта с правами администратора 
        print("Запрос прав администратора...") 
        params = " ".join([f'"{arg}"' for arg in sys.argv]) 
        try: 
            # runas - это глагол для вызова UAC 
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}" {params}', None, 1) 
        except Exception as e: 
            print(f"Не удалось получить права администратора: {e}") 
            sys.exit(1)
