import sys
import os
import time
import subprocess
import logging
import shutil
import tempfile

def update_and_restart(target_exe, update_file, pid_to_wait):
    target_exe = os.path.abspath(target_exe)
    update_file = os.path.abspath(update_file)
    
    # Setup logging
    temp_dir = tempfile.gettempdir()
    log_file = os.path.join(temp_dir, 'MoneyTracker_updater.log')
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')
    logging.info(f"Updater started. Target: {target_exe}, Update: {update_file}, PID: {pid_to_wait}")
    
    def show_error(msg):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(msg), "Ошибка обновления", 0x10)
        except:
            pass

    # Wait for the main application to close
    if pid_to_wait:
        try:
            pid = int(pid_to_wait)
            logging.info(f"Waiting for process {pid} to exit...")
            max_wait = 30
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    # Check if process exists. On Windows, this is a bit rough but works.
                    import ctypes
                    SYNCHRONIZE = 0x00100000
                    process = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
                    if process:
                        ctypes.windll.kernel32.WaitForSingleObject(process, 1000)
                        ctypes.windll.kernel32.CloseHandle(process)
                        # If we are here, wait returned or timed out. 
                        # Let's simple check if we can rename the target file, that's the ultimate test.
                        if not os.path.exists(target_exe):
                            break
                        try:
                            os.rename(target_exe, target_exe + ".bak")
                            os.rename(target_exe + ".bak", target_exe)
                            # If we succeeded, the file is not locked!
                            break 
                        except OSError:
                            logging.info("File still locked...")
                            time.sleep(1)
                            continue
                    else:
                        break
                except Exception as e:
                    logging.error(f"Error checking process: {e}")
                    time.sleep(1)
            
            logging.info("Process exited or file unlocked.")
        except Exception as e:
            logging.error(f"Error waiting for process: {e}")
            show_error(f"Ошибка при ожидании закрытия программы: {e}")
            return

    # Verify environment
    try:
        # Check disk space in temp (need at least 200MB for safety)
        if hasattr(os, 'statvfs'): # Linux/Unix
            st = os.statvfs(temp_dir)
            free = st.f_bavail * st.f_frsize
        else: # Windows
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            total_free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(temp_dir), 
                ctypes.byref(free_bytes), ctypes.byref(total_bytes), ctypes.byref(total_free_bytes))
            free = free_bytes.value
        
        logging.info(f"Free space in temp: {free / (1024*1024):.2f} MB")
        if free < 200 * 1024 * 1024:
            logging.warning("Low disk space in temp directory.")
    except Exception as e:
        logging.warning(f"Could not check disk space: {e}")

    # Replace file
    success = False
    try:
        # Verify update file integrity (basic check)
        if not os.path.exists(update_file) or os.path.getsize(update_file) == 0:
            logging.error("Update file is missing or empty.")
            show_error("Файл обновления поврежден или отсутствует.")
            return

        # Retry loop for replacement
        for i in range(5):
            try:
                # 1. Backup existing file
                backup_file = target_exe + ".bak"
                if os.path.exists(target_exe):
                    if os.path.exists(backup_file):
                        try:
                            os.remove(backup_file)
                        except OSError:
                            logging.warning("Could not remove old backup. overwriting...")
                    
                    try:
                        os.rename(target_exe, backup_file)
                    except OSError as e:
                        logging.warning(f"Could not rename target to backup: {e}")
                        # If we can't rename, we likely can't overwrite.
                        time.sleep(1)
                        continue
                
                try:
                    # 2. Move new file to target
                    # Use shutil.move for cross-filesystem support
                    shutil.move(update_file, target_exe)
                    
                    # 3. Verify the move
                    if os.path.exists(target_exe) and os.path.getsize(target_exe) > 0:
                        logging.info("File replaced successfully.")
                        success = True
                        
                        # We keep the backup for safety until successful launch (which we can't verify here easily)
                        # But we can leave it.
                        break
                    else:
                        raise Exception("Move appeared successful but target file is missing or empty.")

                except Exception as e:
                    logging.error(f"Failed to move new file to target: {e}")
                    # ROLLBACK: Try to restore backup
                    if os.path.exists(backup_file):
                        try:
                            logging.info("Attempting rollback...")
                            # Ensure target is clean before restoring
                            if os.path.exists(target_exe):
                                try:
                                    os.remove(target_exe)
                                except OSError as rem_e:
                                    logging.error(f"Failed to remove partial target during rollback: {rem_e}")
                            
                            # Restore backup
                            os.rename(backup_file, target_exe)
                            logging.info("Rollback successful.")
                        except Exception as rollback_e:
                            logging.critical(f"Rollback failed: {rollback_e}")
                            show_error(f"Критическая ошибка! Не удалось восстановить резервную копию: {rollback_e}")
                    raise e 
            except Exception as e:
                logging.warning(f"Attempt {i+1} failed: {e}")
                time.sleep(1)
                
    except Exception as e:
        logging.error(f"Failed to replace file: {e}")
        show_error(f"Не удалось заменить файл программы: {e}")
    
    # Cleanup update file if it still exists (failure case)
    if os.path.exists(update_file):
        try:
            os.remove(update_file)
            logging.info("Cleaned up leftover update file.")
        except Exception as e:
            logging.error(f"Failed to cleanup update file: {e}")

    if not success:
        logging.error("Update failed. Exiting.")
        show_error("Обновление не удалось. Попробуйте скачать новую версию вручную.")
        return

    # Final integrity check of the replaced file
    if os.path.exists(target_exe):
        size = os.getsize(target_exe)
        if size < 1000000: # Typical minimal size for this EXE
            logging.error(f"Integrity check failed: Replaced EXE size too small ({size} bytes)")
            show_error("Критическая ошибка: Файл приложения поврежден после замены. Попробуйте переустановить программу.")
            return
        logging.info(f"Integrity check passed. Final size: {size} bytes")
    
    # Restart application
    try:
        logging.info(f"Restarting {target_exe}...")
        # Use start to detach properly and ensure window shows up
        if os.name == 'nt':
             os.startfile(target_exe)
        else:
             subprocess.Popen([target_exe])
    except Exception as e:
        logging.error(f"Failed to restart: {e}")
        show_error(f"Обновление успешно, но не удалось запустить программу: {e}")

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
