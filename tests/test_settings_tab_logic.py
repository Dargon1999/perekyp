
import unittest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication
from unittest.mock import MagicMock
import time

# Ensure QApplication exists
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from gui.tabs.settings_tab import SettingsLoginWorker

class TestSettingsLoginWorker(unittest.TestCase):
    def setUp(self):
        self.mock_security_manager = MagicMock()
        
    def test_worker_success(self):
        # Setup mock to return True
        self.mock_security_manager.verify_code.return_value = True
        
        worker = SettingsLoginWorker(self.mock_security_manager, "admin", "admin_code", "correct")
        
        # Connect signal
        self.success = False
        self.message = ""
        
        def on_finished(s, m, d):
            self.success = s
            self.message = m
            
        worker.finished.connect(on_finished)
        worker.run() # Run synchronously for test
        
        self.assertTrue(self.success)
        self.assertEqual(self.message, "")
        
    def test_worker_failure(self):
        # Setup mock to return False
        self.mock_security_manager.verify_code.return_value = False
        # Setup register_attempt to return (False, 0)
        self.mock_security_manager.register_attempt.return_value = (False, 0)
        
        worker = SettingsLoginWorker(self.mock_security_manager, "admin", "admin_code", "wrong")
        
        self.success = True
        self.message = ""
        
        def on_finished(s, m, d):
            self.success = s
            self.message = m
            
        worker.finished.connect(on_finished)
        worker.run()
        
        self.assertFalse(self.success)
        self.assertEqual(self.message, "Неверный код доступа")

    def test_worker_lockout(self):
        # Setup mock failure
        self.mock_security_manager.verify_code.return_value = False
        # Setup register_attempt to return (True, 30)
        self.mock_security_manager.register_attempt.return_value = (True, 30.0)
        
        worker = SettingsLoginWorker(self.mock_security_manager, "admin", "admin_code", "wrong")
        
        self.success = True
        self.message = ""
        self.duration = 0
        
        def on_finished(s, m, d):
            self.success = s
            self.message = m
            self.duration = d
            
        worker.finished.connect(on_finished)
        worker.run()
        
        self.assertFalse(self.success)
        self.assertIn("Блокировка", self.message)
        self.assertEqual(self.duration, 30.0)

    def test_worker_empty_code(self):
        # Even though UI filters this, worker should handle it gracefully
        self.mock_security_manager.verify_code.return_value = False
        self.mock_security_manager.register_attempt.return_value = (False, 0)
        
        worker = SettingsLoginWorker(self.mock_security_manager, "admin", "admin_code", "")
        
        self.success = True
        self.message = ""
        
        def on_finished(s, m, d):
            self.success = s
            self.message = m
            
        worker.finished.connect(on_finished)
        worker.run()
        
        self.assertFalse(self.success)
        # Verify it treats it as wrong code (or handled by security manager)
        self.assertEqual(self.message, "Неверный код доступа")

    def test_worker_special_chars(self):
        self.mock_security_manager.verify_code.return_value = False
        self.mock_security_manager.register_attempt.return_value = (False, 0)
        
        worker = SettingsLoginWorker(self.mock_security_manager, "admin", "admin_code", "!@#$%^&*()")
        
        self.success = True
        
        def on_finished(s, m, d):
            self.success = s
            
        worker.finished.connect(on_finished)
        worker.run()
        
        self.assertFalse(self.success)

    def test_worker_limit_excess(self):
        # This mirrors test_worker_lockout but emphasizes the limit aspect
        self.mock_security_manager.verify_code.return_value = False
        self.mock_security_manager.register_attempt.return_value = (True, 60.0) # 60s lockout
        
        worker = SettingsLoginWorker(self.mock_security_manager, "admin", "admin_code", "wrong")
        
        self.success = True
        self.duration = 0
        
        def on_finished(s, m, d):
            self.success = s
            self.duration = d
            
        worker.finished.connect(on_finished)
        worker.run()
        
        self.assertFalse(self.success)
        self.assertEqual(self.duration, 60.0)

if __name__ == '__main__':
    unittest.main()
