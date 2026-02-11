
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QCheckBox

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.widgets.feedback_widget import FeedbackWidget, FeedbackWorker

# Needed for QWidgets
app = QApplication.instance()
if app is None:
    app = QApplication([])

class TestFeedbackFeatures(unittest.TestCase):
    def setUp(self):
        self.mock_data_manager = MagicMock()
        self.mock_auth_manager = MagicMock()
        self.widget = FeedbackWidget(self.mock_data_manager, self.mock_auth_manager)
        
    def test_checkbox_default_state(self):
        """Test that technical data checkbox exists and is checked by default."""
        self.assertTrue(hasattr(self.widget, 'tech_data_cb'))
        self.assertIsInstance(self.widget.tech_data_cb, QCheckBox)
        self.assertTrue(self.widget.tech_data_cb.isChecked())
        
    def test_tech_data_collection_checked(self):
        """Test collecting technical data when checkbox is checked."""
        self.widget.tech_data_cb.setChecked(True)
        data = self.widget.get_technical_data()
        
        self.assertNotEqual(data, {})
        self.assertIn('os', data)
        self.assertIn('app_version', data)
        self.assertIn('timestamp', data)
        
        # Verify Timestamp Format (DD.MM.YYYY HH:MM)
        ts = data['timestamp']
        try:
            datetime.strptime(ts, "%d.%m.%Y %H:%M")
        except ValueError:
            self.fail(f"Timestamp format incorrect: {ts}. Expected DD.MM.YYYY HH:MM")

    def test_tech_data_collection_unchecked(self):
        """Test that no data is collected when checkbox is unchecked."""
        self.widget.tech_data_cb.setChecked(False)
        data = self.widget.get_technical_data()
        self.assertEqual(data, {})

    @patch('requests.post')
    def test_worker_payload_footer(self, mock_post):
        """Test that the worker adds a footer with the date."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        data = {
            "topic": "Test",
            "message": "Msg",
            "technical_data": "{}"
        }
        worker = FeedbackWorker("http://api", "token", data)
        worker.run()
        
        args, kwargs = mock_post.call_args
        if 'json' in kwargs:
            payload = kwargs['json']
        elif 'data' in kwargs:
             import json
             payload = json.loads(kwargs['data']['payload_json'])
             
        embed = payload['embeds'][0]
        self.assertIn('footer', embed)
        self.assertIn('text', embed['footer'])
        self.assertIn("MoneyTracker V8", embed['footer']['text'])
        # Check date format in footer roughly
        import re
        self.assertTrue(re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", embed['footer']['text']))

if __name__ == '__main__':
    unittest.main()
