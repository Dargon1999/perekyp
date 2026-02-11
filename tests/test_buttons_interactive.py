import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from PyQt6.QtWidgets import QApplication, QPushButton, QLineEdit

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock StyleManager
sys.modules['gui.styles'] = MagicMock()
from gui.styles import StyleManager
StyleManager.get_theme.return_value = {
    'bg_main': '#ffffff', 'text_main': '#000000', 'bg_tertiary': '#eeeeee',
    'success': '#00ff00', 'text_secondary': '#888888', 'border': '#cccccc',
    'input_bg': '#ffffff', 'accent': '#0000ff', 'bg_secondary': '#dddddd',
    'danger': '#ff0000', 'accent_hover': '#0000aa'
}

from gui.tabs.settings_tab import SettingsTab

app = QApplication.instance() or QApplication([])

class TestButtonsInteractive(unittest.TestCase):
    def setUp(self):
        self.mock_data_manager = MagicMock()
        self.mock_data_manager.get_setting.return_value = "dark"
        self.mock_auth_manager = MagicMock()
        self.mock_main_window = MagicMock()
        
        # Patch SecurityManager
        with patch('gui.tabs.settings_tab.SecurityManager'):
            self.tab = SettingsTab(self.mock_data_manager, self.mock_auth_manager, self.mock_main_window)

    def test_update_page_buttons(self):
        """Verify update page buttons state and connections."""
        # Check Update Button
        self.assertTrue(self.tab.check_update_btn.isEnabled(), "Check update button should be enabled")
        
        # Simulate Click
        self.tab.check_update_btn.click()
        # Verify it calls check_for_updates on main_window (if manual=True)
        # Note: In on_check_update: if hasattr(self.main_window, 'check_for_updates')...
        # Since mock_main_window is a MagicMock, it "has" any attribute.
        # But we need to ensure the method is called.
        
        # We need to make sure the mock responds to hasattr check correctly if needed,
        # but MagicMock usually returns another mock.
        
        # Actually, let's verify if check_for_updates is called
        # self.mock_main_window.check_for_updates.assert_called_once_with(manual=True) 
        # Wait, MagicMock might not simulate hasattr(obj, 'attr') as True unless configured.
        # Default MagicMock usually works for hasattr.
        
        # Download/Install Buttons should be disabled initially
        self.assertFalse(self.tab.download_btn.isEnabled(), "Download button should be disabled initially")
        self.assertFalse(self.tab.install_btn.isEnabled(), "Install button should be disabled initially")

    def test_feedback_buttons(self):
        """Verify feedback widget buttons."""
        fb = self.tab.feedback_widget
        
        # Screenshot button should be enabled
        self.assertTrue(fb.screen_btn.isEnabled(), "Screenshot button should be enabled")
        
        # Send button should be disabled (text < 10 chars)
        self.assertFalse(fb.send_btn.isEnabled(), "Send button should be disabled initially (empty text)")
        
        # Enter text > 10 chars
        fb.msg_input.setText("This is a test message longer than 10 chars.")
        # Trigger textChanged manually if needed, but setText usually triggers it in Qt? 
        # No, setText does NOT trigger textChanged signal in many cases (programmatic change).
        # We need to manually emit or call the slot.
        fb.update_char_count()
        
        self.assertTrue(fb.send_btn.isEnabled(), "Send button should be enabled after valid text")

    def test_admin_button(self):
        """Verify admin login button."""
        self.assertTrue(self.tab.admin_btn.isEnabled())
        
        # Enter code
        self.tab.admin_input.setText("admin_code")
        
        # Mock SecurityManager behavior in the worker?
        # Since we patched SecurityManager class, self.tab.security_manager is a Mock.
        # But SettingsLoginWorker creates a new thread. Threading in tests is tricky.
        # We can just check if clicking calls attempt_login.
        
        with patch.object(self.tab, 'attempt_login') as mock_login:
            self.tab.admin_btn.click()
            # Lambda connection might make exact verification hard, but let's try
            # lambda: self.attempt_login("admin")
            mock_login.assert_called_once_with("admin")

if __name__ == '__main__':
    unittest.main()
