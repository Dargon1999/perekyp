
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from PyQt6.QtCore import QObject, pyqtSignal

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.tabs.settings_tab import SettingsLoginWorker

class TestAdminAuthSimple(unittest.TestCase):
    def test_admin_login_success(self):
        """Test that correct code emits success signal"""
        # Mock SecurityManager
        mock_security = MagicMock()
        mock_security.verify_code.return_value = True
        
        # Create worker with "correct" code
        worker = SettingsLoginWorker(mock_security, "admin", "admin_code", "correct_123")
        
        # Connect signal
        self.success_emitted = False
        self.message = ""
        
        def on_finished(success, msg, duration):
            self.success_emitted = success
            self.message = msg
            
        worker.finished.connect(on_finished)
        worker.run() # Run synchronously for test
        
        self.assertTrue(self.success_emitted, "Should emit success for correct code")
        self.assertEqual(self.message, "", "Message should be empty on success")
        mock_security.verify_code.assert_called_with("admin_code", "correct_123")

    def test_admin_login_failure(self):
        """Test that incorrect code emits failure signal with error message"""
        # Mock SecurityManager
        mock_security = MagicMock()
        mock_security.verify_code.return_value = False
        mock_security.register_attempt.return_value = (False, 0.0) # Not locked yet
        
        # Create worker with "wrong" code
        worker = SettingsLoginWorker(mock_security, "admin", "admin_code", "wrong_123")
        
        # Connect signal
        self.success_emitted = True # Assume true initially to verify change
        self.message = ""
        
        def on_finished(success, msg, duration):
            self.success_emitted = success
            self.message = msg
            
        worker.finished.connect(on_finished)
        worker.run()
        
        self.assertFalse(self.success_emitted, "Should emit failure for wrong code")
        self.assertEqual(self.message, "Неверный код доступа", "Should show correct error message")
        mock_security.verify_code.assert_called_with("admin_code", "wrong_123")

if __name__ == '__main__':
    unittest.main()
