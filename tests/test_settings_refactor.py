
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication, QCheckBox
from gui.tabs.settings_tab import SettingsTab

# Mock DataManager
class MockDataManager:
    def __init__(self):
        self.settings = {
            "listing_cost": 100.0,
            "listing_cost_enabled": True,
            "tab_visible_car_rental": True
        }
        
    def get_setting(self, key, default=None):
        return self.settings.get(key, default)
        
    def set_setting(self, key, value):
        print(f"DEBUG: MockDataManager.set_setting called with {key}={value}")
        self.settings[key] = value

# Mock MainWindow
class MockMainWindow:
    def __init__(self):
        self.update_tab_visibility_called = False
        
    def update_tab_visibility(self):
        self.update_tab_visibility_called = True

class TestSettingsRefactor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
            
    def setUp(self):
        self.data_manager = MockDataManager()
        self.auth_manager = MagicMock()
        self.main_window = MockMainWindow()
        self.settings_tab = SettingsTab(self.data_manager, self.auth_manager, self.main_window)
        
    def test_listing_cost_toggle(self):
        # Navigate to General Page (Index 0)
        self.settings_tab.nav_group.button(0).click()
        
        # Find the toggle
        toggle = self.settings_tab.auto_price_toggle
        self.assertTrue(toggle.isChecked())
        
        # Toggle it off
        toggle.setChecked(False)
        
        # Check DataManager
        self.assertFalse(self.data_manager.settings["listing_cost_enabled"])
        
    def test_tab_visibility_toggle(self):
        # Navigate to Tabs Page (Index 2)
        self.settings_tab.nav_group.button(2).click()
        
        # Check if toggle exists
        self.assertIn("car_rental", self.settings_tab.tab_toggles)
        cb = self.settings_tab.tab_toggles["car_rental"]
        self.assertTrue(cb.isChecked())
        
        # Toggle it off
        cb.setChecked(False)
        
        # Check DataManager
        self.assertFalse(self.data_manager.settings["tab_visible_car_rental"])
        
        # Check MainWindow callback
        self.assertTrue(self.main_window.update_tab_visibility_called)

if __name__ == '__main__':
    unittest.main()
