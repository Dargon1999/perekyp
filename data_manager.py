import json
import os
import uuid
import shutil
import gzip
import base64
import binascii
import sys
import logging
import time
import hashlib
from datetime import datetime
from PyQt6.QtCore import Qt, QByteArray, QBuffer, QIODevice, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QPainter
from utils import Money


APP_NAME = "MoneyTracker"

def get_base_paths():
    """Determine data directory based on presence of local data.json (Portable Mode)."""
    # 1. Determine base executable path
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        # Development mode: Check script directory first, then CWD
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cwd = os.getcwd()
        
        # If data.json exists in the script directory (project root), use it.
        # This handles cases where the user runs the script from a different directory.
        if os.path.exists(os.path.join(script_dir, "data.json")):
            base_path = script_dir
        else:
            base_path = cwd
    
    local_data = os.path.join(base_path, "data.json")
    
    if os.path.exists(local_data):
        # Portable mode detected
        return base_path
    else:
        # Standard installation mode
        return os.path.join(os.getenv("APPDATA"), APP_NAME)

if __name__ == "__main__":
    # If run as a script (e.g. by PyInstaller), do not initialize anything that requires a GUI or environment variables.
    pass
else:
    # Standard initialization mode
    DATA_DIR = get_base_paths()
    DATA_FILE = os.path.join(DATA_DIR, "data.json")
    IMAGES_DIR = os.path.join(DATA_DIR, "images")

    # Ensure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

class DataManager(QObject):
    data_changed = pyqtSignal()

    def __init__(self, filename=None):
        super().__init__()
        # Use global DATA_FILE if filename not provided
        self.filename = filename if filename else DATA_FILE
        
        # Check if we need to migrate from local file to AppData
        self._check_and_migrate_local_data()
        
        self.data = self.load_data()
        self.ensure_active_profile()
        self.migrate_profiles()
        self.migrate_dates_to_russian_format()
        self.migrate_clothes_data()

    def migrate_clothes_data(self):
        """Ensure all sold clothes items have 'date_sold' field."""
        changed = False
        for profile in self.data["profiles"]:
            if "clothes" in profile and "sold_history" in profile["clothes"]:
                for item in profile["clothes"]["sold_history"]:
                    if "date_sold" not in item:
                        # Use date_added or current time as fallback
                        fallback_date = item.get("date_added", datetime.now().strftime("%d.%m.%Y %H:%M"))
                        item["date_sold"] = fallback_date
                        logging.warning(f"Migrated missing date_sold for item {item.get('name', 'Unknown')} (ID: {item.get('id')})")
                        changed = True
        
        if changed:
            logging.info("Completed clothes data migration: added missing date_sold fields")
            self.save_data()

    def migrate_dates_to_russian_format(self):
        """Convert all transaction dates from YYYY-MM-DD to DD.MM.YYYY."""
        changed = False
        for profile in self.data["profiles"]:
            for cat in ["car_rental", "mining", "farm_bp"]:
                if cat in profile and "transactions" in profile[cat]:
                    for t in profile[cat]["transactions"]:
                        if "date" in t and "-" in t["date"]:
                            try:
                                # Check if already in DD.MM.YYYY (simple check)
                                parts = t["date"].split("-")
                                if len(parts) == 3 and len(parts[0]) == 4: # YYYY-MM-DD
                                    dt = datetime.strptime(t["date"], "%Y-%m-%d")
                                    t["date"] = dt.strftime("%d.%m.%Y")
                                    changed = True
                            except ValueError:
                                pass
        
        if changed:
            print("Migrated dates to DD.MM.YYYY format")
            self.save_data()

    def _check_and_migrate_local_data(self):
        """Check if data.json exists in local dir and move it to AppData if AppData is empty."""
        local_file = "data.json"
        local_images_dir = "images"
        
        # If the target file doesn't exist but local file does, copy it
        if not os.path.exists(self.filename) and os.path.exists(local_file):
            try:
                shutil.copy2(local_file, self.filename)
                print(f"Migrated data from {local_file} to {self.filename}")
            except Exception as e:
                print(f"Error migrating data: {e}")

        # Migrate images if they exist locally but not in AppData
        if os.path.exists(local_images_dir):
            try:
                for item in os.listdir(local_images_dir):
                    s = os.path.join(local_images_dir, item)
                    d = os.path.join(IMAGES_DIR, item)
                    if os.path.isfile(s) and not os.path.exists(d):
                        shutil.copy2(s, d)
                print(f"Migrated images from {local_images_dir} to {IMAGES_DIR}")
            except Exception as e:
                print(f"Error migrating images: {e}")

    def save_pixmap_image(self, pixmap):
        """Saves a QPixmap as Base64 string (for portability). Replaces old file-based saving."""
        return self.save_image_to_base64(pixmap)

    def save_image(self, file_path):
        """Loads an image from file_path and saves it as Base64 string."""
        if not file_path or not os.path.exists(file_path):
            return None
        pixmap = QPixmap(file_path)
        return self.save_image_to_base64(pixmap)

    def get_placeholder_pixmap(self, w=200, h=200, text="No Image"):
        """Generates a placeholder pixmap."""
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.lightGray)
        painter = QPainter(pix)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawRect(0, 0, w-1, h-1)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return pix

    def load_pixmap(self, path, max_size=None):
        """
        Loads a QPixmap from a path (file path or Base64 data URI).
        Handles path resolution and errors.
        """
        if not path:
            return QPixmap()
        
        resolved = self.resolve_image_path(path)
        pix = QPixmap()
        
        # 1. Base64 Handling
        if resolved.startswith("data:image"):
            try:
                header, data = resolved.split(',', 1)
                b64_data = QByteArray.fromBase64(data.encode())
                pix.loadFromData(b64_data)
            except Exception as e:
                logging.error(f"Failed to load Base64 image: {e}")
                return self.get_placeholder_pixmap(text="Error")

        # 2. File Path Handling
        else:
            if os.path.isdir(resolved):
                logging.warning(f"Image path is a directory: {resolved}")
                return self.get_placeholder_pixmap(text="Is Dir")
                
            if os.path.exists(resolved):
                if os.path.getsize(resolved) == 0:
                    logging.warning(f"Image file is empty: {resolved}")
                    return self.get_placeholder_pixmap(text="Empty")
                    
                pix.load(resolved)
                if pix.isNull():
                    logging.warning(f"Failed to load image (unsupported format?): {resolved}")
                    return self.get_placeholder_pixmap(text="Bad Format")
            else:
                logging.warning(f"Image file not found: {resolved}")
                return self.get_placeholder_pixmap(text="Missing")
        
        if pix.isNull():
             return self.get_placeholder_pixmap(text="Error")

        if max_size:
            w, h = max_size
            pix = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        return pix

    def save_image_to_base64(self, pixmap):
        """Saves a QPixmap as a Base64 string."""
        if pixmap.isNull():
            return None

        # Optimize
        MAX_SIZE = 1280
        if pixmap.width() > MAX_SIZE or pixmap.height() > MAX_SIZE:
             pixmap = pixmap.scaled(MAX_SIZE, MAX_SIZE, 
                                    Qt.AspectRatioMode.KeepAspectRatio, 
                                    Qt.TransformationMode.SmoothTransformation)
        
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG", quality=80)
        base64_data = byte_array.toBase64().data().decode()
        return f"data:image/png;base64,{base64_data}"

    def resolve_image_path(self, path):
        """Resolves relative image path to absolute path in AppData or CWD."""
        if not path: return None
        
        # Check if it's base64
        if path.startswith("data:image"):
            return path
            
        # 1. Check if path exists as-is (Absolute or Relative to CWD)
        if os.path.exists(path):
            return os.path.abspath(path)
            
        # 1.5 Special check for localized user paths (like Pictures/Screenshots)
        # If absolute path and not found, it might be from a different system
        if os.path.isabs(path):
            if "Pictures" in path or "Screenshots" in path or "Desktop" in path:
                # Try to find it in current user's equivalent folder
                parts = path.replace('\\', '/').split('/')
                try:
                    # Look for Pictures/Screenshots etc in current user profile
                    user_profile = os.path.expanduser("~")
                    if "Pictures" in parts:
                        idx = parts.index("Pictures")
                        rel_part = os.path.join(*parts[idx:])
                        candidate = os.path.join(user_profile, rel_part)
                        if os.path.exists(candidate):
                            return candidate
                except Exception:
                    pass

        # 2. If absolute but missing, try to rescue it by taking basename
        if os.path.isabs(path):
            basename = os.path.basename(path)
            # If absolute path contains AppData, try to look there first if moved
            if "AppData" in path:
                 # path might be from another user's AppData, extract relative part if possible
                 pass
        else:
            basename = path
            
        # 3. Search in standard locations
        candidates = [
            os.path.join(DATA_DIR, basename),
            os.path.join(IMAGES_DIR, basename),
            os.path.join(IMAGES_DIR, "helper", basename),
            os.path.join(os.getcwd(), basename),
            os.path.join(DATA_DIR, "images", basename),
            os.path.join(os.path.expanduser("~"), "images", basename),
            os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd(), basename)
        ]
        
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
            
        logging.warning(f"Image not found: {path}. Checked: {len(candidates)} locations")
        return os.path.join(DATA_DIR, path)

    def load_data(self):
        if not os.path.exists(self.filename):
            return {"profiles": [], "active_profile_id": None}
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Check for legacy format
            if isinstance(data, list):
                return self._migrate_legacy_data(data)
            elif isinstance(data, dict) and "profiles" not in data:
                return self._migrate_legacy_data(data)
                
            return data
        except (json.JSONDecodeError, IOError):
            return {"profiles": [], "active_profile_id": None}

    def _migrate_legacy_data(self, old_data):
        """Migrate old data format to new profile-based format."""
        profile_id = str(uuid.uuid4())
        
        # Extract transactions/data
        transactions = []
        starting_amount = 0.0
        
        if isinstance(old_data, list):
            transactions = old_data
        elif isinstance(old_data, dict):
            transactions = old_data.get("transactions", [])
            starting_amount = old_data.get("starting_amount", 0.0)
            
        new_profile = {
            "id": profile_id,
            "name": "Migrated Profile",
            "created_at": datetime.now().strftime("%d.%m.%Y"),
            "starting_amount": float(starting_amount),
            "settings": {
                "theme": "dark",
                "listing_cost": 0.0,
                "version": "6.1.8"
            },
            "car_rental": {
                "starting_amount": 0.0,
                "transactions": []
            },
            "mining": {
                "starting_amount": 0.0,
                "transactions": []
            },
            "farm_bp": {
                "starting_amount": 0.0,
                "transactions": []
            },
            "clothes": {
                "starting_amount": 0.0,
                "inventory": [],
                "sold_history": []
            },
            "transactions": transactions
        }
        
        # If old data had specific categories, copy them
        if isinstance(old_data, dict):
            if "car_rental" in old_data:
                if isinstance(old_data["car_rental"], list):
                    new_profile["car_rental"]["transactions"] = old_data["car_rental"]
                else:
                    new_profile["car_rental"] = old_data["car_rental"]
            
            if "mining" in old_data:
                if isinstance(old_data["mining"], list):
                    new_profile["mining"]["transactions"] = old_data["mining"]
                else:
                    new_profile["mining"] = old_data["mining"]

            if "clothes" in old_data:
                if isinstance(old_data["clothes"], list):
                    new_profile["clothes"]["inventory"] = old_data["clothes"]
                else:
                    new_profile["clothes"] = old_data["clothes"]
        
        migrated_data = {
            "profiles": [new_profile],
            "active_profile_id": profile_id
        }
        
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(migrated_data, f, indent=4, ensure_ascii=False)
        except IOError:
            pass
            
        return migrated_data

    def save_data(self):
        # Create backup before saving
        self.perform_scheduled_backup()
        
        # Add metadata
        self.data["_metadata"] = {
            "version": "9.0.1",
            "schema_version": 2,
            "last_modified": datetime.now().isoformat(),
            "app_version": APP_NAME
        }
        
        # Use atomic write to prevent data corruption
        temp_file = self.filename + ".tmp"
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Write to temp file first
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
                
                # Atomic replace (renames are atomic on POSIX and modern Windows)
                if os.path.exists(self.filename):
                    os.replace(temp_file, self.filename)
                else:
                    os.rename(temp_file, self.filename)
                
                # Emit signal after successful save
                self.data_changed.emit()
                return
            except IOError as e:
                msg = f"Error saving data to {self.filename} (Attempt {attempt+1}/{max_retries}): {e}"
                logging.error(msg)
                time.sleep(0.1)
            except Exception as e:
                logging.error(f"Unexpected error saving data: {e}")
                
        logging.critical(f"Failed to save data after {max_retries} attempts.")

    # --- Backup Management ---

    def perform_scheduled_backup(self):
        """Checks if a backup is needed based on schedule and performs it."""
        channel = self.get_global_data("backup_channel", "")
        frequency = self.get_global_data("backup_frequency", "never")
        last_backup_str = self.get_global_data("last_backup_timestamp", "")
        
        if not channel or not os.path.exists(channel) or frequency == "never":
            # Just perform local backup (standard)
            self.create_backup()
            return

        # Calculate if we need to run backup
        should_backup = False
        now = datetime.now()
        
        if not last_backup_str:
            should_backup = True
        else:
            try:
                last_backup = datetime.strptime(last_backup_str, "%Y-%m-%d %H:%M:%S")
                delta = now - last_backup
                
                if frequency == "1d" and delta.days >= 1:
                    should_backup = True
                elif frequency == "1w" and delta.days >= 7:
                    should_backup = True
                elif frequency == "2w" and delta.days >= 14:
                    should_backup = True
                elif frequency == "1m" and delta.days >= 30:
                    should_backup = True
            except ValueError:
                should_backup = True # Invalid date format, force backup

        if should_backup:
            self.create_backup(extra_channel=channel)
            self.set_global_data("last_backup_timestamp", now.strftime("%Y-%m-%d %H:%M:%S"))

    def create_backup(self, extra_channel=None):
        if not os.path.exists(self.filename):
            return
        
        # 1. Standard Local Backup
        backup_dir = os.path.join(os.path.dirname(self.filename), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"data_backup_{timestamp}.json"
        local_backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            shutil.copy2(self.filename, local_backup_path)
            
            # Keep only last 10 backups locally
            backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("data_backup_")])
            if len(backups) > 10:
                for b in backups[:-10]:
                    try:
                        os.remove(b)
                    except:
                        pass
        except Exception as e:
            print(f"Local backup failed: {e}")
            logging.error(f"Local backup failed: {e}")

        # 2. Extra Channel Backup (Dual Storage)
        if extra_channel and os.path.exists(extra_channel) and os.path.isdir(extra_channel):
            try:
                extra_backup_path = os.path.join(extra_channel, backup_filename)
                shutil.copy2(self.filename, extra_backup_path)
                
                # Cleanup in extra channel (optional, maybe keep more?)
                # Let's keep last 10 there too to avoid clutter
                extra_backups = sorted([os.path.join(extra_channel, f) for f in os.listdir(extra_channel) if f.startswith("data_backup_")])
                if len(extra_backups) > 10:
                    for b in extra_backups[:-10]:
                        try:
                            os.remove(b)
                        except:
                            pass
                print(f"Backup saved to extra channel: {extra_backup_path}")
            except Exception as e:
                print(f"Extra channel backup failed: {e}")
                logging.error(f"Extra channel backup failed: {e}")

    def restore_from_backup(self, backup_path):
        try:
             shutil.copy2(backup_path, self.filename)
             self.data = self.load_data()
             return True
        except Exception as e:
             print(f"Restore failed: {e}")
             return False

    def ensure_active_profile(self):
        """Ensure there is at least one profile and one is active."""
        if not self.data["profiles"]:
            self.create_profile("Default Profile", 0)
        
        if not self.data.get("active_profile_id"):
             self.data["active_profile_id"] = self.data["profiles"][0]["id"]
             self.save_data()
        
        # Verify active profile exists
        active_id = self.data["active_profile_id"]
        if not any(p["id"] == active_id for p in self.data["profiles"]):
            self.data["active_profile_id"] = self.data["profiles"][0]["id"]
            self.save_data()

    def migrate_profiles(self):
        """Ensure all profiles have the new structure."""
        changed = False
        for profile in self.data["profiles"]:
            # Initialize settings
            if "settings" not in profile:
                profile["settings"] = {
                    "theme": "dark",
                    "listing_cost": 0.0,
                    "version": "5.0.0"
                }
                changed = True
            
            # Initialize categories
            for cat in ["car_rental", "mining", "farm_bp", "fishing"]:
                if cat not in profile:
                    profile[cat] = {
                        "transactions": []
                    }
                    changed = True
                elif isinstance(profile[cat], list):
                    profile[cat] = {
                        "transactions": profile[cat]
                    }
                    changed = True
                # Remove starting_amount from category if it exists
                if isinstance(profile[cat], dict) and "starting_amount" in profile[cat]:
                    del profile[cat]["starting_amount"]
                    changed = True
            
            if "clothes" not in profile:
                profile["clothes"] = {
                    "inventory": [], 
                    "sold_history": [] 
                }
                changed = True
            elif isinstance(profile["clothes"], list):
                profile["clothes"] = {
                    "inventory": profile["clothes"], 
                    "sold_history": [] 
                }
                changed = True
            # Remove starting_amount from clothes
            if isinstance(profile["clothes"], dict) and "starting_amount" in profile["clothes"]:
                del profile["clothes"]["starting_amount"]
                changed = True

            # Initialize new trade categories
            for cat in ["clothes_new", "cars_trade"]:
                if cat not in profile:
                    profile[cat] = {
                        "inventory": [],
                        "sold_history": []
                    }
                    changed = True
                # Remove starting_amount from trade categories
                if isinstance(profile[cat], dict) and "starting_amount" in profile[cat]:
                    del profile[cat]["starting_amount"]
                    changed = True
            
            # Ensure all clothes items have IDs
            if "clothes" in profile and isinstance(profile["clothes"], dict):
                for list_name in ["inventory", "sold_history"]:
                    if list_name in profile["clothes"]:
                        for item in profile["clothes"][list_name]:
                            if "id" not in item:
                                item["id"] = str(uuid.uuid4())
                                changed = True
            
            if "memo" not in profile:
                profile["memo"] = {
                    "uk": [],
                    "ak": []
                }
                changed = True

            if "capital_planning" not in profile:
                profile["capital_planning"] = {
                    "target_amount": 0.0,
                    "target_date": None,
                    "history": [],
                    "settings": {"simplified_mode": False}
                }
                changed = True

            if "achievements" not in profile:
                profile["achievements"] = []
                changed = True
            
        if changed:
            self.save_data()

    # --- Global Data Management ---

    def get_global_data(self, key, default=None):
        if "global" not in self.data:
            return default
        return self.data["global"].get(key, default)

    def set_global_data(self, key, value):
        if "global" not in self.data:
            self.data["global"] = {}
        self.data["global"][key] = value
        self.save_data()

    # --- Secure Storage (Simple Encryption) ---

    def _get_encryption_key(self):
        # Generate a consistent key based on a fixed salt
        salt = "MoneyTracker_Secure_Salt_2025_v8"
        return hashlib.sha256(salt.encode()).digest()

    def encrypt_value(self, value):
        if not value: return ""
        try:
            # Simple XOR encryption with the hash key
            key = self._get_encryption_key()
            value_bytes = value.encode('utf-8')
            encrypted = bytearray()
            for i in range(len(value_bytes)):
                encrypted.append(value_bytes[i] ^ key[i % len(key)])
            # Encode to Base64 for storage
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logging.error(f"Encryption error: {e}")
            return ""

    def decrypt_value(self, value):
        if not value: return ""
        try:
            # Decode from Base64
            encrypted_bytes = base64.b64decode(value)
            key = self._get_encryption_key()
            decrypted = bytearray()
            for i in range(len(encrypted_bytes)):
                decrypted.append(encrypted_bytes[i] ^ key[i % len(key)])
            return decrypted.decode('utf-8')
        except Exception as e:
            logging.error(f"Decryption error: {e}")
            return ""

    def save_secure_value(self, key, value):
        """Encrypts and saves a value to global settings."""
        encrypted = self.encrypt_value(value)
        self.set_global_data(key, encrypted)
        
    def get_secure_value(self, key, default=""):
        """Retrieves and decrypts a value from global settings."""
        encrypted = self.get_global_data(key, "")
        if not encrypted: return default
        return self.decrypt_value(encrypted)

    # --- Setting Helpers ---

    def get_setting(self, key, default=None):
        profile = self.get_active_profile()
        if profile and "settings" in profile:
            return profile["settings"].get(key, default)
        return default

    def set_setting(self, key, value):
        profile = self.get_active_profile()
        if profile:
            if "settings" not in profile:
                profile["settings"] = {}
            profile["settings"][key] = value
            self.save_data()

    # --- Profile Helpers ---

    def get_active_profile(self):
        active_id = self.data.get("active_profile_id")
        if not active_id: return None
        return next((p for p in self.data["profiles"] if p["id"] == active_id), None)

    def get_all_profiles(self):
        return self.data.get("profiles", [])

    def create_profile(self, name, starting_amount):
        profile_id = str(uuid.uuid4())
        new_profile = {
            "id": profile_id,
            "name": name,
            "created_at": datetime.now().strftime("%d.%m.%Y"),
            "starting_amount": float(starting_amount),
            "settings": {
                "theme": "dark",
                "listing_cost": 0.0,
                "version": "9.2.0"
            },
            "car_rental": {"transactions": []},
            "mining": {"transactions": []},
            "farm_bp": {"transactions": []},
            "fishing": {"transactions": []},
            "clothes": {"inventory": [], "sold_history": []},
            "clothes_new": {"inventory": [], "sold_history": []},
            "cars_trade": {"inventory": [], "sold_history": []},
            "capital_planning": {
                "target_amount": 0.0,
                "target_date": None,
                "history": [],
                "settings": {"simplified_mode": False}
            },
            "achievements": [],
            "transactions": []
        }
        self.data["profiles"].append(new_profile)
        self.data["active_profile_id"] = profile_id 
        self.save_data()
        return new_profile

    def delete_profile(self, profile_id):
        self.data["profiles"] = [p for p in self.data["profiles"] if p["id"] != profile_id]
        if self.data["active_profile_id"] == profile_id:
            self.data["active_profile_id"] = None
        self.ensure_active_profile() 
        self.save_data()

    def update_profile(self, profile_id, name, starting_amount):
        for profile in self.data["profiles"]:
            if profile["id"] == profile_id:
                profile["name"] = name
                profile["starting_amount"] = float(starting_amount)
                self.save_data()
                return True
        return False

    def set_active_profile(self, profile_id):
        if any(p["id"] == profile_id for p in self.data["profiles"]):
            self.data["active_profile_id"] = profile_id
            self.save_data()
            return True
        return False

    def get_memo_sections(self):
        profile = self.get_active_profile()
        if not profile: return []
        if "memo_sections" not in profile:
            profile["memo_sections"] = []
            self.save_data()
        return profile["memo_sections"]

    def get_memo_items(self, section_id):
        profile = self.get_active_profile()
        if not profile: return []
        
        for section in profile.get("memo_sections", []):
            if section["id"] == section_id:
                if "items" not in section:
                    section["items"] = []
                    self.save_data()
                return section["items"]
        return []

    def add_memo_section(self, title, headers):
        profile = self.get_active_profile()
        if not profile: return False
        
        if "memo_sections" not in profile:
            profile["memo_sections"] = []
            
        new_section = {
            "id": str(uuid.uuid4()),
            "title": title,
            "headers": headers,
            "items": []
        }
        profile["memo_sections"].append(new_section)
        self.save_data()
        return True

    def delete_memo_section(self, section_id):
        profile = self.get_active_profile()
        if not profile or "memo_sections" not in profile: return False
        
        original_len = len(profile["memo_sections"])
        profile["memo_sections"] = [s for s in profile["memo_sections"] if s["id"] != section_id]
        
        if len(profile["memo_sections"]) < original_len:
            self.save_data()
            return True
        return False

    def add_memo_item(self, section_id, values, image_path=None):
        logging.info(f"Adding memo item to section {section_id}: values={values}, image={image_path}")
        profile = self.get_active_profile()
        if not profile:
            logging.error("No active profile found")
            return False
        
        for section in profile.get("memo_sections", []):
            if section["id"] == section_id:
                item_data = {
                    "id": str(uuid.uuid4()),
                    "values": values,
                    "image_path": image_path
                }
                section["items"].append(item_data)
                self.save_data()
                logging.info(f"Memo item added successfully, id={item_data['id']}")
                return True
        logging.error(f"Section {section_id} not found")
        return False

    def update_memo_item(self, section_id, item_id, values, image_path=None):
        logging.info(f"Updating memo item {item_id} in section {section_id}: values={values}, image={image_path}")
        profile = self.get_active_profile()
        if not profile:
            logging.error("No active profile found")
            return False
        
        for section in profile.get("memo_sections", []):
            if section["id"] == section_id:
                for item in section["items"]:
                    if item["id"] == item_id:
                        item["values"] = values
                        item["image_path"] = image_path
                        self.save_data()
                        logging.info("Memo item updated successfully")
                        return True
        logging.error(f"Item {item_id} not found in section {section_id}")
        return False

    def delete_memo_item(self, section_id, item_id):
        profile = self.get_active_profile()
        if not profile: return False
        
        for section in profile.get("memo_sections", []):
            if section["id"] == section_id:
                original_len = len(section["items"])
                section["items"] = [i for i in section["items"] if i["id"] != item_id]
                if len(section["items"]) < original_len:
                    self.save_data()
                    return True
        return False

    def update_memo_section_title(self, section_id, new_title):
        profile = self.get_active_profile()
        if not profile: return False
        
        for section in profile.get("memo_sections", []):
            if section["id"] == section_id:
                section["title"] = new_title
                self.save_data()
                return True
        return False

    # --- Timers Methods ---

    def get_timers(self):
        profile = self.get_active_profile()
        if not profile: return []
        if "timers" not in profile:
            profile["timers"] = []
            self.save_data()
        return profile["timers"]

    def add_timer(self, name, t_type, duration):
        profile = self.get_active_profile()
        if not profile: return False
        
        if "timers" not in profile:
            profile["timers"] = []
            
        now = datetime.now().timestamp()
        
        new_timer = {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": t_type,
            "duration": duration,
            "start_time": now,
            "end_time": now + duration,
            "is_running": True,
            "paused_remaining": 0
        }
        profile["timers"].append(new_timer)
        self.save_data()
        return True

    def delete_timer(self, timer_id):
        profile = self.get_active_profile()
        if not profile or "timers" not in profile: return False
        
        original_len = len(profile["timers"])
        profile["timers"] = [t for t in profile["timers"] if t["id"] != timer_id]
        
        if len(profile["timers"]) < original_len:
            self.save_data()
            return True
        return False

    def update_timer_status(self, timer_id, action):
        profile = self.get_active_profile()
        if not profile: return False
        
        for timer in profile.get("timers", []):
            if timer["id"] == timer_id:
                now = datetime.now().timestamp()
                
                if action == "pause":
                    if timer["is_running"]:
                        remaining = timer["end_time"] - now
                        timer["paused_remaining"] = max(0, remaining)
                        timer["is_running"] = False
                        self.save_data()
                        return True
                        
                elif action == "resume":
                    if not timer["is_running"]:
                        timer["end_time"] = now + timer["paused_remaining"]
                        timer["is_running"] = True
                        self.save_data()
                        return True
        return False

    # --- Trade Methods (Generic) ---

    def get_trade_inventory(self, category):
        profile = self.get_active_profile()
        if not profile: return []
        return profile.get(category, {}).get("inventory", [])

    def get_trade_sold(self, category):
        profile = self.get_active_profile()
        if not profile: return []
        return profile.get(category, {}).get("sold_history", [])

    # --- Legacy Clothes Wrappers ---

    def get_clothes_inventory(self):
        return self.get_trade_inventory("clothes")

    def get_clothes_sold(self):
        return self.get_trade_sold("clothes")

    # --- Feature Specific Data ---

    def get_capital_planning_data(self):
        profile = self.get_active_profile()
        if not profile: return None
        if "capital_planning" not in profile:
            profile["capital_planning"] = {
                "target_amount": 0.0,
                "target_date": None,
                "history": [],
                "settings": {"simplified_mode": False}
            }
            self.save_data()
        return profile["capital_planning"]

    def update_capital_planning_data(self, data):
        profile = self.get_active_profile()
        if not profile: return
        profile["capital_planning"] = data
        self.save_data()

    def get_fishing_equipment(self):
        profile = self.get_active_profile()
        if not profile: return {}
        if "fishing" not in profile: return {}
        return profile["fishing"].get("equipment", {})

    def update_fishing_equipment(self, equipment_data):
        profile = self.get_active_profile()
        if not profile: return
        if "fishing" not in profile:
            profile["fishing"] = {}
        profile["fishing"]["equipment"] = equipment_data
        self.save_data()

    def get_achievements(self):
        """Returns a list of unlocked achievement IDs for the active profile."""
        profile = self.get_active_profile()
        if not profile: return []
        return profile.get("achievements", [])

    def unlock_achievement(self, achievement_id):
        profile = self.get_active_profile()
        if not profile: return False
        if "achievements" not in profile:
            profile["achievements"] = []
        
        if achievement_id not in profile["achievements"]:
            profile["achievements"].append(achievement_id)
            self.save_data()
            return True
        return False

    def get_unique_item_names(self, category):
        """Returns a list of unique item names used in a specific category."""
        transactions = self.get_transactions(category)
        names = set()
        for t in transactions:
            name = t.get("item_name")
            if name:
                # Remove icons if any (like 📷)
                clean_name = name.replace("📷", "").strip()
                if clean_name:
                    names.add(clean_name)
        return sorted(list(names))

    def add_transaction(self, category, amount, comment, date_str=None, item_name="", image_path=None, ad_cost=0.0):
        profile = self.get_active_profile()
        if not profile:
            return None
        
        if not date_str:
            date_str = datetime.now().strftime("%d.%m.%Y")

        transaction = {
            "id": str(uuid.uuid4()),
            "date": date_str,
            "amount": float(amount),
            "comment": comment,
            "item_name": item_name,
            "image_path": image_path,
            "ad_cost": float(ad_cost) if ad_cost else 0.0
        }

        if category in ["car_rental", "mining", "farm_bp", "fishing"]:
            if category not in profile:
                profile[category] = {"transactions": [], "starting_amount": 0.0}
            if "transactions" not in profile[category]:
                profile[category]["transactions"] = []
                
            profile[category]["transactions"].append(transaction)
            try:
                profile[category]["transactions"].sort(key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"), reverse=True)
            except ValueError:
                 profile[category]["transactions"].sort(key=lambda x: x["date"], reverse=True)
        else:
            if "transactions" not in profile: profile["transactions"] = []
            profile["transactions"].append(transaction)
            try:
                profile["transactions"].sort(key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"), reverse=True)
            except ValueError:
                profile["transactions"].sort(key=lambda x: x["date"], reverse=True)

        self.save_data()
        return transaction

    def delete_transaction(self, category, transaction_id):
        profile = self.get_active_profile()
        if not profile:
            return False
        
        target_list = None
        if category in ["car_rental", "mining", "farm_bp", "fishing"]:
            target_list = profile.get(category, {}).get("transactions", [])
        else:
            target_list = profile.get("transactions", [])

        original_len = len(target_list)
        new_list = [t for t in target_list if t["id"] != transaction_id]
        
        if len(new_list) < original_len:
            if category in ["car_rental", "mining", "farm_bp", "fishing"]:
                profile[category]["transactions"] = new_list
            else:
                profile["transactions"] = new_list
            self.save_data()
            return True
        return False

    def update_transaction(self, category, transaction_id, amount, comment, date_str, item_name, image_path=None, ad_cost=0.0):
        profile = self.get_active_profile()
        if not profile: return False
        
        target_list = None
        if category in ["car_rental", "mining", "farm_bp", "fishing"]:
            target_list = profile.get(category, {}).get("transactions", [])
        else:
            target_list = profile.get("transactions", [])
            
        for t in target_list:
            if t["id"] == transaction_id:
                t["amount"] = float(amount)
                t["comment"] = comment
                t["date"] = date_str
                t["item_name"] = item_name
                t["image_path"] = image_path
                t["ad_cost"] = float(ad_cost) if ad_cost else 0.0
                
                try:
                    target_list.sort(key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"), reverse=True)
                except ValueError:
                    target_list.sort(key=lambda x: x["date"], reverse=True)
                    
                self.save_data()
                return True
        return False

    def get_transactions(self, category):
        profile = self.get_active_profile()
        if not profile: return []
        if category in ["car_rental", "mining", "farm_bp", "fishing"]:
            return profile.get(category, {}).get("transactions", [])
        return profile.get("transactions", [])

    def update_category_starting_amount(self, category, amount):
        profile = self.get_active_profile()
        if not profile: return
        if category in ["car_rental", "mining", "clothes", "clothes_new", "cars_trade"]:
            profile[category]["starting_amount"] = float(amount)
            self.save_data()

    def get_category_starting_amount(self, category):
        profile = self.get_active_profile()
        if not profile: return 0.0
        if category in ["car_rental", "mining", "clothes", "clothes_new", "cars_trade"]:
            return profile[category].get("starting_amount", 0.0)
        return 0.0

    def get_category_stats(self, category):
        profile = self.get_active_profile()
        if not profile: return None

        if category in ["clothes", "clothes_new", "cars_trade", "fishing"]:
            if category not in profile:
                return {"income": 0, "expenses": 0, "current_balance": 0, "pure_profit": 0}
            
            if category == "fishing":
                # Fishing uses transactions list
                transactions = profile.get(category, {}).get("transactions", [])
                income = Money(0)
                expenses = Money(0)
                for t in transactions:
                    amt = Money.from_major(t["amount"])
                    if amt.amount > 0: income += amt
                    else: expenses += abs(amt)
            else:
                inventory = profile[category].get("inventory", [])
                sold = profile[category].get("sold_history", [])
                
                income = Money(0)
                for item in sold:
                    income += Money.from_major(item.get("sell_price", 0))
                
                expenses = Money(0)
                for item in inventory:
                    expenses += Money.from_major(item.get("buy_price", 0))
                for item in sold:
                    expenses += Money.from_major(item.get("buy_price", 0))
            
            pure_profit = income - expenses
            
            # Use cached or manual calculation to avoid recursion
            liquid_cash = Money.from_major(profile.get("starting_amount", 0.0))
            # ... we need a way to get liquid cash without calling get_total_capital_balance
            # Let's just return the pure profit and let the UI handle the global balance display
            
            return {
                "income": income.to_major(),
                "expenses": expenses.to_major(),
                "pure_profit": pure_profit.to_major()
            }
            
        elif category in ["car_rental", "mining", "farm_bp"]:
            transactions = profile.get(category, {}).get("transactions", [])
            
            income = Money(0)
            expenses = Money(0)
            for t in transactions:
                amt = Money.from_major(t["amount"])
                if amt.amount > 0: income += amt
                else: expenses += abs(amt)
                
                # Add ad cost
                ad_cost = Money.from_major(t.get("ad_cost", 0.0))
                expenses += ad_cost
            
            pure_profit = income - expenses
            
            return {
                "income": income.to_major(),
                "expenses": expenses.to_major(),
                "pure_profit": pure_profit.to_major()
            }
        return None

    def get_total_capital_balance(self):
        """Calculates total liquid cash and total net worth across all modules."""
        profile = self.get_active_profile()
        if not profile:
            return {"liquid_cash": 0.0, "net_worth": 0.0}

        # Base starting amount from profile
        liquid_cash = Money.from_major(profile.get("starting_amount", 0.0))
        net_worth = Money(liquid_cash.amount)

        # Categories with simple transactions (Income/Expenses)
        for cat in ["car_rental", "mining", "farm_bp", "fishing"]:
            stats = self.get_category_stats(cat)
            if stats:
                profit = Money.from_major(stats["pure_profit"])
                liquid_cash += profit
                net_worth += profit

        # Categories with Inventory (Purchase-Sale)
        for cat in ["clothes", "clothes_new", "cars_trade"]:
            stats = self.get_category_stats(cat)
            if stats:
                # liquid_cash = starting + income - (expenses_inventory + expenses_sold)
                # This is already handled in get_category_stats["current_balance"] relative to category starting amount.
                # However, we want to add the PROFIT from these categories to the GLOBAL liquid cash.
                profit = Money.from_major(stats["pure_profit"])
                liquid_cash += profit
                
                # Net worth includes the value of items currently in inventory
                inventory = profile.get(cat, {}).get("inventory", [])
                inventory_value = Money(0)
                for item in inventory:
                    inventory_value += Money.from_major(item.get("buy_price", 0))
                
                net_worth = liquid_cash + inventory_value

        return {
            "liquid_cash": liquid_cash.to_major(),
            "net_worth": net_worth.to_major()
        }

    def export_profile(self, profile_id):
        for profile in self.data["profiles"]:
            if profile["id"] == profile_id:
                json_str = json.dumps(profile, ensure_ascii=False)
                compressed = gzip.compress(json_str.encode('utf-8'))
                b64 = base64.b64encode(compressed).decode('utf-8')
                return b64
        return None

    def import_profile(self, data_str):
        try:
            profile = None
            try:
                decoded = base64.b64decode(data_str)
                decompressed = gzip.decompress(decoded)
                json_str = decompressed.decode('utf-8')
                profile = json.loads(json_str)
            except (binascii.Error, gzip.BadGzipFile, UnicodeDecodeError, ValueError):
                try:
                    profile = json.loads(data_str)
                except:
                    pass
            return profile
        except Exception as e:
            print(f"Error importing profile: {e}")
            return None

    def save_filter_history(self, category, start_date, end_date):
        """Save a custom filter period to history."""
        profile = self.get_active_profile()
        if not profile or category not in profile: return

        if "filter_history" not in profile[category]:
            profile[category]["filter_history"] = []

        history_item = {
            "start_date": start_date,
            "end_date": end_date,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        history = profile[category]["filter_history"]
        if history and history[0]["start_date"] == start_date and history[0]["end_date"] == end_date:
            return

        history.insert(0, history_item)
        profile[category]["filter_history"] = history[:10]
        self.save_data()

    def get_filter_history(self, category):
        profile = self.get_active_profile()
        if not profile or category not in profile: return []
        return profile[category].get("filter_history", [])

    def update_timer(self, timer_id, updates):
        profile = self.get_active_profile()
        if not profile: return False
        
        if "timers" in profile:
            for timer in profile["timers"]:
                if timer["id"] == timer_id:
                    timer.update(updates)
                    self.save_data()
                    return True
        return False

    def get_item_stats(self, category):
        profile = self.get_active_profile()
        if not profile: return {}
        
        stats = {}
        
        # 1. Calculate from transactions
        transactions = []
        if category in ["car_rental", "mining", "farm_bp", "fishing"] and category in profile:
             transactions = profile[category].get("transactions", [])
        elif category not in ["car_rental", "mining", "farm_bp", "fishing"]:
             transactions = profile.get("transactions", [])
        
        for t in transactions:
            name = t.get("item_name", "Неизвестно")
            if not name: name = "Неизвестно"
            
            if name not in stats:
                stats[name] = {"count": 0, "income": 0, "expenses": 0, "profit": 0}
            
            amount = t.get("amount", 0)
            
            # Only count Income transactions as "Deals"
            if amount > 0:
                stats[name]["count"] += 1
            
            if amount > 0:
                stats[name]["income"] += amount
            else:
                stats[name]["expenses"] += abs(amount)
                
            # Add ad cost to expenses and subtract from profit
            ad_cost = t.get("ad_cost", 0.0)
            if ad_cost > 0:
                stats[name]["expenses"] += ad_cost
                
            stats[name]["profit"] += amount
            stats[name]["profit"] -= ad_cost
            
        # 2. Apply offsets
        if "item_stats_offsets" in profile and category in profile["item_stats_offsets"]:
            offsets = profile["item_stats_offsets"][category]
            for name, data in offsets.items():
                if name not in stats:
                    stats[name] = {"count": 0, "income": 0, "expenses": 0, "profit": 0}
                stats[name]["count"] += data.get("count", 0) # Apply offset
                
        return stats

    def set_item_stat_offset(self, category, item_name, offset):
        profile = self.get_active_profile()
        if not profile: return
        
        if "item_stats_offsets" not in profile:
            profile["item_stats_offsets"] = {}
        if category not in profile["item_stats_offsets"]:
            profile["item_stats_offsets"][category] = {}
            
        if item_name not in profile["item_stats_offsets"][category]:
            profile["item_stats_offsets"][category][item_name] = {}
            
        profile["item_stats_offsets"][category][item_name]["count"] = offset
        self.save_data()

    def get_unique_item_names(self, category):
        profile = self.get_active_profile()
        if not profile: return []
        
        transactions = []
        if category in ["car_rental", "mining", "farm_bp"]:
            if category in profile:
                transactions = profile[category].get("transactions", [])
        else:
            transactions = profile.get("transactions", [])
            
        names = set()
        for t in transactions:
            name = t.get("item_name")
            if name:
                names.add(name)
        
        return sorted(list(names))

    def add_trade_item(self, category, name, buy_price, note, photo_path):
        profile = self.get_active_profile()
        if not profile: return False
        
        if category not in profile:
            profile[category] = {"inventory": [], "sold_history": [], "starting_amount": 0}
            
        item = {
            "id": str(uuid.uuid4()),
            "name": name,
            "buy_price": float(buy_price),
            "note": note,
            "photo_path": photo_path,
            "date_added": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "status": "in_stock"
        }
        
        if "inventory" not in profile[category]:
             profile[category]["inventory"] = []
             
        profile[category]["inventory"].append(item)
        self.save_data()
        return True

    def delete_trade_item(self, category, item_id, is_sold=False):
        try:
            profile = self.get_active_profile()
            if not profile or category not in profile: 
                logging.error(f"delete_trade_item: Profile or {category} section missing")
                return False
            
            target_list = "sold_history" if is_sold else "inventory"
            if target_list not in profile[category]: 
                logging.warning(f"delete_trade_item: Target list {target_list} missing")
                return False
            
            original_len = len(profile[category][target_list])
            profile[category][target_list] = [
                item for item in profile[category][target_list] 
                if item.get("id") != item_id
            ]
            
            if len(profile[category][target_list]) < original_len:
                self.save_data()
                logging.info(f"Deleted {category} item {item_id} from {target_list}")
                return True
            
            logging.warning(f"delete_trade_item: Item {item_id} not found in {target_list}")
            return False
        except Exception as e:
            logging.exception(f"Error deleting {category} item {item_id}: {e}")
            return False

    def sell_trade_item(self, category, item_id, sell_price):
        try:
            profile = self.get_active_profile()
            if not profile or category not in profile: 
                logging.error(f"sell_trade_item: Profile or {category} section missing")
                return False
            
            inventory = profile[category].get("inventory", [])
            item_to_sell = None
            
            # Find item
            for item in inventory:
                if item.get("id") == item_id:
                    item_to_sell = item
                    break
            
            if not item_to_sell:
                logging.warning(f"sell_trade_item: Item {item_id} not found in inventory")
                return False
                
            # Move to sold
            try:
                # Ensure sell_price is valid
                price_val = float(sell_price)
                if price_val < 0:
                     raise ValueError("Price cannot be negative")
            except ValueError as ve:
                logging.error(f"sell_trade_item: Invalid price {sell_price}: {ve}")
                return False

            item_to_sell["status"] = "sold"
            item_to_sell["sell_price"] = price_val
            item_to_sell["date_sold"] = datetime.now().strftime("%d.%m.%Y %H:%M")
            
            # Remove from inventory
            profile[category]["inventory"] = [i for i in inventory if i.get("id") != item_id]
            
            # Add to sold history
            if "sold_history" not in profile[category]:
                profile[category]["sold_history"] = []
                
            profile[category]["sold_history"].append(item_to_sell)
            
            # Sort sold history by date sold (newest first)
            try:
                 profile[category]["sold_history"].sort(key=lambda x: datetime.strptime(x.get("date_sold", "01.01.1970 00:00"), "%d.%m.%Y %H:%M"), reverse=True)
            except ValueError:
                 logging.warning("sell_trade_item: Error sorting sold history by date")
                 
            self.save_data()
            logging.info(f"Sold {category} item {item_id} for {price_val}")
            return True
        except Exception as e:
            logging.exception(f"Error selling {category} item {item_id}: {e}")
            return False

    # --- Wrappers for Legacy Code ---

    def add_clothes_item(self, name, buy_price, note, photo_path):
        return self.add_trade_item("clothes", name, buy_price, note, photo_path)

    def delete_clothes_item(self, item_id, is_sold=False):
        return self.delete_trade_item("clothes", item_id, is_sold)

    def sell_clothes_item(self, item_id, sell_price):
        return self.sell_trade_item("clothes", item_id, sell_price)

    def import_profile_data(self, import_data):
        """
        Import profiles from external data.
        Merges data without overwriting existing records with same ID.
        Returns count of added records (profiles + items).
        """
        count = 0
        if "profiles" not in import_data:
            return 0
            
        current_profile_ids = {p["id"]: p for p in self.data["profiles"]}
        
        for p_in in import_data["profiles"]:
            p_id = p_in.get("id")
            if not p_id: continue
            
            if p_id not in current_profile_ids:
                # New profile, add it completely
                self.data["profiles"].append(p_in)
                count += 1 
                continue
                
            # Profile exists, merge data
            p_curr = current_profile_ids[p_id]
            
            # Merge Cars
            if "car_rental" in p_in:
                if "car_rental" not in p_curr: p_curr["car_rental"] = {}
                count += self._merge_lists(p_curr["car_rental"], p_in["car_rental"], "cars")
                count += self._merge_lists(p_curr["car_rental"], p_in["car_rental"], "transactions")

            # Merge Mining
            if "mining" in p_in:
                if "mining" not in p_curr: p_curr["mining"] = {}
                count += self._merge_lists(p_curr["mining"], p_in["mining"], "equipment")
                count += self._merge_lists(p_curr["mining"], p_in["mining"], "transactions")
                
            # Merge Farm BP
            if "farm_bp" in p_in:
                if "farm_bp" not in p_curr: p_curr["farm_bp"] = {}
                count += self._merge_lists(p_curr["farm_bp"], p_in["farm_bp"], "transactions")
                
            # Merge Clothes
            if "clothes" in p_in:
                if "clothes" not in p_curr: p_curr["clothes"] = {}
                count += self._merge_lists(p_curr["clothes"], p_in["clothes"], "inventory")
                count += self._merge_lists(p_curr["clothes"], p_in["clothes"], "sold_history")
            
            # Merge Memos (sections and items)
            if "memo_sections" in p_in:
                 if "memo_sections" not in p_curr: p_curr["memo_sections"] = []
                 # Merge memo sections
                 existing_section_ids = {s["id"]: s for s in p_curr["memo_sections"]}
                 for s_in in p_in["memo_sections"]:
                     if s_in["id"] not in existing_section_ids:
                         p_curr["memo_sections"].append(s_in)
                         count += 1
                     else:
                         # Merge items in existing section
                         s_curr = existing_section_ids[s_in["id"]]
                         count += self._merge_lists(s_curr, s_in, "items")

            # Merge Timers
            if "timers" in p_in:
                if "timers" not in p_curr: p_curr["timers"] = []
                # Timers list is direct
                count += self._merge_direct_list(p_curr["timers"], p_in["timers"])

        self.save_data()
        return count

    def _merge_lists(self, target_dict, source_dict, key):
        if key not in source_dict: return 0
        if key not in target_dict: target_dict[key] = []
        return self._merge_direct_list(target_dict[key], source_dict[key])

    def _merge_direct_list(self, target_list, source_list):
        added = 0
        existing_ids = {item.get("id") for item in target_list if isinstance(item, dict) and "id" in item}
        
        for item in source_list:
            if not isinstance(item, dict): continue
            item_id = item.get("id")
            if item_id and item_id not in existing_ids:
                target_list.append(item)
                existing_ids.add(item_id)
                added += 1
        return added
