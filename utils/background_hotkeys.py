import os
import sys
import time
import ctypes
import shutil
import glob
import platform
import tempfile
import subprocess
import threading
import gc
import keyboard
import psutil
try:
    from plyer import notification
except ImportError:
    notification = None

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def show_message(title, message):
    """Reliable Windows message box + Tray notification."""
    # Try sound first as fallback
    try:
        ctypes.windll.kernel32.Beep(440, 200) # Standard A4 note
    except:
        pass

    try:
        if notification:
            notification.notify(
                title=title,
                message=message,
                app_name="MoneyTracker Background",
                timeout=5
            )
    except:
        pass
    
    # Also log to a file for debugging
    with open("hotkeys_debug.log", "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {title}: {message}\n")

def clean_temp():
    """Deep cleaning of temporary files."""
    total_freed = 0
    targets = [tempfile.gettempdir()]
    
    if platform.system() == "Windows":
        targets.extend([
            os.path.expandvars(r'%LOCALAPPDATA%\Temp'),
            os.path.expandvars(r'%SystemRoot%\Temp'),
            os.path.expandvars(r'%SystemRoot%\Prefetch')
        ])
    
    for target in targets:
        if not os.path.exists(target): continue
        for root, dirs, files in os.walk(target, topdown=False):
            for name in files:
                try:
                    file_path = os.path.join(root, name)
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    total_freed += size
                except: pass
            for name in dirs:
                try: shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                except: pass
                
    # Empty Recycle Bin (Windows)
    if platform.system() == "Windows":
        try: ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 1 | 2 | 4)
        except: pass
        
    return f"Очистка завершена. Освобождено {total_freed / (1024*1024):.2f} МБ"

import threading

# --- Global States for Debouncing and Locking ---
f7_lock = threading.Lock()
f8_lock = threading.Lock()
f7_active = False # Atomic-like flag
f8_active = False

def on_f7():
    """F7 Action: Mem Cleanup (Embedded Resource)."""
    global f7_active
    
    # Check-and-set locking mechanism
    with f7_lock:
        if f7_active:
            return
        f7_active = True
    
    try:
        show_message("MoneyTracker: ОЗУ", "Запуск встроенной очистки памяти...")
        from utils.mem_reduct_launcher import launch_embedded_mem_reduct
        success, res = launch_embedded_mem_reduct()
        show_message("MoneyTracker: ОЗУ", res)
        
        # Prevent double-trigger from same physical press (debounce/auto-repeat)
        while keyboard.is_pressed('f7'):
            time.sleep(0.1)
            
    finally:
        # Reset flag only after operation completes AND key is released
        with f7_lock:
            f7_active = False

def on_f8():
    """F8 Action: Temp Cleanup."""
    global f8_active
    
    # Check-and-set locking mechanism
    with f8_lock:
        if f8_active:
            return
        f8_active = True
    
    try:
        show_message("MoneyTracker: Temp", "Запуск глубокой очистки...")
        res = clean_temp()
        show_message("MoneyTracker: Temp", res)
        
        # Prevent double-trigger from same physical press
        while keyboard.is_pressed('f8'):
            time.sleep(0.1)
            
    finally:
        # Reset flag only after operation completes AND key is released
        with f8_lock:
            f8_active = False

def main():
    # Simple check to avoid multiple instances
    lock_file = os.path.join(tempfile.gettempdir(), "moneytracker_hotkeys.lock")
    if os.path.exists(lock_file):
        try:
            # Check if process is still alive (Windows)
            with open(lock_file, "r") as f:
                pid = int(f.read().strip())
            if pid != os.getpid():
                # Try to see if process exists
                import psutil
                if psutil.pid_exists(pid):
                    print("Hotkey listener already running. Exiting.")
                    return
        except:
            pass
            
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))

    # Write start signal to log
    with open("hotkeys_debug.log", "w", encoding="utf-8") as f:
        f.write(f"Background Hotkeys Listener started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Running as Admin: {is_admin()}\n")

    # Register global hotkeys with block=True to avoid missing events
    keyboard.add_hotkey('f7', on_f7)
    keyboard.add_hotkey('f8', on_f8)
    
    # Keep the script running
    try:
        keyboard.wait()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        with open("hotkeys_debug.log", "a", encoding="utf-8") as f:
            f.write(f"CRITICAL ERROR: {str(e)}\n")

if __name__ == "__main__":
    # The script needs admin to hook keys if other admin apps are focused
    # However, we'll try to run normally first.
    main()
