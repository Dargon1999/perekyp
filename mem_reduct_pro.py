#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mem Reduct Pro - Aggressive Memory Optimizer
"""

import ctypes
import ctypes.wintypes
import sys
import time
import gc
import threading
import logging
import json
import os
import platform
import winreg
import subprocess
import shutil
import glob
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import psutil
from PIL import Image, ImageDraw
import pystray

# === CONFIGURATION ===
if getattr(sys, 'frozen', False):
    # Running as bundle (PyInstaller)
    BASE_DIR = Path(sys.executable).parent
    BUNDLE_DIR = Path(sys._MEIPASS)
else:
    # Running as script
    BASE_DIR = Path(__file__).parent
    BUNDLE_DIR = BASE_DIR

CONFIG_FILE = BASE_DIR / "mem_reduct_config.json"

DEFAULT_CONFIG = {
    "auto_clean_enabled": False,
    "auto_clean_threshold": 80,
    "autostart": False,
    "minimize_to_tray": True,
    "show_notifications": True,
    "show_charts": True,
    "interactive_procs": True,
    "hotkey_enabled": True,
    "hotkey_key": "F7",
    "cleanup_threads": 4,
    "cleanup_buffer_mb": 64,
    "cleanup_dirs": [
        os.environ.get('TEMP', ''), 
        os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
    ]
}

class Config:
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        self.load()
    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.data.update(json.load(f))
            except: pass
    def save(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except: pass

config = Config()

# === NATIVE CORE LOADER ===
native_core = None
DLL_PATH = BASE_DIR / "mem_reduct_core.dll"

def compile_and_load_dll():
    global native_core
    if not DLL_PATH.exists():
        bat_file = BASE_DIR / "compile_core.bat"
        if bat_file.exists():
            try:
                subprocess.run([str(bat_file)], check=True, capture_output=True, cwd=str(BASE_DIR), shell=True)
            except: pass
    
    if DLL_PATH.exists():
        try:
            native_core = ctypes.CDLL(str(DLL_PATH))
            native_core.InitializeCore.restype = ctypes.c_bool
            if native_core.InitializeCore():
                # Define argtypes for safety
                native_core.StartParallelFileCleanup.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_int]
                native_core.GetCleanupProgress.argtypes = [
                    ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_longlong),
                    ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_longlong),
                    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_longlong)
                ]
                return True
        except: pass
    return False

# === LOGGING ===
LOG_FILE = BASE_DIR / "mem_reduct.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MemReductPro")

def log_action(msg):
    logger.info(msg)

# === FILE CLEANUP MANAGER ===
class FileCleanupManager:
    def __init__(self):
        self.patterns = {
            "User Temp": os.path.join(os.environ.get('TEMP', ''), "**", "*"),
            "System Temp": os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp', "**", "*"),
            "Prefetch": os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch', "**", "*"),
            "Recent Items": os.path.join(os.environ.get('AppData', ''), 'Microsoft', 'Windows', 'Recent', "**", "*"),
            "Windows Logs": os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Logs', "**", "*.log"),
            "Chrome Cache": os.path.join(os.environ.get('LocalAppData', ''), 'Google', 'Chrome', 'User Data', 'Default', 'Cache', "**", "*"),
            "Edge Cache": os.path.join(os.environ.get('LocalAppData', ''), 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache', "**", "*"),
            "Steam Cache": os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'Steam', 'appcache', "**", "*"),
            "Discord Cache": os.path.join(os.environ.get('AppData', ''), 'discord', 'Cache', "**", "*"),
            "Telegram Cache": os.path.join(os.environ.get('AppData', ''), 'Telegram Desktop', 'tdata', 'user_data', 'cache', "**", "*"),
        }
        self.found_files = [] # List of (path, size, category)
        self.backup_dir = BASE_DIR / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

    def scan(self, progress_callback=None):
        self.found_files = []
        total_categories = len(self.patterns)
        
        for i, (category, pattern) in enumerate(self.patterns.items()):
            if progress_callback:
                progress_callback(f"Сканирование: {category}...", i / total_categories)
            
            try:
                for path in glob.glob(pattern, recursive=True):
                    try:
                        if os.path.isfile(path) or os.path.islink(path):
                            size = os.path.getsize(path)
                            self.found_files.append({"path": path, "size": size, "category": category})
                    except (OSError, PermissionError):
                        continue
            except Exception as e:
                log_action(f"Scan error in {category}: {e}")
        
        if progress_callback:
            progress_callback("Сканирование завершено", 1.0)
        return self.found_files

    def cleanup(self, selected_files, progress_callback=None):
        """
        selected_files: list of dicts from self.found_files
        """
        total_removed = 0
        total_files = len(selected_files)
        
        # Create backup for critical categories if needed
        # For simplicity, we'll backup anything the user might consider "critical"
        # such as Recent Items or specific files if requested. 
        # But here we'll just follow the requirement: "создание резервной копии перед удалением критичных данных"
        critical_categories = ["Recent Items"]
        
        if any(f['category'] in critical_categories for f in selected_files):
            try:
                self.backup_dir.mkdir(parents=True, exist_ok=True)
                log_action(f"Backup directory created: {self.backup_dir}")
            except Exception as e:
                log_action(f"Failed to create backup dir: {e}")

        for i, file_info in enumerate(selected_files):
            path = file_info['path']
            category = file_info['category']
            size = file_info['size']
            
            if progress_callback:
                progress_callback(f"Удаление: {os.path.basename(path)}", i / total_files)
            
            try:
                # Backup if critical
                if category in critical_categories and self.backup_dir.exists():
                    # Create a safe relative path for backup
                    safe_path = path.replace(":", "").lstrip("\\").lstrip("/")
                    dest = self.backup_dir / safe_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)
                
                # Remove
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                    total_removed += size
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    if not os.path.exists(path):
                        total_removed += size
            except (OSError, PermissionError) as e:
                log_action(f"Skip (in use): {path}")
            except Exception as e:
                log_action(f"Error deleting {path}: {e}")
                
        if progress_callback:
            progress_callback("Очистка завершена", 1.0)
            
        return total_removed

# === WinAPI Definitions ===
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

# Hotkey Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

VK_CODES = {
    'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73, 'F5': 0x74, 'F6': 0x75,
    'F7': 0x76, 'F8': 0x77, 'F9': 0x78, 'F10': 0x79, 'F11': 0x7A, 'F12': 0x7B,
    'A': 0x41, 'B': 0x42, 'C': 0x43, 'D': 0x44, 'E': 0x45, 'F': 0x46, 'G': 0x47,
    'H': 0x48, 'I': 0x49, 'J': 0x4A, 'K': 0x4B, 'L': 0x4C, 'M': 0x4D, 'N': 0x4E,
    'O': 0x4F, 'P': 0x50, 'Q': 0x51, 'R': 0x52, 'S': 0x53, 'T': 0x54, 'U': 0x55,
    'V': 0x56, 'W': 0x57, 'X': 0x58, 'Y': 0x59, 'Z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35, '6': 0x36,
    '7': 0x37, '8': 0x38, '9': 0x39,
}

def get_vk_code(key_name):
    """Mapping for keys to virtual key codes."""
    return VK_CODES.get(key_name.upper(), 0x76) # Default F7 if not found

# Flags
QUOTA_LIMITS_HARDWS_MIN_DISABLE = 0x00000002
QUOTA_LIMITS_HARDWS_MAX_DISABLE = 0x00000008

# Standard SYSTEM_MEMORY_LIST_COMMAND (RAMMap 1:1)
class MemoryCommand:
    FlushModifiedList = 2
    PurgeStandbyList = 3
    PurgeLowPriorityStandbyList = 4
    MemoryCombinePages = 12 # defrag RAM

# NTAPI Classes
SystemMemoryListInformation = 80
SystemWorkingSetInformation = 1
SystemFileCacheInformation = 21

def is_admin():
    try: return shell32.IsUserAnAdmin()
    except: return False

def request_admin():
    if is_admin(): return True
    try:
        # Prefer pythonw.exe to avoid console window
        py_exe = sys.executable
        if py_exe.lower().endswith("python.exe"):
            pyw = py_exe.lower().replace("python.exe", "pythonw.exe")
            if os.path.exists(pyw):
                py_exe = pyw
        
        ret = shell32.ShellExecuteW(None, "runas", py_exe, f'"{__file__}"', None, 1)
        return ret > 32
    except: return False

class PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("CommitTotal", ctypes.c_size_t), ("CommitLimit", ctypes.c_size_t),
                ("CommitPeak", ctypes.c_size_t), ("PhysicalTotal", ctypes.c_size_t), ("PhysicalAvailable", ctypes.c_size_t),
                ("SystemCache", ctypes.c_size_t), ("KernelTotal", ctypes.c_size_t), ("KernelPaged", ctypes.c_size_t),
                ("KernelNonpaged", ctypes.c_size_t), ("PageSize", ctypes.c_size_t), ("HandleCount", ctypes.c_ulong),
                ("ProcessCount", ctypes.c_ulong), ("ThreadCount", ctypes.c_ulong)]

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

class SYSTEM_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("Reserved1", ctypes.c_ulong * 24), ("PageSize", ctypes.c_ulong), ("Reserved2", ctypes.c_ulong * 16)]

class SYSTEM_PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("IdleProcessTime", ctypes.c_longlong), ("IoReadTransferCount", ctypes.c_longlong),
        ("IoWriteTransferCount", ctypes.c_longlong), ("IoOtherTransferCount", ctypes.c_longlong),
        ("IoReadOperationCount", ctypes.c_ulong), ("IoWriteOperationCount", ctypes.c_ulong),
        ("IoOtherOperationCount", ctypes.c_ulong), ("AvailablePages", ctypes.c_ulong),
        ("CommittedPages", ctypes.c_ulong), ("CommitLimit", ctypes.c_ulong),
        ("PeakCommitment", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
        ("CopyOnWriteCount", ctypes.c_ulong), ("TransitionCount", ctypes.c_ulong),
        ("CacheTransitionCount", ctypes.c_ulong), ("DemandZeroCount", ctypes.c_ulong),
        ("PageReadCount", ctypes.c_ulong), ("PageReadIoCount", ctypes.c_ulong),
        ("CacheReadCount", ctypes.c_ulong), ("CacheReadIoCount", ctypes.c_ulong),
        ("PageWriteCount", ctypes.c_ulong), ("PageWriteIoCount", ctypes.c_ulong),
        ("MappedWriteCount", ctypes.c_ulong), ("MappedWriteIoCount", ctypes.c_ulong),
        ("PagedPoolPages", ctypes.c_ulong), ("NonPagedPoolPages", ctypes.c_ulong),
        ("PagedPoolAllocs", ctypes.c_ulong), ("PagedPoolFrees", ctypes.c_ulong),
        ("NonPagedPoolAllocs", ctypes.c_ulong), ("NonPagedPoolFrees", ctypes.c_ulong),
        ("FreeSystemPtes", ctypes.c_ulong), ("CachePages", ctypes.c_ulong),
        ("CachedLibraryPages", ctypes.c_ulong), ("PagedPoolPeak", ctypes.c_ulong),
        ("NonPagedPoolPeak", ctypes.c_ulong), ("SystemCodePage", ctypes.c_ulong),
        ("SystemDataPage", ctypes.c_ulong), ("SystemCachePage", ctypes.c_ulong),
        ("PagedPoolSafeLimit", ctypes.c_ulong), ("NonPagedPoolSafeLimit", ctypes.c_ulong),
    ]

def enable_privileges():
    """Enable system privileges for deep memory access."""
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
                tp.Privileges[0].Attributes = 0x00000002 # SE_PRIVILEGE_ENABLED
                advapi32.AdjustTokenPrivileges(hToken, False, ctypes.byref(tp), 0, None, None)
                
        kernel32.CloseHandle(hToken)
        return True
    except: return False

def nt_call(cmd_val, info_class=SystemMemoryListInformation):
    val = ctypes.c_ulong(cmd_val)
    return ntdll.NtSetSystemInformation(info_class, ctypes.byref(val), ctypes.sizeof(val))

class Snap:
    def __init__(self, standby, modified):
        self.standby = standby
        self.modified = modified

def get_snapshot():
    """Captures the current state of system memory lists (RAMMap-accurate)."""
    m = MLI()
    status = ntdll.NtQuerySystemInformation(SystemMemoryListInformation, ctypes.byref(m), ctypes.sizeof(m), None)
    if status == 0:
        standby = sum(m.PageCountByPriority)
        modified = m.ModifiedPageCount + m.ModifiedNoWritePageCount
        return Snap(standby, modified)
    return Snap(0, 0)

def get_detailed_accounting():
    """Returns accurate RAMMap-style accounting info."""
    perf = SYSTEM_PERFORMANCE_INFORMATION()
    ntdll.NtQuerySystemInformation(2, ctypes.byref(perf), ctypes.sizeof(perf), None)
    
    basic = SYSTEM_BASIC_INFORMATION()
    ntdll.NtQuerySystemInformation(0, ctypes.byref(basic), ctypes.sizeof(basic), None)
    page_size = basic.PageSize if basic.PageSize > 0 else 4096
    
    m = MLI()
    ntdll.NtQuerySystemInformation(SystemMemoryListInformation, ctypes.byref(m), ctypes.sizeof(m), None)
    
    standby = sum(m.PageCountByPriority) * page_size
    modified = (m.ModifiedPageCount + m.ModifiedNoWritePageCount) * page_size
    free = m.FreePageCount * page_size
    zero = m.ZeroPageCount * page_size
    
    return {
        "standby": standby,
        "modified": modified,
        "free": free,
        "zero": zero,
        "available": free + zero + standby,
        "page_size": page_size
    }

def trim_working_sets():
    """WORKING SET STORM: Aggressive trim of all user processes."""
    ACCESS = 0x1F0FFF  # full access (safe for trimming)
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if p.pid <= 4 or (p.info['name'] and p.info['name'].lower() in ["python.exe", "mem_reduct_v2.exe"]):
                continue
            h = kernel32.OpenProcess(ACCESS, False, p.pid)
            if h:
                psapi.EmptyWorkingSet(h)
                kernel32.CloseHandle(h)
        except: pass

def aggressive_clean_fallback():
    """🔥 RAMMap-like engine v1 (User-mode approximation)."""
    enable_privileges()
    
    # 0. SNAPSHOT BEFORE
    before = get_snapshot()
    log_action(f"ENGINE: RAMMap v1 Start. Standby: {before.standby}, Modified: {before.modified}")

    # 1. WORKING SET STORM
    trim_working_sets()

    # 2. FLUSH MODIFIED PAGES
    nt_call(MemoryCommand.FlushModifiedList)

    # 3. MULTI-PASS STANDBY PURGE (KEY RAMMAP BEHAVIOR)
    for _ in range(5):
        nt_call(MemoryCommand.PurgeStandbyList)
        nt_call(MemoryCommand.PurgeLowPriorityStandbyList)
        time.sleep(0.02)

    # 4. COMBINE PAGES (defrag RAM)
    nt_call(MemoryCommand.MemoryCombinePages)

    # 5. SECOND WAVE (IMPORTANT)
    for _ in range(3):
        nt_call(MemoryCommand.PurgeStandbyList)
        time.sleep(0.01)

    # 6. STABILIZATION LOOP (RAMMap key differentiator)
    for _ in range(10):
        time.sleep(0.05)
        nt_call(MemoryCommand.PurgeStandbyList)

    # 7. SNAPSHOT AFTER
    after = get_snapshot()
    
    freed_standby = before.standby - after.standby
    freed_modified = before.modified - after.modified
    
    log_action(f"ENGINE: RAMMap v1 End. Freed Standby: {freed_standby}, Freed Modified: {freed_modified}")
    
    return {
        "standby_freed": freed_standby,
        "modified_freed": freed_modified,
        "total_freed_pages": freed_standby + freed_modified
    }

def set_autostart(enabled=True):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}"'
            else:
                cmd = f'"{sys.executable}" "{__file__}"'
            winreg.SetValueEx(key, "MemReductPro", 0, winreg.REG_SZ, cmd)
        else:
            try: winreg.DeleteValue(key, "MemReductPro")
            except FileNotFoundError: pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        log_action(f"Autostart Error: {e}")
        return False

def stress_test():
    """Instantly allocates ~500MB to demonstrate cleaning effectiveness."""
    try:
        # Use bytearray for instant physical allocation
        data = bytearray(500 * 1024 * 1024)
        time.sleep(2)
        del data
        gc.collect()
    except: pass

class MEMORY_STATS(ctypes.Structure):
    _fields_ = [
        ("commitTotal", ctypes.c_ulonglong),
        ("commitLimit", ctypes.c_ulonglong),
        ("workingSet", ctypes.c_ulonglong),
        ("standby", ctypes.c_ulonglong),
        ("modified", ctypes.c_ulonglong),
        ("available", ctypes.c_ulonglong),
        ("systemCache", ctypes.c_ulonglong),
    ]

# === GUI APPLICATION ===
def format_bytes(size_bytes):
    """Конвертация байтов в удобный формат (X.XX ГБ или X.X МБ)."""
    if size_bytes == 0:
        return "0 МБ"
    if size_bytes >= 1024**3:
        return f"{size_bytes / (1024**3):.2f} ГБ"
    else:
        return f"{size_bytes / (1024**2):.1f} МБ"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mem Reduct Pro")
        self.geometry("440x680")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.is_cleaning = False
        self.is_cleaning_files = False
        self.cleanup_manager = FileCleanupManager()
        self.memory_history = [0] * 60 # 60 seconds of history
        self.hotkey_thread = None
        self.stop_hotkey = threading.Event()
        
        self.setup_ui()
        self.update_stats()
        self.check_scheduler()
        self.setup_tray()
        self.start_hotkey_listener()

    def start_hotkey_listener(self):
        if config.data.get("hotkey_enabled", True):
            if self.hotkey_thread and self.hotkey_thread.is_alive():
                return
            self.stop_hotkey.clear()
            self.hotkey_thread = threading.Thread(target=self.hotkey_loop, daemon=True)
            self.hotkey_thread.start()

    def hotkey_loop(self):
        vk = get_vk_code(config.data.get("hotkey_key", "F7"))
        hotkey_id = 1
        
        # MOD_NOREPEAT = 0x4000 (Vista+)
        if not user32.RegisterHotKey(None, hotkey_id, 0, vk):
            log_action(f"Failed to register hotkey {config.data.get('hotkey_key')}")
            return
            
        try:
            msg = ctypes.wintypes.MSG()
            while not self.stop_hotkey.is_set():
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1): # PM_REMOVE = 1
                    if msg.message == WM_HOTKEY:
                        self.after(0, self.toggle_visibility)
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.05)
        finally:
            user32.UnregisterHotKey(None, hotkey_id)

    def toggle_visibility(self):
        if self.state() == "iconic" or not self.winfo_viewable():
            self.show_win()
        else:
            self.withdraw()

    def setup_ui(self):
        # Header
        self.header = ctk.CTkLabel(self, text="MEM REDUCT PRO", font=("Segoe UI", 26, "bold"), text_color="#3B8ED0")
        self.header.pack(pady=10)

        self.core_status_lbl = ctk.CTkLabel(self, text="Native Core: LOADING...", font=("Segoe UI", 10))
        self.core_status_lbl.pack()

        self.status_bar = ctk.CTkFrame(self, height=30, fg_color="#2B2B2B")
        self.status_bar.pack(fill="x", padx=10)
        admin_status = "АДМИНИСТРАТОР" if is_admin() else "ОГРАНИЧЕННЫЙ РЕЖИМ"
        admin_color = "#4CAF50" if is_admin() else "#FF5252"
        self.admin_lbl = ctk.CTkLabel(self.status_bar, text=admin_status, font=("Segoe UI", 10, "bold"), text_color=admin_color)
        self.admin_lbl.pack(pady=2)

        # Tabs
        self.tabs = ctk.CTkTabview(self, height=450, command=self.on_tab_change)
        self.tabs.pack(fill="both", padx=10, pady=5, expand=True)
        self.tabs.add("Обзор")
        self.tabs.add("Temp")
        self.tabs.add("Детали (WinAPI)")
        self.tabs.add("Настройки")

        # --- TAB 1: OVERVIEW ---
        ov_scroll = ctk.CTkScrollableFrame(self.tabs.tab("Обзор"), fg_color="transparent")
        ov_scroll.pack(fill="both", expand=True)
        ov = ov_scroll

        # ... (rest of overview code stays same)
        self.phys_frame = self.create_group(ov, "Физическая память")
        self.ram_val = self.create_metric(self.phys_frame, "Загрузка системы", "0%")
        
        # Memory Chart
        self.chart_canvas = tk.Canvas(self.phys_frame, height=50, bg="#2B2B2B", highlightthickness=0)
        self.chart_canvas.pack(fill="x", padx=20, pady=5)
        
        self.ram_bar = ctk.CTkProgressBar(self.phys_frame, height=10)
        self.ram_bar.pack(fill="x", padx=20, pady=5)
        self.ram_used = self.create_metric(self.phys_frame, "Используется", "0 ГБ")
        self.ram_avail = self.create_metric(self.phys_frame, "Доступно", "0 ГБ")
        self.ram_total = self.create_metric(self.phys_frame, "Всего в системе", "0 ГБ")

        self.virt_frame = self.create_group(ov, "Виртуальная память")
        self.page_lbl = self.create_metric(self.virt_frame, "Использование", "0 / 0 ГБ")

        self.cache_frame = self.create_group(ov, "Системный Кэш")
        self.sys_cache_ov_lbl = self.create_metric(self.cache_frame, "Кэш файлов", "0 МБ")
        self.sys_ws_lbl = self.create_metric(self.cache_frame, "Рабочий набор системы", "0 ГБ")

        # Top Processes
        self.proc_frame = self.create_group(ov, "Топ процессов (RAM)")
        self.proc_list_frame = ctk.CTkFrame(self.proc_frame, fg_color="transparent")
        self.proc_list_frame.pack(fill="x", padx=10, pady=5)
        self.proc_labels = [] # To store (name_lbl, size_lbl)

        # Stress Test Button
        self.stress_btn = ctk.CTkButton(ov, text="🔥 ТЕСТ НАГРУЗКИ", fg_color="#444", hover_color="#555", 
                                        height=28, command=lambda: threading.Thread(target=stress_test, daemon=True).start())
        self.stress_btn.pack(pady=5)

        # --- TAB 2: TEMP CLEANUP ---
        temp_tab = self.tabs.tab("Temp")
        self.setup_temp_tab(temp_tab)

        # --- TAB 3: WINAPI DETAILS ---
        det_scroll = ctk.CTkScrollableFrame(self.tabs.tab("Детали (WinAPI)"), fg_color="transparent")
        det_scroll.pack(fill="both", expand=True)
        det = det_scroll
        
        self.cache_group = self.create_group(det, "Кэши и списки страниц")
        self.sys_cache_lbl = self.create_metric(self.cache_group, "Системный кэш файлов", "0 МБ")
        self.modified_lbl = self.create_metric(self.cache_group, "Список измененных страниц", "0 МБ")
        self.standby_lbl = self.create_metric(self.cache_group, "Список ожидания", "0 МБ")
        self.standby_low_lbl = self.create_metric(self.cache_group, "Ожидание (низкий приоритет)", "0 МБ")
        
        # Version Specific
        self.ver_group = self.create_group(det, "Специфично для ОС")
        self.reg_cache_lbl = self.create_metric(self.ver_group, "Кэш реестра (8.1+)", "0 МБ")
        self.combined_lbl = self.create_metric(self.ver_group, "Комбинированные страницы (10+)", "0 МБ")

        # --- TAB 3: FILE CLEANUP ---
        # Commented out to avoid crash when tab is not added
        # file_tab = self.tabs.tab("Очистка файлов")
        # self.dir_frame = self.create_group(file_tab, "Директории для очистки")
        # ... (rest of file cleanup UI logic removed for now)

        # --- TAB 4: SETTINGS ---
        cfg = self.tabs.tab("Настройки")
        self.create_settings_ui(cfg)

        self.progress_lbl = ctk.CTkLabel(self, text="Ожидание действий пользователя...", font=("Segoe UI", 11))
        self.progress_lbl.pack(side="bottom", pady=5)

        # Main Clean Button (Fixed at the bottom, visibility toggled by tab)
        shield = "🛡️ " if not is_admin() else ""
        self.clean_btn = ctk.CTkButton(
            self, 
            text=f"{shield}ОЧИСТИТЬ ПАМЯТЬ", 
            height=45, 
            font=("Segoe UI", 15, "bold"),
            command=self.handle_clean_click
        )
        self.clean_btn.pack(fill="x", padx=20, pady=5)

    def on_tab_change(self):
        """Toggle visibility of the main clean button based on active tab."""
        if self.tabs.get() == "Обзор":
            self.clean_btn.pack(fill="x", padx=20, pady=5, before=self.progress_lbl)
        else:
            self.clean_btn.pack_forget()

    def setup_temp_tab(self, parent):
        # Scan and Clean Buttons
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.temp_scan_btn = ctk.CTkButton(btn_frame, text="🔍 СКАНИРОВАТЬ", command=self.handle_temp_scan)
        self.temp_scan_btn.pack(side="left", expand=True, padx=5)
        
        self.temp_clean_btn = ctk.CTkButton(btn_frame, text="🗑️ ОЧИСТИТЬ", state="disabled", fg_color="#FF5252", hover_color="#D32F2F", command=self.handle_temp_clean)
        self.temp_clean_btn.pack(side="right", expand=True, padx=5)

        # Progress Info
        self.temp_progress_bar = ctk.CTkProgressBar(parent, height=10)
        self.temp_progress_bar.pack(fill="x", padx=20, pady=5)
        self.temp_progress_bar.set(0)
        
        self.temp_status_lbl = ctk.CTkLabel(parent, text="Готов к сканированию", font=("Segoe UI", 11))
        self.temp_status_lbl.pack(pady=2)

        # File List Header
        list_header = ctk.CTkFrame(parent, height=30, fg_color="#2B2B2B")
        list_header.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(list_header, text="Найдено временных файлов", font=("Segoe UI", 12, "bold")).pack(pady=5)

        # Scrollable Frame for file list
        self.file_list_frame = ctk.CTkScrollableFrame(parent, height=300)
        self.file_list_frame.pack(fill="both", padx=10, pady=(0, 10))
        
        self.category_vars = {} # {category_name: BooleanVar}

    def handle_temp_scan(self):
        self.temp_scan_btn.configure(state="disabled")
        self.temp_clean_btn.configure(state="disabled")
        
        # Clear previous list
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        self.category_vars = {}

        def run_scan():
            def update_progress(msg, val):
                self.after(0, lambda: self.temp_status_lbl.configure(text=msg))
                self.after(0, lambda: self.temp_progress_bar.set(val))

            found = self.cleanup_manager.scan(progress_callback=update_progress)
            
            # Group by category for display
            categories = {}
            for f in found:
                cat = f['category']
                if cat not in categories: categories[cat] = {"count": 0, "size": 0, "files": []}
                categories[cat]["count"] += 1
                categories[cat]["size"] += f['size']
                categories[cat]["files"].append(f)

            def populate_ui():
                if not found:
                    ctk.CTkLabel(self.file_list_frame, text="Временные файлы не найдены").pack(pady=20)
                else:
                    for cat, data in categories.items():
                        cat_size_str = format_bytes(data["size"])
                        cat_frame = ctk.CTkFrame(self.file_list_frame, fg_color="transparent")
                        cat_frame.pack(fill="x", pady=1, padx=5)
                        
                        var = tk.BooleanVar(value=True)
                        self.category_vars[cat] = var
                        
                        cb = ctk.CTkCheckBox(cat_frame, text=f"{cat} ({data['count']})", 
                                             variable=var, font=("Segoe UI", 11))
                        cb.pack(side="left", padx=10, pady=5)
                        
                        size_lbl = ctk.CTkLabel(cat_frame, text=cat_size_str, font=("Segoe UI", 11, "bold"), text_color="#3B8ED0")
                        size_lbl.pack(side="right", padx=10)
                
                total_size = sum(f['size'] for f in found)
                self.temp_status_lbl.configure(text=f"Найдено: {format_bytes(total_size)} в {len(found)} файлах")
                if found:
                    self.temp_clean_btn.configure(state="normal")
                self.temp_scan_btn.configure(state="normal")

            self.after(0, populate_ui)

        threading.Thread(target=run_scan, daemon=True).start()

    def handle_temp_clean(self):
        # Get selected categories
        selected_cats = [cat for cat, var in self.category_vars.items() if var.get()]
        if not selected_cats:
            messagebox.showwarning("Внимание", "Выберите хотя бы одну категорию для очистки.")
            return

        files_to_delete = [f for f in self.cleanup_manager.found_files if f['category'] in selected_cats]
        if not files_to_delete:
            return

        if not messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить выбранные файлы ({len(files_to_delete)} шт.)?"):
            return
            
        self.temp_scan_btn.configure(state="disabled")
        self.temp_clean_btn.configure(state="disabled")

        def run_clean():
            def update_progress(msg, val):
                self.after(0, lambda: self.temp_status_lbl.configure(text=msg))
                self.after(0, lambda: self.temp_progress_bar.set(val))

            removed_size = self.cleanup_manager.cleanup(files_to_delete, progress_callback=update_progress)
            
            def finalize():
                messagebox.showinfo("Очистка завершена", f"Успешно удалено: {format_bytes(removed_size)}")
                self.temp_status_lbl.configure(text=f"Очищено: {format_bytes(removed_size)}")
                self.temp_scan_btn.configure(state="normal")
                # Clear list after clean
                for widget in self.file_list_frame.winfo_children():
                    widget.destroy()
                self.category_vars = {}
                ctk.CTkLabel(self.file_list_frame, text=f"Очистка завершена. Удалено {format_bytes(removed_size)}").pack(pady=20)

            self.after(0, finalize)

        threading.Thread(target=run_clean, daemon=True).start()

    def create_settings_ui(self, parent):
        self.auto_cb = ctk.CTkCheckBox(parent, text=f"Авто-очистка при загрузке ({config.data['auto_clean_threshold']}%)", command=self.save_settings)
        self.auto_cb.pack(pady=12, padx=20, anchor="w")
        if config.data["auto_clean_enabled"]: self.auto_cb.select()

        self.threshold_slider = ctk.CTkSlider(parent, from_=10, to=95, command=self.update_slider_text)
        self.threshold_slider.pack(fill="x", padx=20, pady=5)
        self.threshold_slider.set(config.data["auto_clean_threshold"])

        self.autostart_cb = ctk.CTkCheckBox(parent, text="Автозагрузка с Windows", command=self.save_settings)
        self.autostart_cb.pack(pady=12, padx=20, anchor="w")
        if config.data["autostart"]: self.autostart_cb.select()

        self.notif_cb = ctk.CTkCheckBox(parent, text="Уведомления об очистке", command=self.save_settings)
        self.notif_cb.pack(pady=12, padx=20, anchor="w")
        if config.data["show_notifications"]: self.notif_cb.select()

        self.charts_cb = ctk.CTkCheckBox(parent, text="Отображать график RAM", command=self.save_settings)
        self.charts_cb.pack(pady=12, padx=20, anchor="w")
        if config.data.get("show_charts", True): self.charts_cb.select()

        self.interactive_cb = ctk.CTkCheckBox(parent, text="Интерактивность процессов", command=self.save_settings)
        self.interactive_cb.pack(pady=12, padx=20, anchor="w")
        if config.data.get("interactive_procs", True): self.interactive_cb.select()

        self.tray_close_cb = ctk.CTkCheckBox(parent, text="Закрывать в системный трей", command=self.update_settings_visibility)
        self.tray_close_cb.pack(pady=12, padx=20, anchor="w")
        if config.data.get("minimize_to_tray", True): self.tray_close_cb.select()

        self.hotkey_frame = ctk.CTkFrame(parent, fg_color="transparent")
        # pack() will be called in update_settings_visibility
        
        self.hotkey_btn = ctk.CTkButton(self.hotkey_frame, text=f"Клавиша вызова: {config.data.get('hotkey_key', 'F7')}", 
                                        command=self.start_hotkey_recording)
        self.hotkey_btn.pack(side="left", padx=20)
        
        self.is_recording_hotkey = False
        self.update_settings_visibility()

        # Version info
        version_lbl = ctk.CTkLabel(parent, text="Версия: v1.0", font=("Segoe UI", 10), text_color="gray")
        version_lbl.pack(side="bottom", pady=20)

    def update_settings_visibility(self):
        """Show/hide hotkey settings based on tray setting."""
        if self.tray_close_cb.get():
            self.hotkey_frame.pack(fill="x", pady=5)
        else:
            self.hotkey_frame.pack_forget()
        self.save_settings()

    def start_hotkey_recording(self):
        """Enter hotkey recording mode."""
        if self.is_recording_hotkey:
            return
            
        self.is_recording_hotkey = True
        self.hotkey_btn.configure(text="Нажмите клавишу...", fg_color="#FF9900")
        
        # Temporarily stop the listener thread to avoid conflicts
        self.stop_hotkey.set()
        
        # Bind any key press to the main window
        self.bind_all("<Key>", self.on_hotkey_recorded)

    def on_hotkey_recorded(self, event):
        """Handle key press during recording."""
        key = event.keysym
        
        # Basic filtering/mapping
        if key.startswith("F") and key[1:].isdigit():
            new_key = key
        elif key in ["Escape", "Return", "Space"]:
            # Ignore these keys or handle them
            self.cancel_hotkey_recording()
            return
        else:
            # For now, let's stick to F-keys as they are safest for global hotkeys
            # But we can allow others if they are valid for RegisterHotKey
            new_key = key.upper()

        config.data["hotkey_key"] = new_key
        self.hotkey_btn.configure(text=f"Клавиша вызова: {new_key}", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        
        self.cancel_hotkey_recording()
        self.save_settings()
        
        # Restart listener with new key
        self.start_hotkey_listener()

    def cancel_hotkey_recording(self):
        self.is_recording_hotkey = False
        self.unbind_all("<Key>")
        self.hotkey_btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

    def update_slider_text(self, val):
        self.auto_cb.configure(text=f"Авто-очистка при загрузке ({int(val)}%)")
        self.save_settings()

    def create_group(self, parent, title):
        f = ctk.CTkFrame(parent)
        f.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 13, "bold"), text_color="#3B8ED0").pack(pady=5)
        return f

    def create_metric(self, parent, label, val):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 11)).pack(side="left")
        v = ctk.CTkLabel(f, text=val, font=("Segoe UI", 11, "bold"))
        v.pack(side="right")
        return v

    def add_dir(self):
        d = filedialog.askdirectory()
        if d:
            config.data["cleanup_dirs"].append(d)
            self.dir_list.insert(tk.END, d)
            config.save()

    def remove_dir(self):
        sel = self.dir_list.curselection()
        if sel:
            idx = sel[0]
            val = self.dir_list.get(idx)
            config.data["cleanup_dirs"].remove(val)
            self.dir_list.delete(idx)
            config.save()

    def update_stats(self):
        try:
            # Update Core Status UI
            if native_core:
                self.core_status_lbl.configure(text="Native Core: ACTIVE (C++ DLL)", text_color="green")
            else:
                self.core_status_lbl.configure(text="Native Core: INACTIVE (Python Fallback)", text_color="orange")

            # RAMMap-style detailed accounting
            acc = get_detailed_accounting()
            mem = psutil.virtual_memory()
            
            # --- Get Detailed Metrics ---
            perf = PERFORMANCE_INFORMATION()
            perf.cb = ctypes.sizeof(perf)
            psapi.GetPerformanceInfo(ctypes.byref(perf), perf.cb)
            
            # Metrics for "Overview" tab
            self.ram_avail.configure(text=f"{acc['available']/(1024**3):.2f} ГБ")
            self.ram_total.configure(text=f"{mem.total/(1024**3):.1f} ГБ")
            self.page_lbl.configure(text=f"{psutil.swap_memory().used/(1024**3):.2f} / {psutil.swap_memory().total/(1024**3):.2f} ГБ")
            
            # Real Used = Total - Available (Available includes Free + Zero + Standby)
            # This matches Mem Reduct and RAMMap logic
            real_used_bytes = mem.total - acc['available']
            percent = (real_used_bytes / mem.total) * 100
            
            # Color logic
            if percent < 65: color = "#3B8ED0"
            elif percent < 80: color = "#ff9900"
            else: color = "#ff3333"
            
            self.ram_val.configure(text=f"{percent:.1f}%", text_color=color)
            self.ram_bar.set(percent / 100)
            self.ram_bar.configure(progress_color=color)
            self.ram_used.configure(text=f"{real_used_bytes/(1024**3):.2f} ГБ")

            # System Cache / Working Set
            system_cache_bytes = perf.SystemCache * acc['page_size']
            self.sys_cache_ov_lbl.configure(text=f"{system_cache_bytes // (1024**2)} МБ")
            total_ws = (perf.PhysicalTotal - perf.PhysicalAvailable) * acc['page_size']
            self.sys_ws_lbl.configure(text=f"{total_ws/(1024**3):.2f} ГБ")

            # --- TAB 2: WINAPI DETAILS ---
            self.sys_cache_lbl.configure(text=f"{system_cache_bytes // (1024**2)} МБ")
            self.modified_lbl.configure(text=f"{acc['modified'] // (1024**2)} МБ")
            self.standby_lbl.configure(text=f"{acc['standby'] // (1024**2)} МБ")
            self.standby_low_lbl.configure(text=f"{acc['free'] // (1024**2)} МБ (Свободно)")
            
            # Version Specific
            if native_core:
                stats = MEMORY_STATS()
                native_core.GetExtendedMemoryStats(ctypes.byref(stats))
                self.reg_cache_lbl.configure(text=f"{(stats.commitLimit - stats.commitTotal)//(1024**2)} МБ" if hasattr(stats, 'commitLimit') else "N/A")
            else:
                # Estimate Registry cache via system call if needed, but for now N/A
                self.reg_cache_lbl.configure(text="N/A (DLL Required)")
            
            self.combined_lbl.configure(text=f"{acc['zero'] // (1024**2)} МБ (Zeroed)")

            # --- Update Chart ---
            self.memory_history.pop(0)
            self.memory_history.append(percent)
            self.draw_chart()

            # --- Update Top Processes ---
            self.update_top_processes()

        except Exception as e:
            log_action(f"Update error: {e}")
            
        self.after(1000, self.update_stats)

    def draw_chart(self):
        if not config.data.get("show_charts", True):
            self.chart_canvas.pack_forget()
            return
        else:
            self.chart_canvas.pack(fill="x", padx=20, pady=5, after=self.ram_val.master)

        self.chart_canvas.delete("all")
        w = self.chart_canvas.winfo_width()
        h = self.chart_canvas.winfo_height()
        if w <= 1: return # Canvas not ready
        
        points = []
        for i, val in enumerate(self.memory_history):
            x = (i / (len(self.memory_history) - 1)) * w
            y = h - (val / 100) * h
            points.extend([x, y])
        
        if len(points) >= 4:
            self.chart_canvas.create_line(points, fill="#3B8ED0", width=2, smooth=True)
            # Add semi-transparent fill
            fill_points = [0, h] + points + [w, h]
            self.chart_canvas.create_polygon(fill_points, fill="#3B8ED0", stipple="gray25", outline="")

    def update_top_processes(self):
        try:
            # Get top 5 memory consumers
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    procs.append({
                        'pid': p.info['pid'],
                        'name': p.info['name'],
                        'rss': p.info['memory_info'].rss
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            top_procs = sorted(procs, key=lambda x: x['rss'], reverse=True)[:5]
            
            # Clear old labels
            for f in self.proc_list_frame.winfo_children():
                f.destroy()
            
            for proc in top_procs:
                name = proc['name']
                size = proc['rss']
                pid = proc['pid']
                
                is_interactive = config.data.get("interactive_procs", True)
                cursor_style = "hand2" if is_interactive else ""
                
                f = ctk.CTkFrame(self.proc_list_frame, fg_color="transparent", cursor=cursor_style)
                f.pack(fill="x", pady=1)
                
                if is_interactive:
                    # Bind click events to the frame and its children
                    f.bind("<Button-1>", lambda e, p=proc: self.show_process_menu(e, p))
                    
                    # Add hover effect
                    f.bind("<Enter>", lambda e, frame=f: frame.configure(fg_color="#333333"))
                    f.bind("<Leave>", lambda e, frame=f: frame.configure(fg_color="transparent"))
                
                name_lbl = ctk.CTkLabel(f, text=name[:20], font=("Segoe UI", 10))
                name_lbl.pack(side="left")
                
                size_lbl = ctk.CTkLabel(f, text=format_bytes(size), font=("Segoe UI", 10, "bold"), text_color="#3B8ED0")
                size_lbl.pack(side="right", padx=10)

                if is_interactive:
                    name_lbl.bind("<Button-1>", lambda e, p=proc: self.show_process_menu(e, p))
                    size_lbl.bind("<Button-1>", lambda e, p=proc: self.show_process_menu(e, p))
        except: pass

    def show_process_menu(self, event, proc):
        """Show a context menu for the selected process."""
        menu = tk.Menu(self, tearoff=0, bg="#2B2B2B", fg="white", activebackground="#3B8ED0")
        menu.add_command(label=f"--- {proc['name']} (PID: {proc['pid']}) ---", state="disabled")
        menu.add_separator()
        menu.add_command(label="🧹 Очистить память процесса", command=lambda: self.clean_single_process(proc))
        menu.add_command(label="❌ Завершить процесс", command=lambda: self.kill_process(proc))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def clean_single_process(self, proc):
        """Trims the working set of a specific process."""
        try:
            ACCESS = 0x1F0FFF
            h = kernel32.OpenProcess(ACCESS, False, proc['pid'])
            if h:
                psapi.EmptyWorkingSet(h)
                kernel32.CloseHandle(h)
                self.progress_lbl.configure(text=f"Память процесса {proc['name']} очищена.")
            else:
                messagebox.showerror("Ошибка", "Недостаточно прав для очистки этого процесса.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить память: {e}")

    def kill_process(self, proc):
        """Terminates a specific process."""
        if messagebox.askyesno("Подтверждение", f"Вы действительно хотите завершить процесс {proc['name']}?"):
            try:
                p = psutil.Process(proc['pid'])
                p.terminate()
                self.progress_lbl.configure(text=f"Процесс {proc['name']} завершен.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось завершить процесс: {e}")

    def handle_clean_click(self):
        if not is_admin():
            if messagebox.askyesno("Требуются права", "Для агрессивной очистки необходимы права администратора. Повысить права?"):
                shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}"', None, 1)
                sys.exit(0)
            return
        
        self.clean_btn.configure(state="disabled", text="В ПРОЦЕССЕ...")
        
        def run():
            try:
                # Capture accurate metrics before
                acc_before = get_detailed_accounting()
                mem_before = psutil.virtual_memory()
                used_before_pct = ((mem_before.total - acc_before['available']) / mem_before.total) * 100
                
                # 1. RAM Cleanup
                self.after(0, lambda: self.progress_lbl.configure(text="🔥 ENGINE: RAMMap Cycle v1..."))
                
                log_action(f"CLEANUP START [RAMMap Engine v1] - RAM: {used_before_pct:.1f}% | Standby: {acc_before['standby']//1024**2}MB | Modified: {acc_before['modified']//1024**2}MB")

                if native_core:
                    native_core.AggressiveClean()
                else:
                    aggressive_clean_fallback()
                
                # Stabilization
                kernel32.Sleep(1000)
                
                # Capture accurate metrics after
                acc_after = get_detailed_accounting()
                mem_after = psutil.virtual_memory()
                used_after_pct = ((mem_after.total - acc_after['available']) / mem_after.total) * 100
                
                # Calculate freed based on increase in available physical memory
                freed_bytes = max(0, acc_after['available'] - acc_before['available'])
                freed_text = f"{freed_bytes / (1024**3):.2f} ГБ" if freed_bytes > 1024**3 else f"{freed_bytes / (1024**2):.1f} МБ"

                # 2. Log detailed metrics (Metrics "Before/After")
                log_action(f"CLEANUP END - RAM: {used_after_pct:.1f}% | Standby: {acc_after['standby']//1024**2}MB | Modified: {acc_after['modified']//1024**2}MB")
                log_action(f"RESULT: Freed {freed_text} | RAM Delta: {used_before_pct - used_after_pct:.1f}%")

                # 3. UI Update
                self.after(0, lambda: self.progress_lbl.configure(text=f"Освобождено {freed_text} ({used_before_pct:.0f}% -> {used_after_pct:.0f}%)."))
                
                # Automatically clean temp dirs
                for d in config.data.get("cleanup_dirs", []):
                    if os.path.exists(d):
                        if native_core:
                            native_core.StartParallelFileCleanup(ctypes.c_wchar_p(d), config.data.get("cleanup_threads", 4), config.data.get("cleanup_buffer_mb", 64))
                
                # Show notification with delta
                if config.data.get("show_notifications"):
                    self.show_notif("Mem Reduct Pro", f"Очистка завершена!\nRAM: {used_before_pct:.0f}% -> {used_after_pct:.0f}%\nОсвобождено: {freed_text}")
                
                self.after(5000, lambda: self.progress_lbl.configure(text="Ожидание действий пользователя..."))
                self.after(0, lambda: self.clean_btn.configure(state="normal", text="ОЧИСТИТЬ ПАМЯТЬ"))
            except Exception as e:
                log_action(f"Cleaning error: {e}")
                self.after(0, lambda: self.clean_btn.configure(state="normal", text="ОЧИСТИТЬ ПАМЯТЬ"))

        threading.Thread(target=run, daemon=True).start()

    def check_scheduler(self):
        if config.data["auto_clean_enabled"]:
            if psutil.virtual_memory().percent >= config.data["auto_clean_threshold"]:
                # Trigger cleanup if not already cleaning
                if self.clean_btn.cget("state") == "normal":
                    self.handle_clean_click()
        self.after(60000, self.check_scheduler)

    def save_settings(self, *args):
        try:
            if hasattr(self, 'auto_cb'):
                config.data["auto_clean_enabled"] = self.auto_cb.get()
            if hasattr(self, 'threshold_slider'):
                config.data["auto_clean_threshold"] = int(self.threshold_slider.get())
            if hasattr(self, 'autostart_cb'):
                config.data["autostart"] = self.autostart_cb.get()
            if hasattr(self, 'notif_cb'):
                config.data["show_notifications"] = self.notif_cb.get()
            if hasattr(self, 'charts_cb'):
                config.data["show_charts"] = self.charts_cb.get()
            if hasattr(self, 'interactive_cb'):
                config.data["interactive_procs"] = self.interactive_cb.get()
            if hasattr(self, 'tray_close_cb'):
                config.data["minimize_to_tray"] = self.tray_close_cb.get()
            
            config.save()
            if "autostart" in config.data:
                set_autostart(config.data["autostart"])
        except Exception as e:
            log_action(f"Save Settings Error: {e}")

    def show_notif(self, title, msg):
        try:
            if hasattr(self, 'tray_icon'):
                self.tray_icon.notify(msg, title)
        except: pass

    def setup_tray(self):
        try:
            icon_path = BUNDLE_DIR / "brain.ico"
            if icon_path.exists():
                img = Image.open(str(icon_path))
            else:
                img = Image.new('RGB', (64, 64), color=(43, 43, 43))
                d = ImageDraw.Draw(img)
                d.ellipse([10, 10, 54, 54], fill="#3B8ED0")
            
            menu = (pystray.MenuItem('Показать', self.show_win, default=True),
                    pystray.MenuItem('Очистить', self.handle_clean_click),
                    pystray.MenuItem('Выход', self.quit_app))
            self.tray_icon = pystray.Icon("MRPro", img, "Mem Reduct Pro", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except: pass

    def show_win(self, icon=None, item=None):
        self.deiconify()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def on_close(self):
        if config.data["minimize_to_tray"]: self.withdraw()
        else: self.quit_app()

    def quit_app(self, icon=None, item=None):
        if hasattr(self, 'tray_icon'): self.tray_icon.stop()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    # === SINGLE INSTANCE CHECK ===
    mutex_name = "Global\\MemReductPro_SingleInstance_Mutex"
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    
    if last_error == 183: # ERROR_ALREADY_EXISTS
        # Find existing window and show it
        hwnd = user32.FindWindowW(None, "Mem Reduct Pro")
        if hwnd:
            user32.ShowWindow(hwnd, 9) # SW_RESTORE = 9
            user32.SetForegroundWindow(hwnd)
        sys.exit(0)

    try:
        if not is_admin():
            if request_admin():
                sys.exit(0)
        
        compile_and_load_dll()
        
        app = App()
        app.mainloop()
    except Exception as e:
        log_action(f"Critical error: {e}")
        sys.exit(1)
