import requests
import os
import json
import logging
import hashlib
import uuid
import sys
import subprocess
import platform
import shutil
import tempfile
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap

class UpdateWorker(QThread):
    check_finished = pyqtSignal(bool, dict) # success, info
    
    def __init__(self, server_url, client_id, version, username="Unknown", is_manual=False):
        super().__init__()
        self.server_url = server_url
        self.client_id = client_id
        self.version = version
        self.username = username
        self.is_manual = is_manual

    def run(self):
        try:
            # 1. Check-in
            checkin_url = f"{self.server_url}/client_checkin"
            try:
                requests.post(checkin_url, json={
                    "client_id": self.client_id,
                    "version": self.version,
                    "username": self.username,
                    "status": "Active"
                }, timeout=3)
            except Exception as e:
                logging.warning(f"[UpdateWorker] Check-in failed: {e}")
                # Non-critical, continue to update check

            # 2. Check for updates
            update_url = f"{self.server_url}/update_info"
            resp = requests.get(update_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                data["is_manual"] = self.is_manual  # Inject is_manual flag
                self.check_finished.emit(True, data)
            else:
                self.check_finished.emit(False, {"is_manual": self.is_manual})
        except requests.exceptions.ConnectionError:
            self.check_finished.emit(False, {"error": "Ошибка подключения к серверу. Проверьте интернет или настройки URL.", "is_manual": self.is_manual})
        except requests.exceptions.Timeout:
            self.check_finished.emit(False, {"error": "Превышено время ожидания ответа от сервера.", "is_manual": self.is_manual})
        except Exception as e:
            self.check_finished.emit(False, {"error": f"Произошла непредвиденная ошибка: {str(e)}", "is_manual": self.is_manual})

class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str) # success, message/path

    def __init__(self, url, dest_path, signature=None):
        super().__init__()
        self.url = url
        self.dest_path = dest_path
        self.signature = signature
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.status.emit("Соединение с сервером...")
            r = requests.get(self.url, stream=True, timeout=10)
            total_length = r.headers.get('content-length')
            
            if r.status_code != 200:
                self.finished.emit(False, f"HTTP {r.status_code}")
                return

            import hashlib
            h = hashlib.sha256()
            
            self.status.emit("Загрузка обновления...")
            with open(self.dest_path, 'wb') as f:
                if total_length is None: # no content length header
                    for data in r.iter_content(chunk_size=4096):
                        if self._is_cancelled:
                            f.close()
                            try:
                                os.remove(self.dest_path)
                            except:
                                pass
                            self.finished.emit(False, "Cancelled")
                            return
                        f.write(data)
                        h.update(data)
                else:
                    dl = 0
                    total_length = int(total_length)
                    for data in r.iter_content(chunk_size=4096):
                        if self._is_cancelled:
                            f.close()
                            try:
                                os.remove(self.dest_path)
                            except:
                                pass
                            self.finished.emit(False, "Cancelled")
                            return
                        dl += len(data)
                        f.write(data)
                        h.update(data)
                        if total_length:
                            percent = int(100 * dl / total_length)
                            self.progress.emit(percent)
            
            # Verify signature if provided
            if self.signature:
                self.status.emit("Проверка целостности файла...")
                calc = h.hexdigest()
                if calc.lower() != self.signature.lower():
                    try:
                        os.remove(self.dest_path)
                    except:
                        pass
                    self.finished.emit(False, f"Bad signature: expected {self.signature}, got {calc}")
                    return
            
            self.status.emit("Загрузка завершена.")
            self.finished.emit(True, self.dest_path)
        except Exception as e:
            self.finished.emit(False, str(e))

class UpdateManager(QObject):
    update_available = pyqtSignal(dict)
    update_progress = pyqtSignal(int)
    update_status = pyqtSignal(str)
    update_error = pyqtSignal(str)
    update_ready = pyqtSignal(str)  # Emits path to update file
    update_finished = pyqtSignal(str) # Compatibility alias
    check_completed = pyqtSignal(dict) # New signal for check completion status
    
    def __init__(self, data_manager, version=None, auth_manager=None):
        super().__init__()
        from version import VERSION
        self.data_manager = data_manager
        self.auth_manager = auth_manager
        self.current_version = version if version else VERSION
        self.heartbeat_timer = None
        self.download_worker = None
        
    def stop(self):
        """Stops the heartbeat timer and any active downloads."""
        if self.heartbeat_timer and self.heartbeat_timer.isActive():
            self.heartbeat_timer.stop()
            print("[UpdateManager] Heartbeat stopped.")
        
        self.cancel_download()

    def start_heartbeat(self, interval_ms=30000):
        """Starts a periodic heartbeat/update check."""
        from PyQt6.QtCore import QTimer
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(lambda: self.check_for_updates_async(is_manual=False))
        self.heartbeat_timer.start(interval_ms)
        # Immediate check removed to disable mandatory checks on launch
        
    def check_for_updates_async(self, is_manual=False):
        url = self.data_manager.get_global_data("update_server_url", "")
        if not url:
            # Default fallback
            url = "https://dargon-52si.onrender.com"
        
        # Auto-correct local HTTPS to HTTP to prevent common user error
        if url.startswith("https://127.0.0.1") or url.startswith("https://localhost"):
            print(f"Warning: Correcting URL {url} to use HTTP for local server.")
            url = url.replace("https://", "http://")
            
        # Strip /dashboard if accidentally copied by user
        if "/dashboard" in url:
            # Silently fix or log as info instead of repetitive warning
            url = url.replace("/dashboard", "")
            # Update the stored URL to prevent future warnings/fixes
            self.data_manager.set_global_data("update_server_url", url)
            
        url = url.rstrip('/')
            
        print(f"Using Update Server URL: {url}")
        
        # Log event
        initiator = "User" if is_manual else "System"
        self._log_event(f"Update check initiated by {initiator}")

        # Get Client ID (HWID based)
        # We use hardware ID to prevent issues when copying the app folder to another PC
        client_id = self._get_hwid()
        # Save it just for reference/debugging, but we always regenerate/verify it
        self.data_manager.set_global_data("client_id", client_id)

        # Get Username (Login OR Profile Name)
        username = "Unknown"
        
        if self.auth_manager and self.auth_manager.current_creds:
             login = self.auth_manager.current_creds.get("login")
             if login and login != "Unknown":
                 username = login
        
        # Fallback to Profile Name if login is still Unknown
        if username == "Unknown" and self.data_manager:
            profile = self.data_manager.get_active_profile()
            if profile and profile.get("name") and profile["name"] != "Unknown":
                username = profile["name"]
                
        # If still Unknown, prompt user for login (if in manual mode or first check)
        if username == "Unknown" and is_manual:
            from PyQt6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(None, "Авторизация", "Введите ваш логин для проверки обновлений:")
            if ok and text.strip():
                username = text.strip()
                # Optionally save this to data_manager for future
                if self.data_manager:
                    self.data_manager.set_global_data("last_login_attempt", username)

        self.worker = UpdateWorker(url, client_id, self.current_version, username, is_manual=is_manual)
        self.worker.check_finished.connect(self.on_check_finished)
        self.worker.start()

    def _log_event(self, message):
        """Logs update events to standard logging instead of a file."""
        import logging
        logging.info(f"[UpdateManager] {message}")
        
    def _get_hwid(self):
        """Generates a unique Hardware ID for this machine."""
        try:
            # Combine multiple hardware/system identifiers
            # node: Network name (hostname)
            # machine: Machine type (e.g. 'AMD64')
            # getnode: MAC address
            data = platform.node() + platform.machine() + str(uuid.getnode())
            
            # On Windows, we can try to get more specific UUID
            if sys.platform == 'win32':
                try:
                    # Try PowerShell first (more modern/reliable)
                    cmd = 'powershell -NoProfile -Command "Get-CimInstance -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"'
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
                    if output:
                        data += output
                except:
                    try:
                        # Fallback to wmic (older systems), suppress stderr
                        output = subprocess.check_output('wmic csproduct get uuid', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
                        if output:
                            data += output
                    except:
                        pass
            
            return hashlib.md5(data.encode()).hexdigest()
        except Exception as e:
            print(f"Error generating HWID: {e}")
            # Fallback to random UUID if HWID fails (should remain constant for this session)
            return str(uuid.uuid4())

    def on_check_finished(self, success, data):
        is_manual = data.get("is_manual", False)
        
        # Prepare result dict for check_completed signal
        result_info = {
            "success": success,
            "is_manual": is_manual,
            "update_found": False,
            "message": ""
        }

        if success:
            server_ver = data.get("version")
            force = data.get("force_update", False)
            
            logging.info(f"[UpdateManager] Check result: Server={server_ver}, Local={self.current_version}, Force={force}, Manual={is_manual}")
            
            should_update = False
            
            # Semantic version comparison
            try:
                def parse_version(v):
                    # Robust semantic versioning parser (MAJOR.MINOR.PATCH)
                    # Removes any prefix like 'v' or suffix like '-beta'
                    v_clean = v.lower().strip().lstrip('v').split('-')[0].split('+')[0]
                    parts = []
                    for x in v_clean.split('.'):
                        try:
                            parts.append(int(x))
                        except ValueError:
                            parts.append(0)
                    # Ensure at least 3 parts (major, minor, patch)
                    while len(parts) < 3:
                        parts.append(0)
                    return parts[:3]
                
                server_parts = parse_version(server_ver)
                local_parts = parse_version(self.current_version)
                
                if server_parts > local_parts:
                    logging.info(f"[UpdateManager] New version available: Server {server_ver} > Local {self.current_version}")
                    should_update = True
                elif server_parts == local_parts:
                    msg = "у вас установлена последняя версия и обновления не требуется"
                    logging.info(f"[UpdateManager] {msg}")
                    result_info["message"] = msg
                else:
                    logging.info(f"[UpdateManager] Local version is newer or equal: Server {server_ver} <= Local {self.current_version}")
            except Exception as e:
                logging.error(f"[UpdateManager] Version comparison error: {e}")
                # Fallback to simple equality check
                if server_ver and server_ver != self.current_version:
                    should_update = True

            if force and server_ver:
                 logging.info(f"[UpdateManager] Force update active. Re-validating version {server_ver}")
                 should_update = True

            if should_update:
                self._log_event(f"Update available: {server_ver} (Force: {force})")
                self.update_available.emit(data)
                result_info["update_found"] = True
                result_info["server_version"] = server_ver
            elif is_manual:
                # If no update was found but it's a manual check, provide the message
                if not result_info["message"]:
                    result_info["message"] = "у вас установлена последняя версия и обновления не требуется"
                
                print(f"[UpdateManager] {result_info['message']}")
                self._log_event(result_info["message"])
                result_info["server_version"] = server_ver
            else:
                print("[UpdateManager] No update needed.")
                self._log_event("No update needed")
                
            # Check for global resources (photos)
            resources = data.get("resources", {})
            self.sync_resources(resources)
        else:
            error_msg = data.get("error", "Unknown error")
            logging.error(f"[UpdateManager] Check failed: {error_msg}")
            result_info["message"] = f"Ошибка проверки: {error_msg}"
            
        # Emit completion signal
        self.check_completed.emit(result_info)
            
    def download_and_install_update(self, download_url=None, force_update=False, notes=None, signature=None):
        """
        Initiates the download and installation process.
        This method is called by MainWindow after user confirmation.
        """
        try:
            logging.info(f"[UpdateManager] download_and_install_update called. URL: {download_url}, Force: {force_update}, Signature: {bool(signature)}")
            print(f"[UpdateManager] download_and_install_update called. URL: {download_url}") # Console debug
            
            if not download_url:
                # Fallback logic
                base_url = self.data_manager.get_global_data("update_server_url", "https://dargon-52si.onrender.com")
                download_url = f"{base_url.rstrip('/')}/download"
                logging.warning(f"[UpdateManager] No URL provided, using fallback: {download_url}")

            # Construct info dict for perform_update
            info = {
                "download_url": download_url,
                "signature": signature,
                "force_update": force_update,
                "notes": notes
            }
            
            self.perform_update(info)
            
        except Exception as e:
            error_msg = f"Critical error in update initiation: {str(e)}"
            logging.error(f"[UpdateManager] {error_msg}")
            self.update_error.emit(error_msg)

    def perform_update(self, info):
        try:
            download_url = info.get("download_url")
            signature = info.get("signature")
            
            if not getattr(sys, 'frozen', False):
                # Allow update simulation in dev mode for testing if needed, 
                # but generally warn user
                print("Update not supported in development mode (would replace python.exe).")
                # self.update_error.emit("Обновление невозможно в режиме разработки.")
                # return
                # For testing purposes, we might want to proceed with download but not restart?
                # Or just let it fail at restart. 
                pass

            if not download_url:
                self.update_error.emit("URL загрузки не найден!")
                return

            print(f"Downloading update from {download_url}...")
            
            # Use absolute path for update file to avoid CWD issues
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
            
            # Ensure write permissions
            if not os.access(exe_dir, os.W_OK):
                self.update_error.emit(f"Нет прав на запись в папку {exe_dir}. Запустите от имени администратора.")
                return

            update_path = os.path.join(exe_dir, "update.tmp")

            # Extended logging for diagnostics
            logging.info(f"Update Init: exe_dir={exe_dir}")
            logging.info(f"Update Init: update_path={update_path}")
            
            # Download to a temp file
            self.download_worker = DownloadWorker(download_url, update_path, signature=signature)
            self.download_worker.progress.connect(self.update_progress)
            self.download_worker.status.connect(self.update_status)
            self.download_worker.finished.connect(self.on_download_finished)
            self.download_worker.start()
            
        except Exception as e:
            logging.error(f"[UpdateManager] perform_update failed: {e}")
            self.update_error.emit(f"Ошибка при запуске обновления: {e}")

        
    def on_download_finished(self, success, result):
        if not success:
            if result == "Cancelled":
                print("Update cancelled by user.")
                return
            print(f"Download failed: {result}")
            self.update_error.emit(f"Ошибка загрузки: {result}")
            return
            
        print("Download complete. Ready to restart.")
        self.update_ready.emit(result)
        self.update_finished.emit(result)

    def cancel_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.download_worker.wait()
            self.download_worker = None
            print("Download cancelled.")

    def restart_application(self, new_exe_path=None):
        """Restarts the application using the updater."""
        import tempfile
        import uuid
        import shutil
        import logging
        
        # Setup detailed logging for the update process
        temp_dir = tempfile.gettempdir()
        log_file = os.path.join(temp_dir, f'MoneyTracker_update_debug_{uuid.uuid4().hex[:4]}.log')
        
        # Simple logger for this method
        def log(msg):
            print(f"[UpdateDebug] {msg}")
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} - {msg}\n")
            except:
                pass

        from datetime import datetime
        log("--- Update Restart Process Started ---")
        
        current_exe = sys.executable
        pid = os.getpid()
        log(f"Current EXE: {current_exe}")
        log(f"Current PID: {pid}")
        log(f"Is Frozen: {getattr(sys, 'frozen', False)}")
        
        # Use provided path or default to absolute path next to exe
        if new_exe_path:
            new_exe = os.path.abspath(new_exe_path)
        else:
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
            new_exe = os.path.join(exe_dir, "update.tmp")
        
        log(f"Target New EXE: {new_exe}")
        
        # Determine updater path
        updater_path = None
        
        if getattr(sys, 'frozen', False):
             # If compiled
             meipass = getattr(sys, '_MEIPASS', '')
             
             # 1. Check for bundled updater.exe in _MEIPASS (extracted alongside main exe)
             bundled_updater = os.path.join(meipass, 'updater.exe')
             
             # 2. Try to find/use updater.py if it was bundled (running via python)
             bundled_py = os.path.join(meipass, 'updater.py')
             
             # 3. Check for external updater.exe (next to main exe)
             exe_dir = os.path.dirname(current_exe)
             ext_exe = os.path.join(exe_dir, 'updater.exe')
             
             if os.path.exists(bundled_updater):
                 updater_path = bundled_updater
                 log(f"Found bundled updater.exe: {updater_path}")
             elif os.path.exists(bundled_py):
                 updater_path = bundled_py
                 log(f"Found bundled updater.py: {updater_path}")
             elif os.path.exists(ext_exe):
                 updater_path = ext_exe
                 log(f"Found external updater.exe: {updater_path}")
             else:
                 log(f"Updater not found. Searched: bundled_updater={bundled_updater}, bundled_py={bundled_py}, ext_exe={ext_exe}")
        else:
            # If dev, look for updater.py in root (cwd)
            updater_path = os.path.join(os.getcwd(), 'updater.py')
            log(f"Dev mode: checking for {updater_path}")
        
        # EMERGENCY FALLBACK: If nothing found, try to locate updater.py in same dir as current script
        if not updater_path or not os.path.exists(updater_path):
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(curr_dir)
            alt_path_py = os.path.join(root_dir, 'updater.py')
            alt_path_exe = os.path.join(root_dir, 'updater.exe')
            if os.path.exists(alt_path_exe):
                updater_path = alt_path_exe
                log(f"Fallback: Found updater.exe in root: {updater_path}")
            elif os.path.exists(alt_path_py):
                updater_path = alt_path_py
                log(f"Fallback: Found updater.py in root: {updater_path}")

        log(f"Final Resolved updater path: {updater_path}")
        
        if not updater_path or not os.path.exists(updater_path):
             error_msg = f"Файл обновления (updater) не найден!"
             log(f"FATAL ERROR: {error_msg}")
             self.update_error.emit(f"{error_msg}\nЛог: {log_file}")
             return

        # Pass current_exe as absolute path just in case
        current_exe = os.path.abspath(current_exe)
        new_exe = os.path.abspath(new_exe)

        log(f"Launching updater: {updater_path}")
        log(f"Args: {current_exe}, {new_exe}, {pid}")

        # Determine how to launch
        is_python = updater_path.endswith('.py')
        
        try:
            if is_python:
                # Launch via python interpreter
                subprocess.Popen([sys.executable, updater_path, current_exe, new_exe, str(pid)], 
                                 creationflags=0x00000008 if sys.platform == 'win32' else 0)
                log("Updater script launched successfully")
            else:
                # Launch EXE directly
                subprocess.Popen([updater_path, current_exe, new_exe, str(pid)], 
                                 cwd=os.path.dirname(updater_path),
                                 creationflags=0x00000008 if sys.platform == 'win32' else 0)
                log("Updater EXE launched successfully")
        except Exception as e:
            log(f"Failed to launch updater: {e}")
            self.update_error.emit(f"Не удалось запустить процесс обновления: {e}\nЛог: {log_file}")
            return
        
        log("--- Application exiting to allow update ---")
        # Exit immediately
        import time
        time.sleep(1) # Give Popen a moment
        sys.exit(0)

    def sync_resources(self, resources):
        # Logic to download new images if needed
        med_img_url = resources.get("med_help_image")
        if med_img_url:
             last_url = self.data_manager.get_global_data("last_med_img_url", "")
             if med_img_url != last_url:
                 try:
                     resp = requests.get(med_img_url, timeout=10)
                     if resp.status_code == 200:
                         pixmap = QPixmap()
                         pixmap.loadFromData(resp.content)
                         
                         rel_path = self.data_manager.save_pixmap_image(pixmap)
                         if rel_path:
                             self.data_manager.set_global_data("med_image_path", rel_path)
                             self.data_manager.set_global_data("last_med_img_url", med_img_url)
                 except Exception as e:
                     print(f"Failed to sync resources: {e}")
