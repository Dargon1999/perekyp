import os
import sys
import logging
import json
import shutil
import platform
import ctypes
import subprocess
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QSharedMemory
from version import VERSION

# Создадим логгер для StartupManager
logger = logging.getLogger("StartupManager")

class StartupManager:
    """
    Отвечает за предварительные проверки перед запуском основного приложения:
    - Проверка на повторный запуск (Single Instance)
    - Проверка прав на запись в директории
    - Проверка целостности версии и файлов
    """
    
    # Store mutex globally within the class to prevent GC
    _win_mutex = None

    def __init__(self, app_name_id):
        self.app_id = app_name_id
        self.shared_memory = QSharedMemory(self.app_id)
        
    def check_single_instance(self):
        """
        Проверяет, не запущено ли уже приложение.
        На Windows использует Mutex для большей надежности.
        """
        if platform.system() == "Windows":
            try:
                # Используем именованный Mutex для Windows
                # Это более надежно, чем QSharedMemory при крашах
                # Важно: Mutex должен быть уникальным для версии, если мы допускаем разные версии,
                # или общим, если хотим только ОДНУ копию программы вообще.
                # Пользователь жалуется на ДВОЙНОЙ запуск при ОДНОМ клике, 
                # значит нам нужно жесткое ограничение.
                
                # Очищаем APP_ID от версии для глобальной блокировки всех версий (если нужно)
                # Или оставляем как есть для блокировки конкретной версии.
                # В данном случае APP_ID уже включает версию.
                
                StartupManager._win_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, self.app_id)
                error = ctypes.windll.kernel32.GetLastError()
                
                if error == 183: # ERROR_ALREADY_EXISTS
                    if StartupManager._win_mutex:
                        ctypes.windll.kernel32.CloseHandle(StartupManager._win_mutex)
                        StartupManager._win_mutex = None
                    return False
                return True
            except Exception as e:
                logger.error(f"Windows Mutex check failed: {e}")
        
        # Кроссплатформенный (или fallback) метод через QSharedMemory
        if self.shared_memory.attach():
            return False
            
        if not self.shared_memory.create(1):
            error = self.shared_memory.error()
            if error == QSharedMemory.SharedMemoryError.AlreadyExists:
                if self.shared_memory.attach():
                    return False
                logger.warning("Found zombie shared memory segment. Bypassing lock.")
                return True
                
            logger.error(f"Unable to create single instance lock: {self.shared_memory.errorString()} (Error code: {error})")
            return True
            
        return True

    def check_write_permissions(self, paths):
        """
        Проверяет права на запись в критические директории.
        paths: список путей для проверки
        """
        missing_perms = []
        for path in paths:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except OSError:
                    missing_perms.append(path)
                    continue
            
            if not os.access(path, os.W_OK):
                missing_perms.append(path)
                
        if missing_perms:
            msg = f"Нет прав на запись в следующие папки:\n" + "\n".join(missing_perms)
            logger.critical(msg)
            self._show_error("Ошибка доступа", msg)
            return False
        return True

    def validate_version_integrity(self):
        """
        Проверяет соответствие версии в коде и возможных метаданных.
        """
        # Пока просто логируем
        logger.info(f"Startup Version Check: {VERSION}")
        return True

    def check_system_requirements(self):
        """
        Минимальные системные требования (ОС, память и т.д.)
        """
        # Пример: Windows 10+
        if platform.system() == "Windows":
            try:
                version = platform.version().split('.')[0]
                if int(version) < 10:
                    logger.warning("Old Windows version detected.")
            except:
                pass
        return True

    def _show_error(self, title, message):
        # Используем ctypes для нативного MessageBox, т.к. Qt может быть еще не полностью готов
        # или чтобы не тянуть лишние зависимости, если StartupManager используется до Qt
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10) # 0x10 = MB_ICONERROR
        except:
            print(f"CRITICAL ERROR [{title}]: {message}")

    def setup_admin_autostart(self, enabled=True):
        """
        Настраивает автозапуск с правами администратора через Task Scheduler.
        Это позволяет запускать приложение без запроса UAC при старте системы.
        """
        if platform.system() != "Windows":
            return False

        task_name = f"MoneyTracker_AdminStart_{self.app_id}"
        
        # Windows-specific flags to hide console
        CREATE_NO_WINDOW = 0x08000000
        
        if not enabled:
            try:
                subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             creationflags=CREATE_NO_WINDOW)
                return True
            except:
                return False

        # Путь к текущему исполняемому файлу
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

        # Команда для создания задачи:
        try:
            cmd = ["schtasks", "/create", "/tn", task_name, "/tr", exe_path, "/sc", "onlogon", "/rl", "highest", "/f"]
            res = subprocess.run(cmd, 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL,
                               creationflags=CREATE_NO_WINDOW)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to setup admin autostart: {e}")
            return False

    @staticmethod
    def is_running_as_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def request_admin_restart(self):
        """Перезапускает приложение с правами администратора."""
        if self.is_running_as_admin():
            return True
            
        try:
            if getattr(sys, 'frozen', False):
                path = sys.executable
                params = ""
            else:
                path = sys.executable
                params = f'"{os.path.abspath(sys.argv[0])}"'
            
            # ShellExecuteW returns > 32 on success
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", path, params, None, 1)
            if int(ret) > 32:
                logger.info("Elevation request successful, exiting current process.")
                sys.exit(0)
            else:
                logger.error(f"Elevation request failed with error code: {ret}")
                return False
        except Exception as e:
            logger.error(f"Elevation request failed: {e}")
            return False

