
import unittest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from unittest.mock import MagicMock
import os

# Ensure QApplication exists for UI tests
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from gui.tabs.settings_tab import SettingsTab
from data_manager import DataManager

class TestSettingsTabComprehensive(unittest.TestCase):
    def setUp(self):
        self.mock_data_manager = MagicMock(spec=DataManager)
        self.mock_auth_manager = MagicMock()
        self.mock_main_window = None # Pass None to avoid QWidget parent mock issue
        
        # Setup data manager mock
        def get_setting_side_effect(key, default=None):
            if key == "theme": return "dark"
            if key == "header_gta_color": return "#ffffff"
            if key == "header_dargon_color": return "#3b82f6"
            if key == "header_show_dargon": return True
            if key == "listing_cost_enabled": return True
            if key == "listing_cost": return 0.0
            if key == "startup_tab": return "car_rental"
            if key == "contract_notification_mode": return "notify_keep"
            if key == "hidden_tabs": return []
            if key == "window_resizable": return True
            return default
            
        self.mock_data_manager.get_setting.side_effect = get_setting_side_effect
        self.mock_data_manager.get_global_data.return_value = ""
        self.mock_data_manager.get_data_dir.return_value = "/tmp"
        
        # Setup auth manager mock to return strings, not mocks
        self.mock_auth_manager.current_creds = {"key": "test-key"}
        self.mock_auth_manager.load_session.return_value = {"login": "test-user"}
        
        # Initialize SettingsTab
        self.tab = SettingsTab(self.mock_data_manager, self.mock_auth_manager, self.mock_main_window)

    def test_tab_initialization(self):
        self.assertIsNotNone(self.tab.nav_group)
        self.assertIsNotNone(self.tab.content_stack)
        # Should have 7 internal pages
        self.assertEqual(self.tab.content_stack.count(), 7)

    def test_navigation_logic(self):
        # Click index 1 (Update page)
        self.tab.on_nav_clicked(1)
        self.assertEqual(self.tab.content_stack.currentIndex(), 1)
        
        # Verify button check states
        self.assertTrue(self.tab.nav_buttons[1].isChecked())
        self.assertFalse(self.tab.nav_buttons[0].isChecked())

    def test_theme_change_handler(self):
        # Test change to light theme
        self.tab.main_window = MagicMock() # Mock it locally for this test
        self.tab.on_theme_changed(1)
        self.mock_data_manager.set_setting.assert_any_call("theme", "light")
        self.tab.main_window.apply_styles.assert_called()

    def test_palette_color_selection_safety(self):
        # Test with valid hex
        self.tab.main_window = MagicMock() # Mock it locally
        self.tab.on_palette_color_selected("#ff0000")
        self.mock_data_manager.set_setting.assert_any_call("accent_color", "#ff0000")
        
        # Test with invalid hex (should not crash)
        self.tab.on_palette_color_selected("invalid")
        # Should still be #ff0000 or initial
        
    def test_tab_visibility_toggle(self):
        self.mock_data_manager.get_setting.return_value = []
        self.tab.main_window = MagicMock() # Mock it locally
        self.tab.toggle_tab_visibility("mining")
        self.mock_data_manager.set_setting.assert_any_call("hidden_tabs", ["mining"])

    def test_storage_path_validation(self):
        # Mock get_data_dir
        self.mock_data_manager.get_data_dir.return_value = os.getcwd()
        self.tab.update_storage_path_info()
        self.assertIn("Путь доступен", self.tab.path_status_lbl.text())

if __name__ == '__main__':
    unittest.main()
