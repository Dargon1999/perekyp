
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import time
import bcrypt
from PyQt6.QtWidgets import QApplication, QStackedWidget

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.tabs.settings_tab import SettingsTab
from gui.widgets.feedback_widget import FeedbackWorker

# Needed for QWidgets
app = QApplication.instance()
if app is None:
    app = QApplication([])

class TestSettingsLogin(unittest.TestCase):
    def setUp(self):
        self.mock_data_manager = MagicMock()
        self.mock_auth_manager = MagicMock()
        self.mock_main_window = MagicMock()
        
        # Create widget
        self.settings_tab = SettingsTab(
            self.mock_data_manager, 
            self.mock_auth_manager, 
            self.mock_main_window
        )
        
        # Mock UI elements that might be created in setup_ui but we want to control
        # (Though SettingsTab creates them in setup_ui, we can access them after init)
        
        # Ensure we have the attributes (setup_ui calls create_advanced_settings which sets these up)
        # We might need to force creation if it's lazy, but usually it's in init -> setup_ui
        
        # Mock secure storage behavior
        self.mock_data_manager.get_secure_value.return_value = ""
        self.mock_data_manager.save_secure_value = MagicMock()

    def test_verify_code_new_setup(self):
        """Test setting up a code for the first time (storage empty)."""
        self.mock_data_manager.get_secure_value.return_value = ""
        
        # User enters "1234"
        result = self.settings_tab.verify_code("admin_code", "1234")
        
        self.assertTrue(result)
        # Should save hashed version
        self.mock_data_manager.save_secure_value.assert_called_once()
        args = self.mock_data_manager.save_secure_value.call_args[0]
        self.assertEqual(args[0], "admin_code")
        self.assertTrue(args[1].startswith("$2b$")) # bcrypt hash

    def test_verify_code_success_bcrypt(self):
        """Test verifying against a stored bcrypt hash."""
        password = "secret_pass"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.mock_data_manager.get_secure_value.return_value = hashed
        
        self.assertTrue(self.settings_tab.verify_code("admin_code", "secret_pass"))
        self.assertFalse(self.settings_tab.verify_code("admin_code", "wrong_pass"))

    def test_verify_code_legacy_migration(self):
        """Test verifying against legacy plaintext and migrating."""
        legacy_pass = "old_secret"
        self.mock_data_manager.get_secure_value.return_value = legacy_pass
        
        # Should return True and update to bcrypt
        result = self.settings_tab.verify_code("admin_code", "old_secret")
        
        self.assertTrue(result)
        self.mock_data_manager.save_secure_value.assert_called_once()
        saved_hash = self.mock_data_manager.save_secure_value.call_args[0][1]
        self.assertTrue(saved_hash.startswith("$2b$"))

    def test_rate_limiting(self):
        """Test 3 failed attempts trigger lockout."""
        # Setup failed verification
        self.mock_data_manager.get_secure_value.return_value = "$2b$12$somevalidhashbutwefailcheck"
        with patch('bcrypt.checkpw', return_value=False):
            # 3 Failures
            self.settings_tab.attempt_login("admin")
            self.settings_tab.attempt_login("admin")
            self.settings_tab.attempt_login("admin")
            
            # Check lockout
            self.assertIn("admin", self.settings_tab.lockout_until)
            self.assertGreater(self.settings_tab.lockout_until["admin"], time.time())
            
            # 4th attempt should be blocked immediately (no verify call)
            # We reset mock to check if it's called
            with patch.object(self.settings_tab, 'verify_code') as mock_verify:
                self.settings_tab.attempt_login("admin")
                mock_verify.assert_not_called()

    def test_admin_vs_extra_routing(self):
        """Test correct stack page shown for admin vs extra."""
        # Setup success
        self.settings_tab.verify_code = MagicMock(return_value=True)
        
        # Admin
        self.settings_tab.attempt_login("admin")
        self.assertEqual(self.settings_tab.adv_stack.currentIndex(), 1) # Admin page
        
        # Reset
        self.settings_tab.adv_stack.setCurrentIndex(0)
        
        # Extra
        self.settings_tab.attempt_login("extra")
        self.assertEqual(self.settings_tab.adv_stack.currentIndex(), 2) # Extra page

if __name__ == '__main__':
    unittest.main()
