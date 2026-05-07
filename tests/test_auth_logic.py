import unittest
from unittest.mock import MagicMock, patch
from auth.auth_manager import AuthManager

class TestAuthLogic(unittest.TestCase):
    def setUp(self):
        self.auth = AuthManager()

    def test_hwid_generation(self):
        hwid = self.auth.get_hwid()
        self.assertIsInstance(hwid, str)
        self.assertGreater(len(hwid), 10)
        
        # Verify it's consistent
        hwid2 = self.auth.get_hwid()
        self.assertEqual(hwid, hwid2)

    @patch('requests.get')
    def test_validate_key_hwid_mismatch(self, mock_get):
        # Mocking HWID mismatch response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "hwid": {"stringValue": "DIFFERENT_HWID"},
                "is_active": {"booleanValue": True}
            }
        }
        mock_get.return_value = mock_response
        
        success, message, expires = self.auth.validate_key("test", "pass", "key123")
        self.assertFalse(success)
        self.assertEqual(message, "ERR_HWID_MISMATCH")

    @patch('requests.get')
    @patch('requests.patch')
    def test_deactivate_key_success(self, mock_patch, mock_get):
        # Mocking key document fetch
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "fields": {
                "login": {"stringValue": "user1"},
                "password": {"stringValue": "pass1"}
            }
        }
        mock_get.return_value = mock_get_response
        
        # Mocking patch success
        mock_patch_response = MagicMock()
        mock_patch_response.status_code = 200
        mock_patch.return_value = mock_patch_response
        
        success, message = self.auth.deactivate_key("user1", "pass1", "key123")
        self.assertTrue(success)
        self.assertIn("успешно сброшена", message)

if __name__ == '__main__':
    unittest.main()
