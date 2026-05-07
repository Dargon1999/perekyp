import os
import json
import logging
from utils import resource_path

class KeyManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.logger = logging.getLogger(__name__)

    def ensure_preloaded_keys(self):
        try:
            secure_dir = resource_path(os.path.join("secure", "preloaded_keys.enc"))
            # Env fallback: MONEYTRACKER_PRELOADED_KEYS contains JSON string
            env_json = os.getenv("MONEYTRACKER_PRELOADED_KEYS")
            if os.path.exists(secure_dir):
                # File content is encrypted via DataManager.encrypt_value
                with open(secure_dir, "r", encoding="utf-8") as f:
                    enc = f.read().strip()
                dec = self.data_manager.decrypt_value(enc)
                pre = json.loads(dec)
                self._store_preloaded(pre)
                return True
            elif env_json:
                pre = json.loads(env_json)
                self._store_preloaded(pre)
                return True
        except Exception as e:
            self.logger.error(f"ensure_preloaded_keys error: {e}")
        return False

    def _store_preloaded(self, preloaded):
        # Expected format: {"openai": ["key1","key2"], "deepseek": ["keyA"], ...}
        for prov, keys in preloaded.items():
            if not isinstance(keys, list) or not keys:
                continue
            self.data_manager.save_secure_value(f"{prov}_keys", json.dumps(keys))
            self.data_manager.save_secure_value(f"{prov}_key_index", "0")

    def get_key(self, provider):
        provider = provider.lower()
        # Priority: env -> secure single -> secure list
        env_map = {"openai": "OPENAI_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}
        env_key = os.getenv(env_map.get(provider, ""))
        if env_key:
            return env_key
        single = self.data_manager.get_secure_value(f"{provider}_api_key", "")
        if single:
            return single
        keys_json = self.data_manager.get_secure_value(f"{provider}_keys", "")
        idx_str = self.data_manager.get_secure_value(f"{provider}_key_index", "0")
        if keys_json:
            try:
                keys = json.loads(keys_json)
                idx = int(idx_str) if idx_str.isdigit() else 0
                if not keys:
                    return ""
                return keys[idx % len(keys)]
            except Exception:
                return ""
        return ""

    def set_key(self, provider, key):
        provider = provider.lower()
        if not key:
            return
        self.data_manager.save_secure_value(f"{provider}_api_key", key)

    def set_keys(self, provider, keys):
        provider = provider.lower()
        if not keys:
            return
        self.data_manager.save_secure_value(f"{provider}_keys", json.dumps(keys))
        self.data_manager.save_secure_value(f"{provider}_key_index", "0")

    def rotate_key(self, provider):
        provider = provider.lower()
        keys_json = self.data_manager.get_secure_value(f"{provider}_keys", "")
        if not keys_json:
            return None
        try:
            keys = json.loads(keys_json)
            idx_str = self.data_manager.get_secure_value(f"{provider}_key_index", "0")
            idx = int(idx_str) if idx_str.isdigit() else 0
            idx = (idx + 1) % len(keys)
            self.data_manager.save_secure_value(f"{provider}_key_index", str(idx))
            return keys[idx]
        except Exception:
            return None
