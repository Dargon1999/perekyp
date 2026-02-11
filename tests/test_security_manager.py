
import unittest
import os
import json
import time
import shutil
from unittest.mock import MagicMock
from gui.security_manager import SecurityManager

class TestSecurityManager(unittest.TestCase):
    def setUp(self):
        # Mock DataManager
        self.mock_data_manager = MagicMock()
        self.mock_data_manager.get_secure_value.return_value = "" # Default empty
        
        # Setup temporary directory for lockout file
        self.test_dir = "test_data"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
            
        # Patch environment to use test dir
        self.original_appdata = os.environ.get("APPDATA")
        os.environ["APPDATA"] = os.path.abspath(self.test_dir)
        
        # Create SecurityManager
        # We need to ensure MoneyTracker dir exists in test_dir
        os.makedirs(os.path.join(self.test_dir, "MoneyTracker"), exist_ok=True)
        self.security_manager = SecurityManager(self.mock_data_manager)

    def tearDown(self):
        # Restore environment
        if self.original_appdata:
            os.environ["APPDATA"] = self.original_appdata
        
        # Cleanup - retry a few times for file locks
        if os.path.exists(self.test_dir):
            for i in range(5):
                try:
                    shutil.rmtree(self.test_dir)
                    break
                except Exception:
                    time.sleep(0.1)

    def test_lockout_logic(self):
        role = "admin"
        
        # 1. Initial state: no lockout
        self.assertEqual(self.security_manager.check_lockout(role), 0)
        self.assertEqual(self.security_manager.get_attempts(role), 0)
        
        # 2. Fail 1 time
        is_locked, duration = self.security_manager.register_attempt(role, False)
        self.assertFalse(is_locked)
        self.assertEqual(self.security_manager.get_attempts(role), 1)
        
        # 3. Fail 2 times
        is_locked, duration = self.security_manager.register_attempt(role, False)
        self.assertFalse(is_locked)
        self.assertEqual(self.security_manager.get_attempts(role), 2)
        
        # 4. Fail 3 times -> Lockout
        is_locked, duration = self.security_manager.register_attempt(role, False)
        self.assertTrue(is_locked)
        # Verify duration is around 30 seconds (allow small margin)
        self.assertTrue(29 <= duration <= 31, f"Duration {duration} should be ~30s")
        
        # 5. Check lockout active
        remaining = self.security_manager.check_lockout(role)
        self.assertTrue(remaining > 0)
        
    def test_verify_code_default(self):
        # Test default code behavior
        self.mock_data_manager.get_secure_value.return_value = ""
        
        # Correct default code
        self.assertTrue(self.security_manager.verify_code("admin_code", "SanyaDargon"))
        
        # Incorrect code
        self.assertFalse(self.security_manager.verify_code("admin_code", "WrongCode"))

if __name__ == '__main__':
    unittest.main()
