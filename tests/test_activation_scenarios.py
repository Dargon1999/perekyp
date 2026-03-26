import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.auth_manager import AuthManager
import json
from datetime import datetime, timedelta

class TestActivationLogic(unittest.TestCase):
    def setUp(self):
        self.auth = AuthManager()
        self.auth.hwid = "test-hwid-new"
        self.api_key = self.auth.api_key
        self.base_url = self.auth.base_url

    @patch('requests.get')
    @patch('requests.patch')
    def test_successful_activation(self, mock_patch, mock_get):
        # Setup mock response for first activation
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "fields": {
                "duration_days": {"integerValue": "30"},
                "is_active": {"booleanValue": True},
                "hwid": {"nullValue": None}
            }
        }
        mock_patch.return_value.status_code = 200

        success, msg, expires = self.auth.validate_key("user", "pass", "KEY-123")
        
        self.assertTrue(success)
        self.assertEqual(msg, "Успешная авторизация")
        mock_patch.assert_called()

    @patch('requests.get')
    @patch('requests.patch')
    def test_rebind_without_delay_same_creds(self, mock_patch, mock_get):
        # Setup mock for key bound to another HWID, same credentials
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "fields": {
                "hwid": {"stringValue": "completely-different-hwid|cpu|disk|mac"},
                "is_active": {"booleanValue": True},
                "login": {"stringValue": "user"},
                "password": {"stringValue": "pass"}
            }
        }
        mock_patch.return_value.status_code = 200

        # This should now SUCCEED even if last rebind was 1 minute ago,
        # because the 24h delay is removed when credentials match.
        success, msg, expires = self.auth.validate_key("user", "pass", "KEY-123")
        
        self.assertTrue(success)
        self.assertEqual(msg, "Успешная авторизация")
        mock_patch.assert_called()

    @patch('requests.get')
    @patch('requests.patch')
    def test_fuzzy_hwid_match_and_auto_update(self, mock_patch, mock_get):
        # Current HWID (mocked)
        current_hwid = "bios-123|cpu-456|disk-789|mac-000"
        with patch.object(AuthManager, 'get_hwid', return_value=current_hwid):
            # Stored HWID (only MAC changed, BIOS/CPU/Disk same -> 3/4 matches)
            stored_hwid = "bios-123|cpu-456|disk-789|mac-old"
            
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "fields": {
                    "hwid": {"stringValue": stored_hwid},
                    "is_active": {"booleanValue": True},
                    "login": {"stringValue": "user"},
                    "password": {"stringValue": "pass"}
                }
            }
            mock_patch.return_value.status_code = 200

            success, msg, expires = self.auth.validate_key("user", "pass", "KEY-123")
            
            self.assertTrue(success)
            # Should have called patch to update HWID silently
            mock_patch.assert_called()
            # Ensure the call included the NEW HWID
            call_args = mock_patch.call_args[1]
            self.assertIn(current_hwid, str(call_args))

if __name__ == '__main__':
    unittest.main()
