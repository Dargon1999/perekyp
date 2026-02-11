import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint, QSize
from gui.tabs.mining_tab import MiningTab, PricePopup
from gui.localization_manager import LocalizationManager

# Ensure QApplication exists
app = QApplication.instance() or QApplication([])

class TestMiningTab(unittest.TestCase):
    def setUp(self):
        self.mock_data_manager = MagicMock()
        self.mock_data_manager.get_filter_history.return_value = []
        self.mock_data_manager.get_profile_stats.return_value = {
            "starting_amount": 0,
            "income": 0,
            "expense": 0,
            "profit": 0,
            "current_balance": 0
        }
        self.mock_data_manager.get_category_data.return_value = []
        
        # Mock StyleManager to avoid theme errors
        patcher = patch('gui.tabs.generic_tab.StyleManager')
        self.MockStyleManager = patcher.start()
        self.MockStyleManager.get_theme.return_value = {
            'bg_secondary': '#2c3e50', 'text_secondary': '#ecf0f1', 'border': '#34495e',
            'bg_tertiary': '#34495e', 'text_main': '#ecf0f1', 'success': '#2ecc71',
            'input_bg': '#34495e'
        }
        self.addCleanup(patcher.stop)

        # Patch refresh_data to avoid data manager calls
        patcher_refresh = patch('gui.tabs.generic_tab.GenericTab.refresh_data')
        self.mock_refresh = patcher_refresh.start()
        self.addCleanup(patcher_refresh.stop)

        self.tab = MiningTab(self.mock_data_manager)
        self.tab.show()

    def tearDown(self):
        self.tab.close()

    def test_info_icon_exists(self):
        """Test that the info icon is created and added to the layout."""
        self.assertTrue(hasattr(self.tab, 'info_btn'))
        self.assertTrue(self.tab.info_btn.isVisible())
        
        # Check icon size
        self.assertEqual(self.tab.info_btn.width(), 24)
        self.assertEqual(self.tab.info_btn.height(), 24)

    def test_popup_creation_and_content(self):
        """Test that clicking the icon opens the popup with correct content."""
        # Click the button
        self.tab.info_btn.click()
        
        self.assertIsNotNone(self.tab.popup)
        self.assertTrue(self.tab.popup.isVisible())
        self.assertIsInstance(self.tab.popup, PricePopup)
        
        # Check content
        lm = LocalizationManager()
        expected_title = lm.translations['ru']['harvest.price_comparison_title']
        
        # Find labels in popup
        labels = self.tab.popup.findChildren(QWidget) # QWidget includes QLabel
        found_title = False
        found_rabbit = False
        found_price = False
        found_integrity = False
        
        expected_integrity = lm.translations['ru'].get('harvest.price_comparison_integrity_info', '')
        
        for widget in labels:
            if hasattr(widget, 'text'):
                txt = widget.text()
                if txt == expected_title:
                    found_title = True
                if "Кролик" in txt: # Rabbit in Russian
                    found_rabbit = True
                if "1 160 $" in txt:
                    found_price = True
                if expected_integrity in txt:
                    found_integrity = True
                    
        self.assertTrue(found_title, "Title not found in popup")
        self.assertTrue(found_rabbit, "Rabbit row not found")
        self.assertTrue(found_price, "Price not found")
        self.assertTrue(found_integrity, "Integrity info not found")

    def test_popup_positioning_responsive(self):
        """Test responsive positioning logic."""
        # Mock parent window width < 768
        mock_window = MagicMock()
        mock_window.width.return_value = 500
        # Mock geometry to return a rect centered at 250, 250
        mock_rect = MagicMock()
        mock_rect.center.return_value = QPoint(250, 250)
        mock_window.geometry.return_value = mock_rect
        
        test_popup = PricePopup(None)
        
        # Mock parent() of the popup
        with patch.object(test_popup, 'parent', return_value=mock_window):
            # Mock sizeHint to return QSize
            with patch.object(test_popup, 'sizeHint', return_value=QSize(100, 100)):
                test_popup.move = MagicMock()
                
                # Test Responsive
                test_popup.show_at(QPoint(0, 0))
                
                expected_x = 250 - 50 # 200
                expected_y = 250 - 50 # 200
                
                test_popup.move.assert_called_with(expected_x, expected_y)

    def test_popup_positioning_default(self):
        """Test default positioning logic."""
        mock_window = MagicMock()
        mock_window.width.return_value = 1000
        
        test_popup = PricePopup(None)
        
        with patch.object(test_popup, 'parent', return_value=mock_window):
             # Mock sizeHint to return QSize
             with patch.object(test_popup, 'sizeHint', return_value=QSize(100, 100)):
                 test_popup.move = MagicMock()
                 
                 # Test Default
                 with patch('PyQt6.QtWidgets.QApplication.primaryScreen') as mock_screen:
                     mock_screen.return_value.geometry.return_value.right.return_value = 2000
                     mock_screen.return_value.geometry.return_value.bottom.return_value = 2000
                     
                     test_popup.show_at(QPoint(100, 100))
                     
                     test_popup.move.assert_called_with(100, 100)

if __name__ == '__main__':
    unittest.main()
