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
    command_received = pyqtSignal(list)      # commands list
    
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
            
            # Use raw HWID format if available, fallback to MD5 only if necessary
            hwid = "Unknown"
            try:
                if hasattr(self, 'hwid_raw'):
                    hwid = self.hwid_raw
                else:
                    # Injected or calculated
                    data = platform.node() + platform.machine() + str(uuid.getnode())
                    hwid = hashlib.md5(data.encode()).hexdigest()
            except: pass

            # Try to get the profile name (Имя)
            profile_name = "Unknown"
            if hasattr(self, 'profile_name') and self.profile_name:
                profile_name = self.profile_name

            try:
                # Use a session for check-in to handle potential cookies/headers
                resp_checkin = requests.post(checkin_url, json={
                    "client_id": self.client_id,
                    "version": self.version,
                    "username": self.username, # This is the LOGIN
                    "name": profile_name,      # This is the 'Имя'
                    "hwid": hwid,              # This is the HWID
                    "status": "Active"
                }, timeout=5)
                
                if resp_checkin.status_code == 200:
                    checkin_data = resp_checkin.json()
                    commands = checkin_data.get("commands", [])
                    if commands:
                        self.command_received.emit(commands)
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
            
            # Use a session with proper headers
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'MoneyTracker/1.0.2'
            })
            
            r = session.get(self.url, stream=True, timeout=30)
            total_length = r.headers.get('content-length')
            content_type = r.headers.get('content-type', '')
            
            if r.status_code != 200:
                self.finished.emit(False, f"HTTP ошибка: {r.status_code}")
                return
            
            # Check if response is HTML (common for error pages)
            if 'text/html' in content_type.lower():
                # Read first chunk to check content
                first_chunk = r.iter_content(chunk_size=1024, max_iterations=5)
                first_bytes = b''
                for chunk in first_chunk:
                    first_bytes += chunk
                
                if b'<!DOCTYPE' in first_bytes or b'<html' in first_bytes or b'<!doctype' in first_bytes:
                    self.finished.emit(False, "Сервер вернул HTML страницу вместо файла. Проверьте URL обновления.")
                    return
                
                # Continue with what we have
                content_so_far = first_bytes
            
            import hashlib
            h = hashlib.sha256()
            
            self.status.emit("Загрузка обновления...")
            
            # Start fresh file
            with open(self.dest_path, 'wb') as f:
                # Write first chunk if we read it
                if 'content_so_far' in dir():
                    f.write(content_so_far)
                    h.update(content_so_far)
                
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
                    # Account for bytes we already read
                    if 'content_so_far' in dir():
                        dl = len(content_so_far)
                    
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
            
            # Verify downloaded file is actually an executable
            try:
                with open(self.dest_path, 'rb') as f:
                    header = f.read(2)
                    if header != b'MZ':
                        os.remove(self.dest_path)
                        self.finished.emit(False, "Загруженный файл не является исполняемым (.exe). Проверьте URL загрузки.")
                        return
            except Exception as e:
                pass  # File validation optional
            
            # Verify signature if provided
            if self.signature:
                self.status.emit("Проверка целостности файла...")
                calc = h.hexdigest()
                if calc.lower() != self.signature.lower():
                    try:
                        os.remove(self.dest_path)
                    except:
                        pass
                    self.finished.emit(False, f"Ошибка целостности файла (Хеш-сумма не совпадает). Попробуйте скачать снова.")
                    return
            
            self.status.emit("Загрузка завершена.")
            self.finished.emit(True, self.dest_path)
        except Exception as e:
            self.finished.emit(False, f"Ошибка загрузки: {e}")

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

    def start_heartbeat(self, interval_ms=1800000):
        """Starts a periodic heartbeat/update check (default 30 mins)."""
        from PyQt6.QtCore import QTimer
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(lambda: self.check_for_updates_async(is_manual=False))
        self.heartbeat_timer.start(interval_ms)
        # Periodic check every 30 mins, initial check after 10s delay to not block startup
        QTimer.singleShot(10000, lambda: self.check_for_updates_async(is_manual=False))
        
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

        # Get Username (Login AND Profile Name)
        # Priority: 
        # 1. Login from AuthManager (Sasha1204)
        # 2. Profile Name (ter)
        
        login_user = "Unknown"
        profile_user = "Unknown"
        
        # Try to get LOGIN (Sasha1204)
        if self.auth_manager:
            if self.auth_manager.current_creds:
                 login_user = self.auth_manager.current_creds.get("login", "Unknown")
            else:
                # Try loading session if current_creds is empty
                session = self.auth_manager.load_session()
                if session:
                    login_user = session.get("login", "Unknown")
        
        # Try to get Profile Name (ter)
        if self.data_manager:
            profile = self.data_manager.get_active_profile()
            if profile and profile.get("name"):
                profile_user = profile["name"]

        # Final mapping for check-in:
        # username -> should be the Login (Sasha1204)
        # name -> should be the Profile Name (ter)
        
        # If login is missing, fallback to profile name for 'username'
        final_login = login_user if login_user != "Unknown" else profile_user
                
        # If still Unknown, prompt user for login (if in manual mode or first check)
        if final_login == "Unknown" and is_manual:
            from PyQt6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(None, "Авторизация", "Введите ваш логин для проверки обновлений:")
            if ok and text.strip():
                final_login = text.strip()
                if self.data_manager:
                    self.data_manager.set_global_data("last_login_attempt", final_login)

        self.worker = UpdateWorker(url, client_id, self.current_version, final_login, is_manual=is_manual)
        
        # Inject raw HWID and profile name for the check-in
        self.worker.hwid_raw = client_id # In our fixed _get_hwid, this is already the raw format
        self.worker.profile_name = profile_user
        
        self.worker.check_finished.connect(self.on_check_finished)
        self.worker.command_received.connect(self.process_commands)
        self.worker.start()

    def process_commands(self, commands):
        """Processes commands received from the server during check-in."""
        for cmd in commands:
            logging.info(f"[UpdateManager] Processing server command: {cmd}")
            if cmd == 'cleanup_ram':
                try:
                    from utils.mem_reduct_launcher import launch_embedded_mem_reduct
                    success, msg = launch_embedded_mem_reduct()
                    logging.info(f"[UpdateManager] Cleanup RAM result: {success}, {msg}")
                except Exception as e:
                    logging.error(f"[UpdateManager] Cleanup RAM failed: {e}")
            elif cmd == 'cleanup_temp':
                try:
                    from utils.cleanup import clean_temp
                    freed, errors, locked = clean_temp()
                    logging.info(f"[UpdateManager] Cleanup Temp result: Freed {freed} bytes, Errors {errors}, Locked {locked}")
                except Exception as e:
                    logging.error(f"[UpdateManager] Cleanup Temp failed: {e}")

    def _log_event(self, message):
        """Logs update events to standard logging instead of a file."""
        import logging
        logging.info(f"[UpdateManager] {message}")
        
    def _get_hwid(self):
        """Generates a unique Hardware ID for this machine. 
        Uses the raw bios|cpu|disk|mac format expected by the server dashboard."""
        if self.auth_manager:
            return self.auth_manager.get_hwid()
            
        try:
            # Fallback if auth_manager is not available
            data = []
            if sys.platform == 'win32':
                # BIOS UUID
                try:
                    output = subprocess.check_output('wmic csproduct get uuid', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
                    data.append(output if output else "N/A")
                except: data.append("N/A")
                
                # CPU ID
                try:
                    output = subprocess.check_output('wmic cpu get processorid', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
                    data.append(output if output else "N/A")
                except: data.append("N/A")
                
                # Disk Serial
                try:
                    output = subprocess.check_output('wmic diskdrive get serialnumber', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
                    data.append(output if output else "N/A")
                except: data.append("N/A")
                
                # MAC
                data.append(str(uuid.getnode()))
            else:
                return hashlib.md5((platform.node() + platform.machine() + str(uuid.getnode())).encode()).hexdigest()
                
            return "|".join(data)
        except Exception as e:
            print(f"Error generating HWID: {e}")
            return "N/A|N/A|N/A|" + str(uuid.getnode())

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

            # Validate URL
            if not download_url.startswith(('http://', 'https://')):
                self.update_error.emit(f"Некорректный URL загрузки: {download_url}")
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
        
        # Validate downloaded file - check if it's actually an executable
        try:
            with open(result, 'rb') as f:
                header = f.read(2)
                # Check for MZ header (Windows executable)
                if header != b'MZ':
                    # Maybe it's a PE file starting with different bytes
                    f.seek(0)
                    all_bytes = f.read(256)
                    # Check if it looks like an HTML error page
                    if b'<!DOCTYPE' in all_bytes or b'<html' in all_bytes or b'Error' in all_bytes:
                        raise Exception("Сервер вернул HTML-страницу ошибки вместо файла. Проверьте URL обновления.")
                    raise Exception(f"Загруженный файл не является исполняемым. Заголовок: {header.hex()}")
        except Exception as e:
            logging.error(f"Update file validation failed: {e}")
            self.update_error.emit(f"Ошибка проверки файла: {e}")
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
        """Restarts the application using a temporary PowerShell script, eliminating updater.exe."""
        import tempfile
        import uuid
        import logging
        import subprocess
        from datetime import datetime
        
        # Setup detailed logging for the update process
        temp_dir = tempfile.gettempdir()
        log_file = os.path.join(temp_dir, f'MoneyTracker_update_debug_{uuid.uuid4().hex[:4]}.log')
        
        def log(msg):
            print(f"[UpdateDebug] {msg}")
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} - {msg}\n")
            except:
                pass

        log("--- Integrated Update Process Started ---")
        
        current_exe = os.path.abspath(sys.executable)
        pid = os.getpid()
        exe_dir = os.path.dirname(current_exe)
        
        log(f"Current EXE: {current_exe}")
        log(f"Current PID: {pid}")
        log(f"EXE Directory: {exe_dir}")
        
        # Use provided path or default to absolute path next to exe
        if new_exe_path:
            new_exe = os.path.abspath(new_exe_path)
        else:
            new_exe = os.path.join(exe_dir, "update.tmp")
        
        log(f"New EXE (Source): {new_exe}")
        
        if not os.path.exists(new_exe):
            error_msg = f"Файл обновления не найден по пути: {new_exe}"
            log(f"FATAL ERROR: {error_msg}")
            self.update_error.emit(error_msg)
            return

        # Create a robust PowerShell script for the update process
        # 1. Wait for main process to exit
        # 2. Backup old exe
        # 3. Move new exe to target
        # 4. Restart app
        # 5. Clean up
        
        script_path = os.path.join(temp_dir, f"update_script_{uuid.uuid4().hex[:6]}.ps1")
        backup_exe = f"{current_exe}.bak"
        
        ps_script = f"""
$ErrorActionPreference = "Stop"
$LogFile = "{log_file.replace('\\', '\\\\')}"

function Write-Log($Message) {{
    $Time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Time - [PS-Script] $Message" | Out-File -FilePath $LogFile -Append -Encoding UTF8
}}

Write-Log "PowerShell update script started"
Write-Log "Waiting for PID {pid} to exit..."

# 1. Wait for process to exit
$MaxRetries = 40
$RetryCount = 0
while ((Get-Process -Id {pid} -ErrorAction SilentlyContinue) -and ($RetryCount -lt $MaxRetries)) {{
    Start-Sleep -Milliseconds 500
    $RetryCount++
}}

if ($RetryCount -ge $MaxRetries) {{
    Write-Log "Timeout waiting for process {pid} to exit. Aborting."
    exit 1
}}

Write-Log "Process {pid} exited. Proceeding with file replacement."

try {{
    # 2. Backup current exe
    if (Test-Path "{current_exe.replace('\\', '\\\\')}") {{
        Write-Log "Creating backup: {backup_exe.replace('\\', '\\\\')}"
        Move-Item -Path "{current_exe.replace('\\', '\\\\')}" -Destination "{backup_exe.replace('\\', '\\\\')}" -Force
    }}

    # 3. Move new exe to original path
    Write-Log "Moving new EXE from {new_exe.replace('\\', '\\\\')} to {current_exe.replace('\\', '\\\\')}"
    Move-Item -Path "{new_exe.replace('\\', '\\\\')}" -Destination "{current_exe.replace('\\', '\\\\')}" -Force

    Write-Log "Update successful. Waiting 5 seconds for filesystem to stabilize before restart..."
    Start-Sleep -Seconds 5
    
    # 4. Restart application
    Start-Process -FilePath "{current_exe.replace('\\', '\\\\')}"
    
    # Clean up backup on success after a short delay (optional, but keep it for safety during restart)
    Start-Sleep -Seconds 2
    if (Test-Path "{backup_exe.replace('\\', '\\\\')}") {{
        Remove-Item "{backup_exe.replace('\\', '\\\\')}" -Force
        Write-Log "Backup cleaned up."
    }}

}} catch {{
    Write-Log "ERROR during update: $($_.Exception.Message)"
    
    # 5. Rollback if possible
    if (Test-Path "{backup_exe.replace('\\', '\\\\')}" -and !(Test-Path "{current_exe.replace('\\', '\\\\')}")) {{
        Write-Log "Attempting rollback..."
        Move-Item -Path "{backup_exe.replace('\\', '\\\\')}" -Destination "{current_exe.replace('\\', '\\\\')}" -Force
        Write-Log "Rollback complete. Restarting old version."
        Start-Process -FilePath "{current_exe.replace('\\', '\\\\')}"
    }}
    
    # Show error to user via MsgBox
    $Msg = "Ошибка при обновлении: $($_.Exception.Message). Попробуйте запустить программу от имени администратора."
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Msg, "Ошибка обновления", 'OK', 'Error')
}} finally {{
    Write-Log "Script finished. Self-deleting."
    # The script cannot delete itself easily while running, but we can schedule deletion
    # or just let it stay in Temp.
}}
"""
        
        try:
            with open(script_path, "w", encoding="utf-8-sig") as f: # Use UTF8 with BOM for PS
                f.write(ps_script)
            
            log(f"PowerShell script created at: {script_path}")
            
            # Launch PowerShell script hidden
            # -ExecutionPolicy Bypass allows running the script
            # -WindowStyle Hidden hides the console window
            cmd = [
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-WindowStyle", "Hidden",
                "-File", script_path
            ]
            
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            log("PowerShell script launched. Exiting application...")
            
            # Small delay to ensure Popen is processed
            import time
            time.sleep(1)
            sys.exit(0)
            
        except Exception as e:
            log(f"Failed to launch update script: {e}")
            self.update_error.emit(f"Не удалось запустить процесс обновления: {e}\nЛог: {log_file}")
            return

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
