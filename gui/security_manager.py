
import os
import time
import json
import logging
import bcrypt
import pyotp
import qrcode
import platform
import random
import string
import csv
from datetime import datetime, timedelta
from io import BytesIO

class SecurityManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.lockout_file = os.path.join(os.getenv("APPDATA"), "MoneyTracker", "security_lockout.json")
        self.log_file = os.path.join(os.getenv("APPDATA"), "MoneyTracker", "security_events.csv")
        self._ensure_log_header()
        
        # Load lockout state
        self.lockout_state = self._load_lockout_state()
        
    def _ensure_log_header(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'IP/Host', 'User-Agent', 'Event', 'Result', 'Details'])

    def log_event(self, event, result, details=""):
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    platform.node(), # Hostname as "IP" for desktop
                    f"MoneyTracker/V8 ({platform.system()})",
                    event,
                    result,
                    details
                ])
        except Exception as e:
            logging.error(f"Failed to log security event: {e}")

    def _load_lockout_state(self):
        try:
            if os.path.exists(self.lockout_file):
                with open(self.lockout_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {"admin": {"attempts": 0, "lockout_until": 0}, "extra": {"attempts": 0, "lockout_until": 0}}

    def _save_lockout_state(self):
        try:
            with open(self.lockout_file, 'w') as f:
                json.dump(self.lockout_state, f)
        except Exception as e:
            logging.error(f"Failed to save lockout state: {e}")

    def check_lockout(self, role):
        state = self.lockout_state.get(role, {"attempts": 0, "lockout_until": 0})
        if time.time() < state["lockout_until"]:
            return state["lockout_until"] - time.time()
        return 0

    def register_attempt(self, role, success):
        state = self.lockout_state.setdefault(role, {"attempts": 0, "lockout_until": 0})
        
        if success:
            state["attempts"] = 0
            state["lockout_until"] = 0
            self._save_lockout_state()
            self.log_event("Login Attempt", "Success", f"Role: {role}")
            logging.info(f"SecurityManager: Login success for {role}")
            return False, 0
            
        state["attempts"] += 1
        self.log_event("Login Attempt", "Failure", f"Role: {role}, Attempt: {state['attempts']}")
        logging.warning(f"SecurityManager: Login failed for {role}. Attempt {state['attempts']}")
        
        if state["attempts"] >= 3:
            # Exponential backoff: 30s, 1m, 2m...
            # Initial 30s
            factor = state["attempts"] - 2 # 1, 2, 3...
            # 30 * 2^(factor-1) -> 30, 60, 120...
            duration = 30 * (2 ** (factor - 1))
            state["lockout_until"] = time.time() + duration
            self._save_lockout_state()
            logging.warning(f"SecurityManager: Lockout triggered for {role} for {duration}s")
            return True, duration
            
        self._save_lockout_state()
        return False, 0

    def get_attempts(self, role):
        return self.lockout_state.get(role, {}).get("attempts", 0)

    # --- Secure Code Management ---

    def verify_code(self, key, input_code):
        stored = self.data_manager.get_secure_value(key, "")
        
        self.log_event("Auth Debug", "Start", f"Key: {key}, Input len: {len(input_code)}, Stored exists: {bool(stored)}")

        # Initial Setup (Default Codes)
        if not stored:
            # Check default codes for respective roles
            is_admin_default = (key == "admin_code" and input_code == "SanyaDargon")
            is_extra_default = (key == "extra_code" and input_code == "BossDargon")
            
            self.log_event("Auth Debug", "Default Check", f"Admin Default: {is_admin_default}, Extra Default: {is_extra_default}")

            if is_admin_default or is_extra_default:
                # Migrate to bcrypt immediately
                self.set_code(key, input_code)
                return True
            return False
            
        if stored.startswith("$2b$"):
            try:
                result = bcrypt.checkpw(input_code.encode(), stored.encode())
                self.log_event("Auth Debug", "Bcrypt Check", f"Result: {result}")
                return result
            except Exception as e:
                self.log_event("Auth Debug", "Bcrypt Error", f"Error: {e}")
                return False
        else:
            # Legacy fallback
            self.log_event("Auth Debug", "Legacy Check", f"Input matches stored: {stored == input_code}")
            if stored == input_code:
                self.set_code(key, input_code)
                return True
            return False

    def set_code(self, key, new_code):
        # Hash with cost 12
        hashed = bcrypt.hashpw(new_code.encode(), bcrypt.gensalt(rounds=12)).decode()
        self.data_manager.save_secure_value(key, hashed)
        self.log_event("Code Change", "Success", f"Key: {key}")

    def validate_complexity(self, code):
        if len(code) < 12: return False, "Минимум 12 символов"
        if not any(c.islower() for c in code): return False, "Нужна строчная буква"
        if not any(c.isupper() for c in code): return False, "Нужна заглавная буква"
        if not any(c.isdigit() for c in code): return False, "Нужна цифра"
        if not any(c in string.punctuation for c in code): return False, "Нужен спецсимвол"
        return True, ""

    # --- 2FA (TOTP) ---

    def setup_2fa(self, role):
        # Generate secret
        secret = pyotp.random_base32()
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=f"MoneyTracker Admin ({platform.node()})",
            issuer_name="MoneyTracker"
        )
        
        # Generate QR
        qr = qrcode.make(uri)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_bytes = buffer.getvalue()
        
        # Generate Backup Codes
        backup_codes = [''.join(random.choices(string.ascii_uppercase + string.digits, k=8)) for _ in range(8)]
        
        return secret, qr_bytes, backup_codes

    def confirm_2fa_setup(self, role, secret, code, backup_codes):
        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            # Save secret securely
            self.data_manager.save_secure_value(f"{role}_2fa_secret", secret)
            self.data_manager.save_secure_value(f"{role}_backup_codes", json.dumps(backup_codes))
            self.log_event("2FA Setup", "Success", f"Role: {role}")
            return True
        return False

    def verify_2fa(self, role, code):
        secret = self.data_manager.get_secure_value(f"{role}_2fa_secret", "")
        if not secret:
            return True # 2FA not enabled
            
        # Check TOTP
        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            return True
            
        # Check Backup Codes
        backups = json.loads(self.data_manager.get_secure_value(f"{role}_backup_codes", "[]"))
        if code in backups:
            backups.remove(code)
            self.data_manager.save_secure_value(f"{role}_backup_codes", json.dumps(backups))
            self.log_event("2FA Backup Used", "Success", f"Role: {role}")
            return True
            
        return False

    def is_2fa_enabled(self, role):
        return bool(self.data_manager.get_secure_value(f"{role}_2fa_secret", ""))

    def disable_2fa(self, role):
        self.data_manager.save_secure_value(f"{role}_2fa_secret", "")
        self.data_manager.save_secure_value(f"{role}_backup_codes", "")
        self.log_event("2FA Disabled", "Success", f"Role: {role}")

