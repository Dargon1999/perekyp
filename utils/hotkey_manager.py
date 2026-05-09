import os
import json
import logging
import threading
import time
import ctypes
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# WinAPI Constants
user32 = ctypes.windll.user32
WM_HOTKEY = 0x0312

class HotkeyManager(QObject):
    hotkey_triggered = pyqtSignal(str) # action_name

    def __init__(self, config_path="hotkeys_config.json"):
        super().__init__()
        self.config_path = config_path
        self.hotkeys = {}
        self._lock = threading.Lock()
        self._active_keys = set()
        self._last_trigger_time = {} # For debounce
        self.running = False
        self.thread = None
        self.load_config()
        self.start()

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.hotkeys = json.load(f)
            else:
                self.hotkeys = {
                    "F7": {"action": "mem_cleanup", "enabled": True, "vk": 0x76},
                    "F8": {"action": "temp_cleanup", "enabled": True, "vk": 0x77}
                }
        except Exception as e:
            logging.error(f"Failed to load hotkeys config: {e}")

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        logging.info("WinAPI Hotkey Listener started")

    def _listen(self):
        # Register hotkeys
        # VK Codes mapping
        vk_map = {
            "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
            "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
            "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
            "Home": 0x24, "End": 0x23, "Insert": 0x2D, "Delete": 0x2E
        }
        
        registered_ids = {}
        for i, (key, data) in enumerate(self.hotkeys.items(), start=1):
            if data.get("enabled"):
                vk = vk_map.get(key, data.get("vk"))
                if vk:
                    if user32.RegisterHotKey(None, i, 0, vk):
                        registered_ids[i] = data["action"]
                        logging.info(f"Registered hotkey {key} (ID: {i})")
                    else:
                        logging.error(f"Failed to register hotkey {key}: {ctypes.GetLastError()}")

        # Message loop
        import ctypes.wintypes
        msg = ctypes.wintypes.MSG()
        while self.running:
            if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY:
                    action = registered_ids.get(msg.wParam)
                    if action:
                        self._trigger(action)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.01)

        # Unregister
        for i in registered_ids:
            user32.UnregisterHotKey(None, i)

    def _trigger(self, action):
        current_time = time.time()
        with self._lock:
            last_time = self._last_trigger_time.get(action, 0)
            if current_time - last_time < 0.5: # 500ms debounce
                return
            self._last_trigger_time[action] = current_time
        
        logging.info(f"[Hotkey] Triggered: {action}")
        QTimer.singleShot(0, lambda: self.hotkey_triggered.emit(action))

    def stop(self):
        self.running = False
        logging.info("Hotkey Manager stopped")

    def update_hotkey(self, old_key, new_key, action):
        # For simplicity, restart the whole thing if config changes
        self.stop()
        if old_key in self.hotkeys:
            del self.hotkeys[old_key]
        self.hotkeys[new_key] = {"action": action, "enabled": True}
        self.start()
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.hotkeys, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save hotkeys config: {e}")

    def save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.hotkeys, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save hotkeys config: {e}")
