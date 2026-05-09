
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit
from PyQt6.QtCore import Qt

# Ensure QApplication
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.tabs.settings_tab import SettingsTab
from gui.security_manager import SecurityManager

class FakeFeedbackWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()

class TestSettingsV8(unittest.TestCase):
    def setUp(self):
        self.mock_data_manager = MagicMock()
        self.mock_auth_manager = MagicMock()
        self.mock_main_window = MagicMock()
        
        # Patch FeedbackWidget to avoid QWidget parent issues
        patcher = patch('gui.tabs.settings_tab.FeedbackWidget', side_effect=FakeFeedbackWidget)
        self.MockFeedbackWidget = patcher.start()
        self.addCleanup(patcher.stop)
        
        # Mock global data for backup
        self.mock_data_manager.get_global_data.return_value = ""
        
        def get_setting_side_effect(key, default=None):
            if key == "hidden_tabs":
                return []
            if key == "theme":
                return "dark"
            return default
            
        self.mock_data_manager.get_setting.side_effect = get_setting_side_effect
        
        # Patch SecurityManager to avoid file I/O
        with patch('gui.tabs.settings_tab.SecurityManager') as MockSecMan:
            self.mock_security_manager = MockSecMan.return_value
            self.mock_security_manager.verify_code.return_value = True
            
            self.settings_tab = SettingsTab(
                self.mock_data_manager,
                self.mock_auth_manager,
                self.mock_main_window
            )
            
            # Inject our mock security manager (since it's created in init)
            self.settings_tab.security_manager = self.mock_security_manager
            
            # Show widget to ensure isVisible checks work
            self.settings_tab.show()

    def test_init_ui(self):
        """Test UI components are created."""
        self.assertIsNotNone(self.settings_tab.nav_group)
        self.assertIsNotNone(self.settings_tab.content_stack)
        # Check tabs count (5 tabs)
        self.assertEqual(len(self.settings_tab.nav_buttons), 5)
        # Advanced page is index 3
        self.assertTrue(hasattr(self.settings_tab, 'btn_change_admin'))
        self.assertTrue(hasattr(self.settings_tab, 'btn_change_user'))
        self.assertTrue(hasattr(self.settings_tab, 'reset_btn'))

    def test_advanced_tab_access_denied(self):
        """Test access to Advanced tab is blocked without login."""
        self.settings_tab.current_role = None
        
        # Mock SettingsLoginDialog
        with patch('gui.tabs.settings_tab.SettingsLoginDialog') as MockDlg:
            instance = MockDlg.return_value
            instance.exec.return_value = False # Cancelled
            
            # Click Advanced (index 3)
            self.settings_tab.on_nav_clicked(3)
            
            # Should NOT change index to 3
            # Assuming default is 0
            self.assertNotEqual(self.settings_tab.content_stack.currentIndex(), 3)
            
            # Should revert nav button check (assuming prev was 0)
            # self.assertTrue(self.settings_tab.nav_buttons[0].isChecked())

    def test_advanced_tab_access_admin(self):
        """Test access to Advanced tab as Admin."""
        self.settings_tab.current_role = None
        
        with patch('gui.tabs.settings_tab.SettingsLoginDialog') as MockDlg:
            instance = MockDlg.return_value
            instance.exec.return_value = True # Success
            instance.role = "admin"
            
            # Click Advanced
            self.settings_tab.on_nav_clicked(3)
            
            # Should change index
            self.assertEqual(self.settings_tab.content_stack.currentIndex(), 3)
            self.assertEqual(self.settings_tab.current_role, "admin")
            
            # Check visibility
            self.assertTrue(self.settings_tab.btn_change_admin.isVisible())
            self.assertTrue(self.settings_tab.reset_btn.isVisible())

    def test_advanced_tab_access_user(self):
        """Test access to Advanced tab as User."""
        self.settings_tab.current_role = None
        
        with patch('gui.tabs.settings_tab.SettingsLoginDialog') as MockDlg:
            instance = MockDlg.return_value
            instance.exec.return_value = True
            instance.role = "user" # or "extra"
            
            # Click Advanced
            self.settings_tab.on_nav_clicked(3)
            
            # Should change index
            self.assertEqual(self.settings_tab.content_stack.currentIndex(), 3)
            self.assertEqual(self.settings_tab.current_role, "user")
            
            # Check visibility
            self.assertFalse(self.settings_tab.btn_change_admin.isVisible())
            self.assertFalse(self.settings_tab.reset_btn.isVisible())
            # User button should be visible (default)
            self.assertTrue(self.settings_tab.btn_change_user.isVisible())

    def test_license_eye_icon(self):
        """Test license eye icon toggling."""
        # Initial state (password mode)
        self.assertEqual(self.settings_tab.license_input.echoMode(), QLineEdit.EchoMode.Password)
        
        # Click toggle
        self.settings_tab.toggle_license_visibility(True) # Checked = Show
        self.assertEqual(self.settings_tab.license_input.echoMode(), QLineEdit.EchoMode.Normal)
        
        self.settings_tab.toggle_license_visibility(False) # Unchecked = Hide
        self.assertEqual(self.settings_tab.license_input.echoMode(), QLineEdit.EchoMode.Password)

    def test_backup_logic(self):
        """Test backup interactions."""
        # Set fake path
        self.settings_tab.backup_path_input.setText("C:/Backup")
        self.mock_data_manager.get_global_data.return_value = "C:/Backup"
        
        # Test Manual Backup
        with patch.object(self.settings_tab.data_manager, 'create_backup') as mock_backup:
            with patch('PyQt6.QtWidgets.QMessageBox.information'):
                self.settings_tab.on_backup_now()
                mock_backup.assert_called_once()
                # Check args
                args = mock_backup.call_args
                self.assertEqual(args[1]['extra_channel'], "C:/Backup")

if __name__ == '__main__':
    unittest.main()
