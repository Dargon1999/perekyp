import ctypes
import os
import platform
from ctypes import Structure, c_ulonglong, c_bool, c_int, sizeof, byref, POINTER, WinError
from ctypes.wintypes import DWORD, HANDLE, BOOL, ULARGE_INTEGER

# --- Windows API Definitions ---

class MEMORYSTATUSEX(Structure):
    _fields_ = [
        ("dwLength", DWORD),
        ("dwMemoryLoad", DWORD),
        ("ullTotalPhys", c_ulonglong),
        ("ullAvailPhys", c_ulonglong),
        ("ullTotalPageFile", c_ulonglong),
        ("ullAvailPageFile", c_ulonglong),
        ("ullTotalVirtual", c_ulonglong),
        ("ullAvailVirtual", c_ulonglong),
        ("ullAvailExtendedVirtual", c_ulonglong),
    ]

class PERFORMANCE_INFORMATION(Structure):
    _fields_ = [
        ("cb", DWORD),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", DWORD),
        ("ProcessCount", DWORD),
        ("ThreadCount", DWORD),
    ]

class PROCESSENTRY32(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("cntUsage", DWORD),
        ("th32ProcessID", DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", DWORD),
        ("cntThreads", DWORD),
        ("th32ParentProcessID", DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]

class TOKEN_ELEVATION(Structure):
    _fields_ = [
        ("TokenIsElevated", DWORD),
    ]

# Windows Constants
TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100
TOKEN_QUERY = 0x0008
TokenElevation = 20

# Load Windows DLLs
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
advapi32 = ctypes.windll.advapi32

class MemoryStats(Structure):
    _fields_ = [
        ("total_phys", c_ulonglong),
        ("avail_phys", c_ulonglong),
        ("used_phys", c_ulonglong),
        ("total_page", c_ulonglong),
        ("avail_page", c_ulonglong),
        ("system_cache", c_ulonglong),
        ("standby", c_ulonglong),
        ("modified", c_ulonglong),
    ]

class MemReductAPI:
    def __init__(self):
        # We no longer load a custom DLL, we use Windows API directly via ctypes
        self.is_windows = platform.system() == "Windows"

    def get_stats(self):
        if not self.is_windows:
            return None
            
        stats = MemoryStats()
        
        # 1. GlobalMemoryStatusEx
        mem_info = MEMORYSTATUSEX()
        mem_info.dwLength = sizeof(MEMORYSTATUSEX)
        if kernel32.GlobalMemoryStatusEx(byref(mem_info)):
            stats.total_phys = mem_info.ullTotalPhys
            stats.avail_phys = mem_info.ullAvailPhys
            stats.used_phys = mem_info.ullTotalPhys - mem_info.ullAvailPhys
            stats.total_page = mem_info.ullTotalPageFile
            stats.avail_page = mem_info.ullAvailPageFile
        else:
            return None
            
        # 2. GetPerformanceInfo for System Cache
        perf_info = PERFORMANCE_INFORMATION()
        perf_info.cb = sizeof(PERFORMANCE_INFORMATION)
        if psapi.GetPerformanceInfo(byref(perf_info), sizeof(PERFORMANCE_INFORMATION)):
            stats.system_cache = perf_info.SystemCache * perf_info.PageSize
            
        return stats

    def clean(self, level):
        if not self.is_windows:
            return False
            
        success = True
        
        # Level 0+: Clean current process and all other processes working sets
        if level >= 0:
            # Clean current process
            psapi.EmptyWorkingSet(kernel32.GetCurrentProcess())
            
            # Clean all other processes
            h_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if h_snap != -1:
                pe = PROCESSENTRY32()
                pe.dwSize = sizeof(PROCESSENTRY32)
                if kernel32.Process32First(h_snap, byref(pe)):
                    while True:
                        h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pe.th32ProcessID)
                        if h_process:
                            psapi.EmptyWorkingSet(h_process)
                            kernel32.CloseHandle(h_process)
                        if not kernel32.Process32Next(h_snap, byref(pe)):
                            break
                kernel32.CloseHandle(h_snap)
        
        # Level 1+: Future extensions for standby/modified list cleanup
        if level >= 1:
            pass
            
        # Level 2+: Attempt system cache cleanup (requires admin)
        if level >= 2 and self.is_elevated():
            # In C++ this was CleanSystemCache placeholder
            # System cache cleanup via SetSystemFileCacheSize or NtSetSystemInformation is complex
            # For now, we rely on aggressive working set trimming which also helps
            pass
            
        return success

    def is_elevated(self):
        if not self.is_windows:
            return False
            
        h_token = HANDLE()
        if advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_QUERY, byref(h_token)):
            elevation = TOKEN_ELEVATION()
            size = DWORD()
            if advapi32.GetTokenInformation(h_token, TokenElevation, byref(elevation), sizeof(elevation), byref(size)):
                ret = bool(elevation.TokenIsElevated)
                kernel32.CloseHandle(h_token)
                return ret
            kernel32.CloseHandle(h_token)
        return False

    @staticmethod
    def format_bytes(bytes_val):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
