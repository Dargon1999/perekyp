import sys
import platform
import subprocess
import uuid
import requests
import json
import os
import logging
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, server_url=None):
        # Config from User
        # TODO: SECURITY RISK - API Key is hardcoded. Use environment variables or a secure backend proxy.
        self.api_key = "AIzaSyAps_XRnofsuusFDXD6cxDWTnk0bJ0kUaE"
        self.project_id = "generatormail-e478c"
        self.base_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"
        
        app_data = os.getenv("APPDATA") or os.path.expanduser("~")
        self.session_file = os.path.join(app_data, "MoneyTracker", "auth_session.json")
        self.hwid = self.get_hwid()
        self.current_creds = None
        
    def get_hwid_map(self):
        """Generates a map of hardware identifiers for fuzzy matching."""
        hwid_map = {
            "bios": "N/A",
            "cpu": "N/A",
            "disk": "N/A",
            "mac": str(uuid.getnode())
        }
        
        try:
            if platform.system() == "Windows":
                # BIOS UUID
                try:
                    cmd = 'wmic csproduct get uuid'
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
                    lines = [line.strip() for line in output.split('\n') if line.strip()]
                    if len(lines) > 1 and lines[1] != "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF":
                        hwid_map["bios"] = lines[1]
                except: pass

                # CPU ID
                try:
                    cmd = 'wmic cpu get processorid'
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
                    lines = [line.strip() for line in output.split('\n') if line.strip()]
                    if len(lines) > 1:
                        hwid_map["cpu"] = lines[1]
                except: pass

                # Disk Serial
                try:
                    cmd = 'wmic diskdrive get serialnumber'
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
                    lines = [line.strip() for line in output.split('\n') if line.strip()]
                    if len(lines) > 1:
                        hwid_map["disk"] = lines[1]
                except: pass
        except Exception as e:
            logger.error(f"HWID map generation error: {e}")
            
        return hwid_map

    def get_hwid(self):
        """Returns a string representation of the HWID map for storage."""
        h = self.get_hwid_map()
        # Format: bios|cpu|disk|mac
        return f"{h['bios']}|{h['cpu']}|{h['disk']}|{h['mac']}"

    def compare_hwids(self, stored_hwid, current_hwid):
        """
        Compares two HWID strings and returns similarity score and details.
        Returns (is_match, match_count, total_count)
        """
        if not stored_hwid or "|" not in stored_hwid:
            return stored_hwid == current_hwid, 0, 0
            
        s_parts = stored_hwid.split('|')
        c_parts = current_hwid.split('|')
        
        if len(s_parts) != len(c_parts):
            return False, 0, len(c_parts)
            
        matches = 0
        total = 0
        details = []
        labels = ["BIOS", "CPU", "Disk", "MAC"]
        
        for i in range(len(s_parts)):
            if s_parts[i] != "N/A" and c_parts[i] != "N/A":
                total += 1
                if s_parts[i] == c_parts[i]:
                    matches += 1
                    details.append(f"{labels[i]}: OK")
                else:
                    details.append(f"{labels[i]}: CHANGED")
            else:
                details.append(f"{labels[i]}: N/A")
                
        logger.info(f"HWID Check Details: {', '.join(details)} (Matches: {matches}/{total})")
        
        # Match if at least 2 components match (or 1 if total is 1)
        is_match = matches >= 2 or (total <= 1 and matches == total)
        return is_match, matches, total

    def validate_key(self, login, password, key):
        """Validates key with Firebase. Supports soft migration and re-bind."""
        logger.info(f"Auth: Starting validation for user '{login}' with key '{key[:5]}...'")
        current_hwid = self.get_hwid()
        
        try:
            # 1. Fetch Key Document
            doc_url = f"{self.base_url}/keys/{key}?key={self.api_key}"
            response = requests.get(doc_url, timeout=10)

            if response.status_code == 404:
                return False, "Неверный ключ лицензии.", None
            
            if response.status_code != 200:
                return False, f"Ошибка сервера: {response.status_code}", None

            data = response.json()
            fields = data.get("fields", {})
            
            # Helper to get field value safely
            def get_field(name, type_str="stringValue"):
                return fields.get(name, {}).get(type_str)

            # --- BAN CHECK ---
            # Check Firebase 'is_active' and also check the main server status via checkin
            is_active_fb = fields.get("is_active", {}).get("booleanValue", True)
            if not is_active_fb:
                 return False, "Ваш ключ был деактивирован администратором.", None

            # --- Check-in with Main Server to sync status and check for Ban ---
            try:
                # Get more info for check-in
                profile_name = "Unknown"
                app_version = "1.0.4"
                try:
                    from version import VERSION
                    app_version = VERSION
                except: pass

                checkin_url = "https://dargon-52si.onrender.com/api/client/checkin"
                checkin_resp = requests.post(checkin_url, json={
                    "client_id": self.hwid,
                    "version": app_version,
                    "username": login,
                    "name": profile_name,
                    "hwid": self.hwid
                }, timeout=5)
                
                if checkin_resp.status_code == 403:
                    ban_data = checkin_resp.json()
                    return False, ban_data.get("message", "Ваш доступ заблокирован."), None
                elif checkin_resp.status_code == 402:
                    expired_data = checkin_resp.json()
                    return False, expired_data.get("message", "Срок лицензии истек."), None
            except Exception as e:
                logger.warning(f"Checkin during validation failed: {e}")
                # Don't block if main server is down, fallback to Firebase logic

            stored_hwid = get_field("hwid")
            stored_login = get_field("login")
            stored_password = get_field("password")
            rebind_count = int(fields.get("rebind_count", {}).get("integerValue", 0))

            # 2. Activation / Re-bind Logic
            if stored_hwid:
                # Fuzzy matching
                is_match, matches, total = self.compare_hwids(stored_hwid, current_hwid)
                
                if is_match:
                    logger.info(f"Auth: HWID match found ({matches}/{total}).")
                    if stored_login and (stored_login != login or stored_password != password):
                        return False, "Неверный логин или пароль.", None
                    
                    # If hardware changed slightly but still matches, update it silently
                    if current_hwid != stored_hwid:
                        logger.info("Auth: Minor hardware change detected. Updating HWID record.")
                        self._perform_rebind(key, login, password, rebind_count, current_hwid)
                else:
                    # Different PC or major hardware change
                    logger.warning(f"Auth: HWID mismatch. Stored: {stored_hwid}, Current: {current_hwid}")
                    
                    # If it's the same login/pass, allow re-bind automatically (NO 24h delay)
                    if stored_login == login and stored_password == password:
                        logger.info("Auth: HWID changed significantly but credentials match. Performing automatic re-bind.")
                        self._perform_rebind(key, login, password, rebind_count + 1, current_hwid)
                    else:
                        return False, "Ключ активирован на другом ПК. Для переноса введите верные логин/пароль.", None
            else:
                # First Activation
                self._perform_activation(key, login, password, fields, current_hwid)

            # 3. Expiration Check
            expires_at_str = get_field("expires_at")
            if expires_at_str and expires_at_str != "Lifetime":
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', ''))
                if datetime.now() > expires_at:
                    return False, f"Лицензия истекла {expires_at.strftime('%d.%m.%Y')}.", None

            self.save_session(login, password, key)
            return True, "Успешная авторизация", expires_at_str or "Lifetime"
                
        except Exception as e:
            logger.error(f"Auth error: {e}", exc_info=True)
            return self.check_grace_period(login, password, key)

    def _perform_rebind(self, key, login, password, new_count, new_hwid=None):
        """Updates HWID and re-bind metadata."""
        hwid_to_save = new_hwid or self.hwid
        update_mask = "updateMask.fieldPaths=hwid&updateMask.fieldPaths=last_rebind_at&updateMask.fieldPaths=rebind_count"
        url = f"{self.base_url}/keys/{key}?key={self.api_key}&{update_mask}"
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        patch_data = {
            "fields": {
                "hwid": {"stringValue": hwid_to_save},
                "last_rebind_at": {"stringValue": now_str},
                "rebind_count": {"integerValue": new_count}
            }
        }
        requests.patch(url, json=patch_data, timeout=10)

    def _perform_activation(self, key, login, password, fields, initial_hwid=None):
        """Initial activation logic."""
        hwid_to_save = initial_hwid or self.hwid
        duration_days = int(fields.get("duration_days", {}).get("integerValue") or fields.get("duration_days", {}).get("stringValue", "7"))
        now = datetime.now()
        expires_at = now + timedelta(days=duration_days)
        expires_str = expires_at.isoformat() + "Z"
        
        update_mask = "updateMask.fieldPaths=hwid&updateMask.fieldPaths=login&updateMask.fieldPaths=password&updateMask.fieldPaths=activated_at&updateMask.fieldPaths=expires_at"
        url = f"{self.base_url}/keys/{key}?key={self.api_key}&{update_mask}"
        
        patch_data = {
            "fields": {
                "hwid": {"stringValue": hwid_to_save},
                "login": {"stringValue": login},
                "password": {"stringValue": password},
                "activated_at": {"stringValue": now.isoformat() + "Z"},
                "expires_at": {"stringValue": expires_str}
            }
        }
        requests.patch(url, json=patch_data, timeout=10)

    def check_grace_period(self, login, password, key):
        """Allows login if offline but within 24 hours of last successful login."""
        session = self.load_session()
        if not session or session.get("key") != key:
             return False, "Требуется подключение к интернету.", None
             
        last_login_str = session.get("last_login")
        if last_login_str:
            last_login = datetime.fromisoformat(last_login_str)
            if datetime.now() - last_login < timedelta(hours=24):
                return True, "Офлайн режим (24ч)", "Offline"
        
        return False, "Срок офлайн доступа истек.", None

    def logout(self):
        """Point 3: Clear session data and credentials."""
        self.current_creds = None
        # You might also want to clear any saved tokens on disk if applicable
        # For now, just clearing memory is a good start.
        logger.info("AuthManager: Session cleared.")

    def check_license_status(self):
        """Lightweight check using stored session credentials."""
        session = self.load_session()
        if not session:
            return False, "Сессия не найдена.", None
            
        login = session.get("login")
        password = session.get("password")
        key = session.get("key")
        
        if not all([login, password, key]):
            return False, "Неполные данные сессии.", None
            
        return self.validate_key(login, password, key)

    def save_session(self, login, password, key):
        """Saves successful login to auto-fill next time with atomic write and retries."""
        data = {
            "login": login,
            "password": password,
            "key": key,
            "last_login": datetime.now().isoformat()
        }
        
        temp_file = self.session_file + ".tmp"
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
                
                # Atomic write strategy
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                # Replace is atomic on Windows for existing files
                if os.path.exists(self.session_file):
                    os.replace(temp_file, self.session_file)
                else:
                    os.rename(temp_file, self.session_file)
                
                logger.info(f"Auth: Session saved successfully to {self.session_file}")
                return True
            except (IOError, PermissionError) as e:
                logger.warning(f"Auth: Save session attempt {attempt+1} failed: {e}")
                time.sleep(0.2) # Wait for file to be released
            except Exception as e:
                logger.error(f"Auth: Unexpected error saving session: {e}")
                break
        return False

    def load_session(self):
        """Loads last session data with robust error handling."""
        if not os.path.exists(self.session_file):
            return None
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (IOError, PermissionError) as e:
                logger.warning(f"Auth: Load session attempt {attempt+1} failed: {e}")
                time.sleep(0.1)
            except json.JSONDecodeError:
                logger.error("Auth: Session file is corrupted. Deleting.")
                try: os.remove(self.session_file)
                except: pass
                return None
            except Exception as e:
                logger.error(f"Auth: Error loading session: {e}")
                break
        return None
