import os
import sys
import logging
import json
import shutil
import platform
import ctypes
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
    
    def __init__(self, app_name_id):
        self.app_id = app_name_id
        self.shared_memory = QSharedMemory(self.app_id)
        
    def check_single_instance(self):
        """
        Проверяет, не запущено ли уже приложение.
        Использует QSharedMemory.
        Возвращает True, если это единственный экземпляр.
        """
        # Пытаемся подключиться к сегменту памяти. 
        # Если удалось - значит приложение уже запущено.
        if self.shared_memory.attach():
            # На всякий случай проверяем, не пустой ли это сегмент
            # (но в Qt если attach вернул True, значит сегмент есть)
            return False
            
        # Если не удалось прикрепиться - пробуем создать.
        if not self.shared_memory.create(1):
            # Если не удалось создать, это может быть из-за того, что сегмент уже существует
            # (ошибка AlreadyExists), но attach выше не сработал.
            # Это типичный "зомби" сегмент от краша.
            error = self.shared_memory.error()
            
            # В PyQt6 ошибки могут быть в QSharedMemory.SharedMemoryError
            # Пробуем проверить на AlreadyExists
            if error == QSharedMemory.SharedMemoryError.AlreadyExists:
                # Пробуем прикрепиться еще раз, вдруг состояние изменилось
                if self.shared_memory.attach():
                    return False
                
                # Если все еще не можем прикрепиться, но create говорит, что сегмент есть - 
                # это зомби-сегмент. Разрешаем запуск, т.к. реального процесса нет.
                logger.warning("Found zombie shared memory segment. Bypassing lock.")
                return True
                
            logger.error(f"Unable to create single instance lock: {self.shared_memory.errorString()} (Error code: {error})")
            # Если это какая-то другая ошибка (например, доступ запрещен), 
            # всё равно лучше разрешить запуск, чем блокировать пользователя навсегда.
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

