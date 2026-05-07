#!/usr/bin/env python3
"""Working hotkey listener - F7/F8 with proper types"""
import ctypes
from ctypes import wintypes
import sys

# WinAPI
user32 = ctypes.WinDLL('user32', use_last_error=True)

# Constants
VK_F7 = 0x76
VK_F8 = 0x77
WM_HOTKEY = 0x0312
WM_DESTROY = 0x0002

# Proper callback type
LPARAM = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
WPARAM = wintypes.WPARAM
LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM
)

# MSG structure
class MSG(ctypes.Structure):
    _fields_ = [
        ('hwnd', wintypes.HWND),
        ('message', wintypes.UINT),
        ('wParam', WPARAM),
        ('lParam', LPARAM),
        ('time', wintypes.DWORD),
        ('pt', wintypes.POINT)
    ]

class POINT(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

# Window class
class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ('style', wintypes.UINT),
        ('lpfnWndProc', WNDPROC),
        ('cbClsExtra', wintypes.INT),
        ('cbWndExtra', wintypes.INT),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HICON),
        ('hCursor', wintypes.HCURSOR),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR)
    ]

CLASS_NAME = "HotkeyTest"

# Global
running = True

def wnd_proc(hwnd, msg, wparam, lparam):
    global running
    if msg == WM_HOTKEY:
        if wparam == 1:
            print("\n>>> F7 PRESSED! <<<")
            trigger_f7_action()
        elif wparam == 2:
            print("\n>>> F8 PRESSED! <<<")
            trigger_f8_action()
        return 0
    elif msg == WM_DESTROY:
        running = False
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

def trigger_f7_action():
    """Action for F7 - launch Mem Reduct Pro"""
    print("[F7] Would launch Mem Reduct Pro...")
    import subprocess
    import os
    from pathlib import Path
    
    base = Path(__file__).parent
    exe = base / "Mem Reduct Pro.exe"
    
    if exe.exists():
        print("[F7] Found: {}".format(exe))
        subprocess.Popen([str(exe)])
        print("[F7] Launched!")
    else:
        print("[F7] ERROR: {} not found".format(exe))

def trigger_f8_action():
    """Action for F8 - clean TEMP"""
    print("[F8] Would clean TEMP...")
    import subprocess
    import sys
    from pathlib import Path
    
    base = Path(__file__).parent
    sys.path.insert(0, str(base))
    
    try:
        from temp_cleaner import clean_all_temp
        freed, count = clean_all_temp()
        
        if freed > 1024**3:
            freed_text = "{:.2f} GB".format(freed / (1024**3))
        else:
            freed_text = "{:.1f} MB".format(freed / (1024**2))
        
        print("[F8] Cleaned: {}, files: {}".format(freed_text, count))
        
        # Show notification
        ps = """
$template = '<toast><visual><binding template="ToastGeneric"><text>Mem Reduct Pro</text><text>TEMP: {}</text></binding></visual></toast>'
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Mem Reduct Pro").Show($toast)
""".format("osvobojdeno {}, files: {}".format(freed_text, count))
        
        subprocess.Popen(["powershell", "-Command", ps], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
    except Exception as e:
        print("[F8] Error: {}".format(e))

def main():
    global running
    print("=" * 60)
    print("Mem Reduct Pro - Hotkey Test")
    print("=" * 60)
    
    # Register F7
    if not user32.RegisterHotKey(None, 1, 0, VK_F7):
        print("[ERROR] F7 failed: {}".format(ctypes.get_last_error()))
        return
    print("[OK] F7 registered (0x{:02X})".format(VK_F7))
    
    # Register F8
    if not user32.RegisterHotKey(None, 2, 0, VK_F8):
        print("[ERROR] F8 failed: {}".format(ctypes.get_last_error()))
        user32.UnregisterHotKey(None, 1)
        return
    print("[OK] F8 registered (0x{:02X})".format(VK_F8))
    
    # Window class
    wc = WNDCLASS()
    wc.lpszClassName = CLASS_NAME
    wc.lpfnWndProc = WNDPROC(wnd_proc)
    
    if not user32.RegisterClassW(ctypes.byref(wc)):
        print("[ERROR] Class failed: {}".format(ctypes.get_last_error()))
        cleanup()
        return
    
    # Create window
    hwnd = user32.CreateWindowExW(
        0, CLASS_NAME, "Listener", 0, 0, 0, 0, 0, None, None, None, None
    )
    
    if not hwnd:
        print("[ERROR] Window failed: {}".format(ctypes.get_last_error()))
        cleanup()
        return
    
    print("\n[READY] Press F7 or F8 to test (Ctrl+C to exit)\n")
    
    # Message loop
    msg = MSG()
    while running and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    
    cleanup()

def cleanup():
    print("\n[EXIT] Cleaning up...")
    try:
        user32.UnregisterHotKey(None, 1)
        user32.UnregisterHotKey(None, 2)
        user32.UnregisterClassW(CLASS_NAME, None)
    except:
        pass
    print("[EXIT] Done")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[EXIT] Interrupted")
        running = False
        sys.exit(0)
