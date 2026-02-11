import sys
import platform
import subprocess
import uuid
import requests
import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, server_url=None):
        # Config from User
        self.api_key = "AIzaSyAps_XRnofsuusFDXD6cxDWTnk0bJ0kUaE"
        self.project_id = "generatormail-e478c"
        self.base_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"
        
        app_data = os.getenv("APPDATA") or os.path.expanduser("~")
        self.session_file = os.path.join(app_data, "MoneyTracker", "auth_session.json")
        self.hwid = self.get_hwid()
        self.current_creds = None
        
    def get_hwid(self):
        """Generates a unique HWID based on system info."""
        try:
            if platform.system() == "Windows":
                cmd = 'wmic csproduct get uuid'
                uuid_str = subprocess.check_output(cmd).decode().split('\n')[1].strip()
                return uuid_str
            else:
                return str(uuid.getnode())
        except Exception:
            # Fallback to mac address if wmic fails
            return str(uuid.getnode())

    def validate_key(self, login, password, key):
        """Validates key with Firebase."""
        logger.info(f"Validating key: {key[:5]}... for user: {login}")
        try:
            # 1. Fetch Key Document
            doc_url = f"{self.base_url}/keys/{key}?key={self.api_key}"
            logger.debug(f"Fetching: {doc_url}")
            response = requests.get(doc_url, timeout=10)
            
            if response.status_code == 404:
                logger.warning("Key not found (404)")
                return False, "Неверный ключ лицензии", None
            
            if response.status_code != 200:
                logger.warning(f"Server error {response.status_code}: {response.text}")
                return self.check_grace_period(login, password, key)
                
            data = response.json()
            fields = data.get("fields", {})
            
            # Helper to get field value safely
            def get_field(name, type_str="stringValue"):
                return fields.get(name, {}).get(type_str)

            # Check if active
            is_active = fields.get("is_active", {}).get("booleanValue", True) # Default true if missing
            if not is_active:
                 logger.warning("Key is disabled")
                 return False, "Этот ключ заблокирован", None

            # Check Activation
            stored_hwid = get_field("hwid")
            stored_login = get_field("login")
            stored_password = get_field("password")
            
            if stored_hwid:
                # Already activated
                if stored_hwid != self.hwid:
                    logger.warning(f"HWID mismatch: stored={stored_hwid}, current={self.hwid}")
                    return False, "Ключ уже активирован на другом ПК", None
                if stored_login and (stored_login != login or stored_password != password):
                    logger.warning("Login/Password mismatch")
                    return False, "Неверный логин или пароль для этого ключа", None
                
                # Check Expiration
                expires_at_str = get_field("expires_at")
                if expires_at_str and expires_at_str != "Lifetime":
                    try:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if datetime.now() > expires_at:
                             logger.warning("License expired")
                             return False, "Срок действия лицензии истек", None
                    except ValueError:
                        pass # Ignore parsing errors
                
                expires_display = expires_at_str if expires_at_str else "Lifetime"

            else:
                # First Activation
                logger.info("Activating new key...")
                duration_days = fields.get("duration_days", {}).get("integerValue")
                if not duration_days: 
                     # Try string value just in case
                     try:
                         duration_days = int(fields.get("duration_days", {}).get("stringValue", "7"))
                     except:
                         duration_days = 7

                now = datetime.now()
                expires_at = now + timedelta(days=int(duration_days))
                expires_at_str = expires_at.isoformat()
                
                # Update Document (Activate)
                update_mask = "updateMask.fieldPaths=hwid&updateMask.fieldPaths=login&updateMask.fieldPaths=password&updateMask.fieldPaths=activated_at&updateMask.fieldPaths=expires_at"
                patch_url = f"{self.base_url}/keys/{key}?key={self.api_key}&{update_mask}"
                
                patch_data = {
                    "fields": {
                        "hwid": {"stringValue": self.hwid},
                        "login": {"stringValue": login},
                        "password": {"stringValue": password},
                        "activated_at": {"stringValue": now.isoformat()},
                        "expires_at": {"stringValue": expires_at_str}
                    }
                }
                
                patch_resp = requests.patch(patch_url, json=patch_data, timeout=10)
                if patch_resp.status_code != 200:
                    logger.error(f"Activation failed: {patch_resp.text}")
                    return False, f"Ошибка активации: {patch_resp.text}", None
                    
                expires_display = expires_at_str

            # Success
            logger.info("Auth successful")
            self.save_session(login, password, key)
            self.current_creds = {
                "login": login, 
                "password": password, 
                "key": key,
                "expires_at": expires_display
            }
            return True, "Успешная авторизация", expires_display
                
        except requests.exceptions.ConnectionError:
             logger.warning("Connection error, checking grace period")
             return self.check_grace_period(login, password, key)
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False, f"Ошибка: {str(e)}", None

    def check_license_status(self):
        """Re-validates the current license."""
        if not self.current_creds:
            session = self.load_session()
            if session:
                self.current_creds = session
            else:
                return False, "No active session", None

        return self.validate_key(
            self.current_creds.get("login"),
            self.current_creds.get("password"),
            self.current_creds.get("key")
        )

    def check_grace_period(self, login, password, key):
        """Allows login if offline but within 24 hours of last successful login."""
        session = self.load_session()
        if not session:
             return False, "Нет связи с сервером (Firebase) и нет сохраненной сессии", None
             
        # Check if creds match saved session
        if session.get("key") != key or session.get("login") != login or session.get("password") != password:
            return False, "Нет связи с сервером (данные не совпадают с сохраненными)", None
            
        last_login_str = session.get("last_login")
        if last_login_str:
            try:
                last_login = datetime.fromisoformat(last_login_str)
                if (datetime.now() - last_login).total_seconds() < 24 * 3600:
                    return True, "Офлайн режим (Grace Period)", "Offline (24h)"
            except:
                pass
        
        return False, "Срок офлайн доступа (24ч) истек. Подключитесь к интернету.", None

    def save_session(self, login, password, key):
        """Saves successful login to auto-fill next time."""
        data = {
            "login": login,
            "password": password,
            "key": key,
            "last_login": datetime.now().isoformat()
        }
        try:
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            with open(self.session_file, 'w') as f:
                json.dump(data, f)
        except:
            pass

    def load_session(self):
        """Loads last session data."""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None
