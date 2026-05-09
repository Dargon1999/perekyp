import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from utils import format_license_date
from gui.styles import StyleManager

class TestUILogic(unittest.TestCase):
    
    def test_format_license_date(self):
        # 1. ISO 8601 String
        self.assertEqual(format_license_date("2026-06-05T12:43:00"), "05.06.2026 12:43")
        self.assertEqual(format_license_date("2026-06-05 12:43:00"), "05.06.2026 12:43")
        self.assertEqual(format_license_date("2026-06-05"), "05.06.2026 00:00")
        
        # 2. Timestamp (approximate check due to timezone)
        ts = 1780653780.0 # 2026-06-05 12:43:00 UTC (Need to account for local time if utils uses fromtimestamp)
        # utils.py uses fromtimestamp which is local.
        # Let's use a relative timestamp to avoid timezone issues in test
        now = datetime.now()
        ts_now = now.timestamp()
        expected = now.strftime("%d.%m.%Y %H:%M")
        self.assertEqual(format_license_date(ts_now), expected)
        
        # 3. Invalid Inputs
        self.assertEqual(format_license_date(None), "Дата не указана")
        self.assertEqual(format_license_date(""), "Дата не указана")
        self.assertEqual(format_license_date("invalid-date"), "Неверный формат даты")
        
        # 4. Legacy Formats
        self.assertEqual(format_license_date("05.06.2026 12:43"), "05.06.2026 12:43")
        
    def test_theme_manager(self):
        # Test Default
        self.assertEqual(StyleManager.get_theme("light"), StyleManager.LIGHT_THEME)
        self.assertEqual(StyleManager.get_theme("unknown"), StyleManager.LIGHT_THEME)
        
        # Test Dark
        self.assertEqual(StyleManager.get_theme("dark"), StyleManager.DARK_THEME)
        
        # Test Contrast
        light = StyleManager.LIGHT_THEME
        dark = StyleManager.DARK_THEME
        
        self.assertNotEqual(light['bg_main'], dark['bg_main'])
        self.assertNotEqual(light['text_main'], dark['text_main'])

if __name__ == '__main__':
    unittest.main()
