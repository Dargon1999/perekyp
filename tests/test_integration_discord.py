
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json
from PyQt6.QtCore import QCoreApplication

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.widgets.feedback_widget import FeedbackWorker

# Needed for QThread
app = QCoreApplication.instance()
if app is None:
    app = QCoreApplication([])

class TestIntegrationDiscord(unittest.TestCase):
    def setUp(self):
        self.api_url = "https://discord.com/api/webhooks/test_id/test_token"
        self.token = "dummy_token" # Not used for Discord webhook but kept for signature
        self.data = {
            "topic": "Test Bug",
            "message": "This is a test feedback message.",
            "technical_data": json.dumps({
                "OS": "Windows 10",
                "Version": "8.0.0"
            })
        }
        self.worker = FeedbackWorker(self.api_url, self.token, self.data)

    @patch('requests.post')
    def test_discord_payload_structure(self, mock_post):
        """Integration test: Verify correct payload format for Discord."""
        # Setup mock success
        mock_response = MagicMock()
        mock_response.status_code = 204 # Discord success often 204 No Content
        mock_post.return_value = mock_response
        
        # Run worker synchronously (or wait for signal, but run() is blocking in this context if called directly)
        # Note: QThread.run() is the entry point. In a real app start() calls run() in a thread.
        # Calling run() directly executes in main thread, which is fine for testing logic.
        self.worker.run()
        
        # Verify request
        self.assertTrue(mock_post.called)
        args, kwargs = mock_post.call_args
        
        # Check URL
        self.assertEqual(args[0], self.api_url)
        
        # Check Headers
        self.assertIn("User-Agent", kwargs['headers'])
        self.assertIn("MoneyTracker/V8", kwargs['headers']['User-Agent'])
        
        # Check Payload (JSON or files)
        if 'json' in kwargs:
            payload = kwargs['json']
        elif 'data' in kwargs:
             # If using files, payload is in 'payload_json' string within data
             payload = json.loads(kwargs['data']['payload_json'])
        else:
            self.fail("No data/json sent in request")
            
        # Verify Embeds structure
        self.assertIn("embeds", payload)
        embed = payload["embeds"][0]
        self.assertEqual(embed["title"], "Feedback: Test Bug")
        self.assertEqual(embed["description"], "This is a test feedback message.")
        
        # Verify Technical Data in Fields
        fields = embed["fields"]
        tech_field = next((f for f in fields if f["name"] == "Technical Data"), None)
        self.assertIsNotNone(tech_field)
        self.assertIn("**OS:** Windows 10", tech_field["value"])

    @patch('requests.post')
    def test_retry_logic(self, mock_post):
        """Integration test: Verify 3 retries on failure."""
        # Setup failure
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Speed up sleeps
        with patch('time.sleep', return_value=None):
            self.worker.run()
            
        self.assertEqual(mock_post.call_count, 3)

    @patch('requests.post')
    def test_timeout_setting(self, mock_post):
        """Integration test: Verify timeout is set to at least 10s."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        self.worker.run()
        
        args, kwargs = mock_post.call_args
        self.assertIn('timeout', kwargs)
        self.assertGreaterEqual(kwargs['timeout'], 10)

if __name__ == '__main__':
    unittest.main()
