
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QPushButton

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock StyleManager before importing SettingsTab
sys.modules['gui.styles'] = MagicMock()
from gui.styles import StyleManager
StyleManager.get_theme.return_value = {
    'bg_main': '#ffffff', 'text_main': '#000000', 'bg_tertiary': '#eeeeee',
    'success': '#00ff00', 'text_secondary': '#888888', 'border': '#cccccc',
    'input_bg': '#ffffff', 'accent': '#0000ff', 'bg_secondary': '#dddddd'
}

from gui.tabs.settings_tab import SettingsTab

app = QApplication.instance() or QApplication([])

class TestSettingsButtons(unittest.TestCase):
    def setUp(self):
        self.mock_security_manager = MagicMock()
        self.mock_security_manager.check_lockout.return_value = 0
        self.mock_security_manager.get_attempts.return_value = 0
        
        self.mock_data_manager = MagicMock()
        self.mock_auth_manager = MagicMock()
        self.mock_main_window = MagicMock()
        
        # Patch SecurityManager class usage inside SettingsTab
        with patch('gui.tabs.settings_tab.SecurityManager', return_value=self.mock_security_manager):
            self.tab = SettingsTab(self.mock_data_manager, self.mock_auth_manager, self.mock_main_window)
            # Inject mock security manager directly to be sure
            self.tab.security_manager = self.mock_security_manager
            
    def test_button_style_preservation(self):
        """Test that admin and extra buttons retain their custom colors after theme application."""
        # Ensure login page is set up (it is called in init via setup_ui -> setup_advanced_tab -> setup_login_page)
        # But wait, does init call setup_ui?
        # Looking at previous Read: yes, line 410 calls setup_ui().
        
        # Verify initial style has red/blue
        # We need to find them again as they might be created in setup_ui
        admin_btn = self.tab.admin_btn
        extra_btn = self.tab.extra_btn
        
        # NOTE: setup_ui calls apply_theme at the end usually. 
        # So if my fix works, they should ALREADY be red/blue.
        
        self.assertIn("#e74c3c", admin_btn.styleSheet(), "Admin button should be red initially")
        self.assertIn("#3498db", extra_btn.styleSheet(), "Extra button should be blue initially")
        self.assertNotIn("background-color: transparent", admin_btn.styleSheet(), "Admin button should NOT be transparent")
        
        # Apply theme explicitly again
        self.tab.apply_theme("dark")
        
        # Verify style still has red/blue (not overwritten to transparent)
        self.assertIn("#e74c3c", admin_btn.styleSheet(), "Admin button should keep red color after theme")
        self.assertIn("#3498db", extra_btn.styleSheet(), "Extra button should keep blue color after theme")
        self.assertNotIn("background-color: transparent", admin_btn.styleSheet(), "Admin button should NOT be transparent")

    def test_button_click_connection(self):
        """Test that clicking the button calls attempt_login."""
        # Mock attempt_login
        with patch.object(self.tab, 'attempt_login') as mock_attempt:
            self.tab.admin_btn.click()
            mock_attempt.assert_called_with("admin")
            
            self.tab.extra_btn.click()
            mock_attempt.assert_called_with("extra")

if __name__ == '__main__':
    unittest.main()
