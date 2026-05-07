
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
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
    'danger': '#ff0000'
}

from gui.tabs.settings_tab import SettingsTab

app = QApplication.instance() or QApplication([])

class TestIntegrationSettings(unittest.TestCase):
    def setUp(self):
        self.mock_security_manager = MagicMock()
        # Default behavior: Not locked, no previous attempts
        self.mock_security_manager.check_lockout.return_value = 0
        self.mock_security_manager.get_attempts.return_value = 0
        
        # Mock verify_code logic (True if "correct", False otherwise)
        def verify_side_effect(key, code):
            return code == "correct"
        self.mock_security_manager.verify_code.side_effect = verify_side_effect
        
        # Mock register_attempt
        def register_side_effect(role, success):
            if success:
                return False, 0
            else:
                return False, 0 # Assume not locked for simple tests
        self.mock_security_manager.register_attempt.side_effect = register_side_effect

        self.mock_data_manager = MagicMock()
        self.mock_auth_manager = MagicMock()
        self.mock_main_window = MagicMock()
        
        with patch('gui.tabs.settings_tab.SecurityManager', return_value=self.mock_security_manager):
            self.tab = SettingsTab(self.mock_data_manager, self.mock_auth_manager, self.mock_main_window)
            self.tab.security_manager = self.mock_security_manager
            
            # Manually trigger setup that usually happens in main app loop or after init
            # The __init__ of SettingsTab calls setup_ui() which calls setup_login_page()
            # So buttons should be there.

    def test_full_admin_login_flow_success(self):
        """Test typing correct code -> clicking button -> success UI update"""
        # 1. Type correct code
        self.tab.admin_input.setText("correct")
        
        # Mock show_2fa_dialog to return True
        self.tab.show_2fa_dialog = MagicMock(return_value=True)

        # 2. Mock Worker to run synchronously or simulate signal
        # Since SettingsLoginWorker is threaded, we need to ensure it runs or we mock the connection
        # The easiest way is to mock SettingsLoginWorker to just emit immediately upon start()
        
        with patch('gui.tabs.settings_tab.SettingsLoginWorker') as MockWorkerClass:
            mock_worker_instance = MockWorkerClass.return_value
            mock_worker_instance.finished = MagicMock()
            
            # We need to capture the callback passed to connect
            # But connect is called on the instance's signal
            # This is tricky with mocks. 
            
            # Alternative: Just call attempt_login and see if it tries to start worker
            self.tab.attempt_login("admin")
            
            # Verify worker started
            mock_worker_instance.start.assert_called_once()
            
            # Now MANUALLY call the slot that would be called by the signal
            # lambda s, m, d: self.on_login_check_finished(role, s, m, d, input_field, btn)
            # We can call on_login_check_finished directly to test the UI reaction
            
            self.tab.on_login_check_finished("admin", True, "Success", 0.0, self.tab.admin_input, self.tab.admin_btn)
            
            # Check UI updates
            self.assertEqual(self.tab.login_status_lbl.text(), "")
            self.assertEqual(self.tab.adv_stack.currentIndex(), 1) # Page 1 is Admin

    def test_full_admin_login_flow_failure(self):
        """Test typing wrong code -> clicking button -> error UI update"""
        self.tab.admin_input.setText("wrong")
        
        with patch('gui.tabs.settings_tab.SettingsLoginWorker') as MockWorkerClass:
            mock_worker_instance = MockWorkerClass.return_value
            
            self.tab.attempt_login("admin")
            mock_worker_instance.start.assert_called_once()
            
            # Simulate failure callback
            self.tab.on_login_check_finished("admin", False, "Неверный код", 0.0, self.tab.admin_input, self.tab.admin_btn)
            
            # Check UI updates
            self.assertEqual(self.tab.login_status_lbl.text(), "Неверный код")
            self.assertIn("color: #e74c3c", self.tab.login_status_lbl.styleSheet())
            self.assertEqual(self.tab.adv_stack.currentIndex(), 0) # Still on login page

    def test_empty_code_check(self):
        """Test that empty code does not start worker and shows error"""
        self.tab.admin_input.setText("")
        
        with patch('gui.tabs.settings_tab.SettingsLoginWorker') as MockWorkerClass:
            self.tab.attempt_login("admin")
            
            # Worker should NOT start
            MockWorkerClass.assert_not_called()
            
            # Label should show error
            self.assertEqual(self.tab.login_status_lbl.text(), "Введите код доступа")

if __name__ == '__main__':
    unittest.main()
