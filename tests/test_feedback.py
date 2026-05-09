import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QCoreApplication

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.localization_manager import LocalizationManager
from gui.widgets.feedback_widget import FeedbackWorker

# Needed for QThread/QObject
app = QCoreApplication.instance()
if app is None:
    app = QCoreApplication([])

class TestLocalizationManager(unittest.TestCase):
    def setUp(self):
        # Reset singleton if possible or just use get_instance
        self.loc = LocalizationManager()
        
    def test_singleton(self):
        loc2 = LocalizationManager()
        self.assertIs(self.loc, loc2)
        
    def test_default_language(self):
        # Assuming default is 'ru'
        self.assertEqual(self.loc.current_lang, 'ru')
        
    def test_get_translation(self):
        # Test a known key
        self.loc.current_lang = 'ru'
        # 'topic' is from the known dictionary in context
        self.assertEqual(self.loc.get('topic'), 'Тема:')
        
        self.loc.current_lang = 'en'
        self.assertEqual(self.loc.get('topic'), 'Topic:')
        
    def test_missing_key(self):
        self.assertEqual(self.loc.get('non_existent_key'), 'non_existent_key')

class TestFeedbackWorker(unittest.TestCase):
    def setUp(self):
        self.api_url = "http://test.api/feedback"
        self.token = "test_token"
        self.data = {"topic": "bug", "message": "test"}
        self.worker = FeedbackWorker(self.api_url, self.token, self.data)
        
    @patch('requests.post')
    def test_success_submission(self, mock_post):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        # Setup signal spy
        result = []
        self.worker.finished.connect(lambda s, m, c: result.append((s, m, c)))
        
        # Run
        self.worker.run()
        
        # Verify
        self.assertTrue(result[0][0]) # Success
        self.assertEqual(result[0][2], 201) # Status code
        
    @patch('requests.post')
    def test_validation_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        result = []
        self.worker.finished.connect(lambda s, m, c: result.append((s, m, c)))
        
        self.worker.run()
        
        self.assertFalse(result[0][0])
        self.assertEqual(result[0][2], 400)

    @patch('requests.post')
    def test_server_error_retry(self, mock_post):
        # Fail 3 times
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            result = []
            self.worker.finished.connect(lambda s, m, c: result.append((s, m, c)))
            
            self.worker.run()
            
            self.assertFalse(result[0][0])
            self.assertEqual(result[0][2], 500)
            self.assertEqual(mock_post.call_count, 3)

if __name__ == '__main__':
    unittest.main()
