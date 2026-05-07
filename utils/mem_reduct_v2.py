#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mem Reduct Pro - Aggressive Memory Optimizer
"""

import ctypes
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
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
try:
    import customtkinter as ctk
except ImportError:
    # Fallback or alert user
    pass
import psutil
from PIL import Image, ImageDraw
try:
    import pystray
except ImportError:
    pass

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
# Logging disabled as per user request
def log_action(msg):
    pass

# === WinAPI Definitions ===
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

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
    except:
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
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mem Reduct Pro")
        self.geometry("440x720")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.is_cleaning = False
        self.is_cleaning_files = False
        
        self.setup_ui()
        self.update_stats()
        self.check_scheduler()
        self.setup_tray()

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
        self.tabs = ctk.CTkTabview(self, height=480)
        self.tabs.pack(fill="both", padx=10, pady=5)
        self.tabs.add("Обзор")
        self.tabs.add("Детали (WinAPI)")
        self.tabs.add("Настройки")

        # --- TAB 1: OVERVIEW ---
        ov = self.tabs.tab("Обзор")
        self.phys_frame = self.create_group(ov, "Физическая память")
        self.ram_val = self.create_metric(self.phys_frame, "Загрузка системы", "0%")
        self.ram_bar = ctk.CTkProgressBar(self.phys_frame, height=12)
        self.ram_bar.pack(fill="x", padx=20, pady=10)
        self.ram_used = self.create_metric(self.phys_frame, "Используется", "0 ГБ")
        self.ram_avail = self.create_metric(self.phys_frame, "Доступно", "0 ГБ")
        self.ram_total = self.create_metric(self.phys_frame, "Всего в системе", "0 ГБ")

        self.virt_frame = self.create_group(ov, "Виртуальная память (файл подкачки)")
        self.page_lbl = self.create_metric(self.virt_frame, "Использование", "0 / 0 ГБ")

        self.cache_frame = self.create_group(ov, "Системный Кэш")
        self.sys_cache_ov_lbl = self.create_metric(self.cache_frame, "Кэш файлов", "0 МБ")
        self.sys_ws_lbl = self.create_metric(self.cache_frame, "Рабочий набор системы", "0 ГБ")

        # Stress Test Button
        self.stress_btn = ctk.CTkButton(ov, text="🔥 ТЕСТ НАГРУЗКИ", fg_color="#444", hover_color="#555", 
                                        height=30, command=lambda: threading.Thread(target=stress_test, daemon=True).start())
        self.stress_btn.pack(pady=10)

        # Clean Button
        shield = "🛡️ " if not is_admin() else ""
        self.clean_btn = ctk.CTkButton(
            ov, 
            text=f"{shield}ОЧИСТИТЬ ПАМЯТЬ", 
            height=50, 
            font=("Segoe UI", 16, "bold"),
            command=self.handle_clean_click
        )
        self.clean_btn.pack(fill="x", padx=20, pady=10)

        # --- TAB 2: WINAPI DETAILS ---
        det = self.tabs.tab("Детали (WinAPI)")
        self.cache_group = self.create_group(det, "Кэши и списки страниц")
        self.sys_cache_lbl = self.create_metric(self.cache_group, "Системный кэш файлов", "0 МБ")
        self.modified_lbl = self.create_metric(self.cache_group, "Список измененных страниц", "0 МБ")
        self.standby_lbl = self.create_metric(self.cache_group, "Список ожидания", "0 МБ")
        self.standby_low_lbl = self.create_metric(self.cache_group, "Ожидание (низкий приоритет)", "0 МБ")
        
        # Version Specific
        self.ver_group = self.create_group(det, "Специфично для ОС")
        self.reg_cache_lbl = self.create_metric(self.ver_group, "Кэш реестра (8.1+)", "0 МБ")
        self.combined_lbl = self.create_metric(self.ver_group, "Комбинированные страницы (10+)", "0 МБ")

        # --- TAB 4: SETTINGS ---
        cfg = self.tabs.tab("Настройки")
        self.create_settings_ui(cfg)

        self.progress_lbl = ctk.CTkLabel(self, text="Ожидание действий пользователя...", font=("Segoe UI", 11))
        self.progress_lbl.pack(side="bottom", pady=5)

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

        # Version info
        version_lbl = ctk.CTkLabel(parent, text="Версия: v2.0", font=("Segoe UI", 10), text_color="gray")
        version_lbl.pack(side="bottom", pady=20)

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
                self.reg_cache_lbl.configure(text="N/A (DLL Required)")
            
            self.combined_lbl.configure(text=f"{acc['zero'] // (1024**2)} МБ (Zeroed)")

        except:
            pass
            
        self.after(1000, self.update_stats)

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

                # 3. UI Update
                self.after(0, lambda: self.progress_lbl.configure(text=f"Освобождено {freed_text} ({used_before_pct:.0f}% -> {used_after_pct:.0f}%)."))
                
                # Show notification with delta
                if config.data.get("show_notifications"):
                    self.show_notif("Mem Reduct Pro", f"Очистка завершена!\nRAM: {used_before_pct:.0f}% -> {used_after_pct:.0f}%\nОсвобождено: {freed_text}")
                
                self.after(5000, lambda: self.progress_lbl.configure(text="Ожидание действий пользователя..."))
                self.after(0, lambda: self.clean_btn.configure(state="normal", text="ОЧИСТИТЬ ПАМЯТЬ"))
            except:
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
            
            config.save()
            if "autostart" in config.data:
                set_autostart(config.data["autostart"])
        except:
            pass

    def show_notif(self, title, msg):
        try:
            if hasattr(self, 'tray_icon'):
                self.tray_icon.notify(msg, title)
        except: pass

    def setup_tray(self):
        try:
            icon_path = BUND_DIR / "brain.ico"
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
    try:
        if not is_admin():
            if request_admin():
                sys.exit(0)
        
        compile_and_load_dll()
        
        app = App()
        app.mainloop()
    except:
        sys.exit(1)
