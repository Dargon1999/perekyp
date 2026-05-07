import unittest
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

# Ensure app is initialized for UI tests
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from utils.notifications import NotificationManager
from utils.hotkey_manager import HotkeyManager
from data_manager import DataManager

class TestSystemsComplex(unittest.TestCase):
    def setUp(self):
        self.dm = DataManager("test_data.json")
        self.nm = NotificationManager()
        self.hm = HotkeyManager("test_hotkeys.json")

    def tearDown(self):
        if os.path.exists("test_data.json"): os.remove("test_data.json")
        if os.path.exists("test_hotkeys.json"): os.remove("test_hotkeys.json")

    # 1. Notification System Tests
    def test_notification_queue(self):
        self.nm.notify("Test", "Message", level="success", sound=False, external=False)
        self.assertEqual(len(self.nm.queue), 1)
        # Wait for processing
        QTest.qWait(1000)
        self.assertEqual(len(self.nm.queue), 0)

    # 2. Hotkey System Tests
    def test_hotkey_registration(self):
        self.hm.update_hotkey("F9", "F10", "test_action")
        self.assertIn("F10", self.hm.hotkeys)
        self.assertEqual(self.hm.hotkeys["F10"]["action"], "test_action")

    # 3. Settings/Data Management Tests
    def test_settings_persistence(self):
        self.dm.set_setting("test_key", "test_value")
        # Reload
        new_dm = DataManager("test_data.json")
        self.assertEqual(new_dm.get_setting("test_key"), "test_value")

if __name__ == "__main__":
    unittest.main()
