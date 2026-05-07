import os
import platform
import hashlib
import logging
import ctypes
import subprocess
import shutil
import glob
import time
import psutil
import gc
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QMessageBox, QFrame, QScrollArea, QFileDialog, QProgressBar, QTextEdit,
    QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread

# --- WinAPI Helpers for Memory Cleaning (Windows Only) ---
kernel32 = None
ntdll = None
psapi = None
advapi32 = None

if platform.system() == "Windows":
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    except Exception as e:
        logging.error(f"Failed to load WinAPI DLLs: {e}")

# Flags for MoveFileEx
MOVEFILE_DELAY_UNTIL_REBOOT = 0x04
MOVEFILE_REPLACE_EXISTING = 0x01

class MemoryCommand:
    FlushModifiedList = 2
    PurgeStandbyList = 3
    PurgeLowPriorityStandbyList = 4
    MemoryCombinePages = 12

SystemMemoryListInformation = 80

class MLI(ctypes.Structure):
    _fields_ = [
        ("ZeroPageCount", ctypes.c_size_t),
        ("FreePageCount", ctypes.c_size_t),
        ("ModifiedPageCount", ctypes.c_size_t),
        ("ModifiedNoWritePageCount", ctypes.c_size_t),
        ("BadPageCount", ctypes.c_size_t),
        ("PageCountByPriority", ctypes.c_size_t * 8),
        ("RepurposedPageCountByPriority", ctypes.c_size_t * 8),
        ("ModifiedPageCountPageFile", ctypes.c_size_t),
    ]

def is_admin():
    if platform.system() != "Windows":
        return os.getuid() == 0
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def enable_privileges():
    if platform.system() != "Windows":
        return True
    try:
        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]
        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", ctypes.c_ulong)]
        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", ctypes.c_ulong), ("Privileges", LUID_AND_ATTRIBUTES * 1)]

        privs = ["SeDebugPrivilege", "SeIncreaseQuotaPrivilege", "SeProfileSingleProcessPrivilege"]
        hToken = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0020 | 0x0008, ctypes.byref(hToken)):
            return False

        for priv in privs:
            luid = LUID()
            if advapi32.LookupPrivilegeValueW(None, priv, ctypes.byref(luid)):
                tp = TOKEN_PRIVILEGES()
                tp.PrivilegeCount = 1
                tp.Privileges[0].Luid = luid
                tp.Privileges[0].Attributes = 0x00000002 
                advapi32.AdjustTokenPrivileges(hToken, False, ctypes.byref(tp), 0, None, None)
        kernel32.CloseHandle(hToken)
        return True
    except: return False

# --- Workers ---

class InternalMemWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished_data = pyqtSignal(dict)

    def run(self):
        try:
            self.log.emit("🚀 Запуск оптимизации памяти...")
            self.progress.emit(10)
            
            if platform.system() != "Windows":
                self.log.emit("ℹ️ Очистка памяти в Linux ограничена системным кэшем.")
                # Basic Linux cache clearing if root
                if os.getuid() == 0:
                    os.system("sync; echo 3 > /proc/sys/vm/drop_caches")
                    self.log.emit("✅ Системный кэш очищен.")
                gc.collect()
                self.progress.emit(100)
                self.finished_data.emit({"status": "success", "count": 0})
                return

            if not is_admin():
                self.log.emit("⚠️ Внимание: запуск без прав администратора. Очистка будет частичной.")
            
            enable_privileges()
            self.progress.emit(20)
            
            # 1. Trim Working Sets
            self.log.emit("📦 Очистка рабочих наборов процессов...")
            ACCESS = 0x1F0FFF
            count = 0
            all_procs = list(psutil.process_iter(['pid', 'name']))
            total = len(all_procs)
            
            for i, p in enumerate(all_procs):
                try:
                    if p.pid <= 4: continue
                    h = kernel32.OpenProcess(ACCESS, False, p.pid)
                    if h:
                        psapi.EmptyWorkingSet(h)
                        kernel32.CloseHandle(h)
                        count += 1
                except: pass
                
                if i % 10 == 0:
                    self.progress.emit(20 + int((i/total) * 30))

            self.log.emit(f"✅ Очищено рабочих наборов: {count}")
            self.progress.emit(60)

            # 2. NT Set System Info commands
            if ntdll:
                self.log.emit("🧹 Сброс списков измененных страниц...")
                val = ctypes.c_ulong(MemoryCommand.FlushModifiedList)
                ntdll.NtSetSystemInformation(SystemMemoryListInformation, ctypes.byref(val), ctypes.sizeof(val))
                
                # 3. Purge Standby Lists
                self.log.emit("♻️ Очистка списков ожидания (Standby)...")
                for _ in range(3):
                    val = ctypes.c_ulong(MemoryCommand.PurgeStandbyList)
                    ntdll.NtSetSystemInformation(SystemMemoryListInformation, ctypes.byref(val), ctypes.sizeof(val))
                    val = ctypes.c_ulong(MemoryCommand.PurgeLowPriorityStandbyList)
                    ntdll.NtSetSystemInformation(SystemMemoryListInformation, ctypes.byref(val), ctypes.sizeof(val))
                    time.sleep(0.05)
                self.progress.emit(80)

                # 4. Combine Pages
                self.log.emit("🧩 Дефрагментация страниц памяти...")
                val = ctypes.c_ulong(MemoryCommand.MemoryCombinePages)
                ntdll.NtSetSystemInformation(SystemMemoryListInformation, ctypes.byref(val), ctypes.sizeof(val))
            
            gc.collect()
            self.progress.emit(100)
            
            msg = "✨ Оптимизация памяти завершена успешно!"
            self.log.emit(msg)
            logging.info(msg)
            self.finished_data.emit({"status": "success", "count": count})
            
        except Exception as e:
            err_msg = f"❌ Ошибка при очистке памяти: {str(e)}"
            self.log.emit(err_msg)
            logging.error(err_msg)
            self.finished_data.emit({"status": "error", "msg": str(e)})

import tempfile

class InternalTempWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished_data = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            from utils.cleanup import clean_temp, empty_recycle_bin
            
            self.log.emit("🔍 Запуск глубокого сканирования и очистки...")
            self.progress.emit(10)
            
            # 1. Clean Temp & Cache (Requirement 8: Expanded targets)
            freed, errors, locked, count = clean_temp(log_callback=self.log.emit)
            self.progress.emit(60)
            
            # 2. Recycle Bin
            empty_recycle_bin(log_callback=self.log.emit)
            self.progress.emit(90)
            
            freed_mb = freed / (1024 * 1024)
            summary = (f"✨ Очистка завершена!\n"
                       f"📊 Удалено файлов: {count}\n"
                       f"💾 Освобождено: {freed_mb:.2f} МБ\n"
                       f"❗ Ошибок: {errors} | 🔒 Заблокировано: {locked}")
            
            self.log.emit(summary)
            self.progress.emit(100)
            self.finished_data.emit({
                "status": "success", 
                "freed_mb": freed_mb, 
                "file_count": count,
                "errors": errors, 
                "locked": locked
            })
            
        except Exception as e:
            err_msg = f"❌ Критическая ошибка при очистке: {str(e)}"
            self.log.emit(err_msg)
            logging.error(err_msg)
            self.finished_data.emit({"status": "error", "msg": str(e)})

    def _deep_clean(self, directory):
        freed = 0
        errors = 0
        locked = 0
        
        try:
            for root, dirs, files in os.walk(directory, topdown=False):
                if self._is_cancelled: break

                for name in files:
                    if self._is_cancelled: break
                    file_path = os.path.join(root, name)
                    try:
                        if not os.path.exists(file_path): continue
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        freed += size
                    except (PermissionError, OSError):
                        if platform.system() == "Windows":
                            res = kernel32.MoveFileExW(file_path, None, MOVEFILE_DELAY_UNTIL_REBOOT)
                            if res: locked += 1
                            else: errors += 1
                        else:
                            errors += 1
                    except Exception:
                        errors += 1
                
                for name in dirs:
                    if self._is_cancelled: break
                    dir_path = os.path.join(root, name)
                    try:
                        shutil.rmtree(dir_path, ignore_errors=False)
                    except:
                        pass
        except Exception:
            errors += 1
            
        return freed, errors, locked

# --- Main Widgets ---

class UtilityWidget(QWidget):
    def __init__(self, name, hotkey, data_manager, security_manager):
        super().__init__()
        self.utility_name = name
        self.hotkey = hotkey
        self.data_manager = data_manager
        self.security_manager = security_manager
        self.worker = None
        
        self.init_ui()
        
        # NOTE: Global hotkeys are now handled by utils/background_hotkeys.py
        # to ensure they work even when MoneyTracker is minimized or in the background.

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title_lbl = QLabel(self.utility_name)
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #3b82f6;")
        header_layout.addWidget(title_lbl)
        
        status_badge = QLabel("ВСТРОЕННЫЙ")
        status_badge.setStyleSheet("background: #10b981; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;")
        header_layout.addWidget(status_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc_lbl = QLabel(f"активация горя клавиш {self.hotkey.lower()}")
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(desc_lbl)

        # Path selection UI for F7 has been removed (Requirement 4: hardcoded path)
        # The path is now fixed in utils/mem_reduct_launcher.py

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #334155; border-radius: 7px; background: #0f172a; text-align: center; color: transparent; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2dd4bf); border-radius: 7px; }
        """)
        layout.addWidget(self.progress_bar)

        # Logs
        layout.addWidget(QLabel("Журнал операций:"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 8px; font-family: Consolas; font-size: 11px;")
        layout.addWidget(self.log_view)

        # Actions
        self.run_btn = QPushButton(f"Запустить очистку ({self.hotkey})")
        self.run_btn.setFixedHeight(45)
        self.run_btn.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #334155; color: #94a3b8; }
        """)
        self.run_btn.clicked.connect(self.run_utility)
        layout.addWidget(self.run_btn)

    def browse_main_app(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите исполняемый файл",
            os.getcwd(),
            "Executables (*.exe *.py *.bat *.cmd);;All Files (*)"
        )
        if file_path:
            self.main_app_path_input.setText(file_path)
            self.data_manager.set_setting("main_app_path", file_path)

    def append_log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"[{timestamp}] {msg}")
        # Auto scroll to bottom
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def run_utility(self):
        if self.worker and self.worker.isRunning():
            return

        self.run_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_view.clear()
        
        self.worker = self.create_worker()
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.append_log)
        self.worker.finished_data.connect(self.on_finished)
        self.worker.start()

    def create_worker(self):
        raise NotImplementedError

    def on_finished(self, data):
        self.run_btn.setEnabled(True)
        self.log_execution(data)

    def log_execution(self, data):
        user = os.getlogin()
        status = data.get("status", "unknown")
        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] USER: {user} | MODULE: {self.utility_name} | STATUS: {status}"
        logging.info(log_msg)

class MemUtilityWidget(UtilityWidget):
    def __init__(self, data_manager, security_manager):
        super().__init__("Модуль для очистки RAM", "F7", data_manager, security_manager)
        
        # Add Hotkey Configuration
        self.setup_hotkey_ui()
        
        # Update run button text
        self.update_run_button_text()

    def setup_hotkey_ui(self):
        # Hotkey selection row
        hotkey_layout = QHBoxLayout()
        hotkey_layout.addWidget(QLabel("Клавиша запуска:"))
        
        self.hotkey_combo = QComboBox()
        # Common F-keys and others
        keys = [f"F{i}" for i in range(1, 13)] + ["Home", "End", "Insert", "Delete"]
        self.hotkey_combo.addItems(keys)
        
        # Load current hotkey
        current_hotkey = self.data_manager.get_setting("mem_cleanup_hotkey", "F7")
        idx = self.hotkey_combo.findText(current_hotkey)
        if idx >= 0:
            self.hotkey_combo.setCurrentIndex(idx)
        
        self.hotkey_combo.currentTextChanged.connect(self.on_hotkey_changed)
        hotkey_layout.addWidget(self.hotkey_combo)
        hotkey_layout.addStretch()
        
        # Insert before progress bar
        idx = self.layout().indexOf(self.progress_bar)
        self.layout().insertLayout(idx, hotkey_layout)

    def on_hotkey_changed(self, new_key):
        old_key = self.data_manager.get_setting("mem_cleanup_hotkey", "F7")
        if old_key == new_key:
            return
            
        self.data_manager.set_setting("mem_cleanup_hotkey", new_key)
        self.data_manager.save_data()
        
        # Update hotkey manager
        from utils.hotkey_manager import HotkeyManager
        h_mgr = HotkeyManager()
        h_mgr.update_hotkey(old_key, new_key, "mem_cleanup")
        
        # Update UI
        self.update_run_button_text()
        self.append_log(f"Горячая клавиша изменена на {new_key}")

    def update_run_button_text(self):
        current_key = self.data_manager.get_setting("mem_cleanup_hotkey", "F7")
        self.run_btn.setText(f"Запустить программу или нажмите {current_key} для запуска")

    def create_worker(self):
        return InternalMemWorker()

    def on_finished(self, data):
        self.run_btn.setEnabled(True)
        self.log_execution(data)
        
        # Launch external application after cleanup (Requirement 2 & 4)
        from utils.mem_reduct_launcher import launch_embedded_mem_reduct
        launch_embedded_mem_reduct()

class TempUtilityWidget(UtilityWidget):
    def __init__(self, data_manager, security_manager):
        super().__init__("Очистка TEMP", "F8", data_manager, security_manager)
        # Уточняем текст кнопки
        self.run_btn.setText("Запустить очистку файлов или нажмите F8")

    def create_worker(self):
        return InternalTempWorker()
