import sys
import os
import time
import subprocess
import logging
import shutil
import tempfile
import hashlib

def verify_integrity(file_path):
    """Basic integrity check: file exists, size is reasonable, and can be read."""
    try:
        if not os.path.exists(file_path):
            return False, "Файл не найден"
        
        size = os.path.getsize(file_path)
        if size < 1000000: # 1MB minimum for MoneyTracker.exe
            return False, f"Файл слишком мал ({size} байт)"
            
        # Try to read a chunk to ensure it's not locked/unreadable
        with open(file_path, 'rb') as f:
            f.read(1024)
            
        return True, "OK"
    except Exception as e:
        return False, str(e)

def update_and_restart(target_exe, update_file, pid_to_wait):
    target_exe = os.path.abspath(target_exe)
    update_file = os.path.abspath(update_file)
    
    # Setup logging in a persistent location
    app_data = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
    log_dir = os.path.join(app_data, "MoneyTracker", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'updater.log')
    
    # Configure logging to both file and console
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    logging.info(f"--- Updater Started ---")
    logging.info(f"Target: {target_exe}")
    logging.info(f"Update: {update_file}")
    logging.info(f"PID to wait: {pid_to_wait}")
    
    def show_error(msg):
        logging.error(f"Error shown to user: {msg}")
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(msg), "Ошибка обновления", 0x10)
        except:
            pass

    # Protection against infinite restart loop
    restart_count_file = os.path.join(log_dir, "restart_count.tmp")
    try:
        count = 0
        if os.path.exists(restart_count_file):
            with open(restart_count_file, "r") as f:
                content = f.read().strip()
                if content:
                    count = int(content)
        
        if count > 3:
            logging.critical("Infinite restart loop detected! Aborting auto-restart.")
            show_error("Обнаружена циклическая ошибка запуска. Обновление приостановлено. Пожалуйста, запустите программу вручную.")
            if os.path.exists(restart_count_file):
                os.remove(restart_count_file)
            return
            
        with open(restart_count_file, "w") as f:
            f.write(str(count + 1))
    except Exception as e:
        logging.warning(f"Could not check restart count: {e}")

    # Wait for the main application to close
    if pid_to_wait:
        try:
            pid = int(pid_to_wait)
            logging.info(f"Waiting for process {pid} to exit...")
            max_wait = 30
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    import ctypes
                    SYNCHRONIZE = 0x00100000
                    process = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
                    if process:
                        res = ctypes.windll.kernel32.WaitForSingleObject(process, 1000)
                        ctypes.windll.kernel32.CloseHandle(process)
                        if res == 0: # WAIT_OBJECT_0
                            break
                    else:
                        break
                except:
                    break
                time.sleep(0.5)
            
            logging.info("Main process appears to have exited.")
        except Exception as e:
            logging.error(f"Error waiting for process: {e}")

    # Verify update file before moving
    ok, err = verify_integrity(update_file)
    if not ok:
        logging.error(f"Update file integrity check failed: {err}")
        show_error(f"Файл обновления поврежден: {err}")
        return

    # Replace file
    success = False
    backup_file = target_exe + ".bak"
    
    try:
        # Retry loop for replacement (sometimes files stay locked a bit longer)
        for i in range(10):
            try:
                logging.info(f"Attempt {i+1} to replace file...")
                
                # 1. Remove old backup
                if os.path.exists(backup_file):
                    try: os.remove(backup_file)
                    except: pass

                # 2. Rename current to backup
                if os.path.exists(target_exe):
                    os.rename(target_exe, backup_file)
                
                # 3. Move update to target
                shutil.move(update_file, target_exe)
                
                # 4. Final verify
                ok, err = verify_integrity(target_exe)
                if ok:
                    logging.info("Update applied successfully.")
                    success = True
                    break
                else:
                    raise Exception(f"Integrity check failed after move: {err}")

            except Exception as e:
                logging.warning(f"Attempt {i+1} failed: {e}")
                # Rollback if possible
                if os.path.exists(backup_file) and not os.path.exists(target_exe):
                    try: os.rename(backup_file, target_exe)
                    except: pass
                time.sleep(1)
                
    except Exception as e:
        logging.error(f"Critical error during file replacement: {e}")
        show_error(f"Не удалось обновить файл: {e}")

    if success:
        # Cleanup
        if os.path.exists(backup_file):
            try: os.remove(backup_file)
            except: pass
            
        # Restart
        try:
            logging.info(f"Restarting application: {target_exe}")
            if os.name == 'nt':
                # Use ShellExecute to ensure it runs as a normal process
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(None, "open", target_exe, None, None, 1)
            else:
                subprocess.Popen([target_exe], start_new_session=True)
            
            logging.info("Restart command issued. Updater exiting.")
            # Clear restart count on success (well, at least we tried to start)
            # Actually, the app should clear it itself on successful start, 
            # but we can reset it here as we are confident in the update.
            if os.path.exists(restart_count_file):
                os.remove(restart_count_file)
                
        except Exception as e:
            logging.error(f"Failed to restart: {e}")
            show_error(f"Обновление завершено, но не удалось запустить программу автоматически: {e}")
    else:
        logging.error("Update failed after all attempts.")
        show_error("Не удалось применить обновление. Пожалуйста, скачайте новую версию вручную.")

if __name__ == "__main__":
    # Ensure we have arguments
    if len(sys.argv) < 4:
        print("Usage: updater.exe <target_exe> <update_file> <pid>")
        sys.exit(1)
    
    try:
        target = sys.argv[1]
        update = sys.argv[2]
        pid = sys.argv[3]
        update_and_restart(target, update, pid)
    except Exception as e:
        with open("updater_crash.log", "w") as f:
            f.write(str(e))
