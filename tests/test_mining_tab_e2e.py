
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtTest import QTest

from gui.tabs.mining_tab import MiningTab, PricePopup
from gui.localization_manager import LocalizationManager

# Ensure one QApplication instance
app = QApplication.instance() or QApplication([])

class TestMiningTabE2E(unittest.TestCase):
    def setUp(self):
        # Mock DataManager
        self.mock_data_manager = MagicMock()
        self.mock_data_manager.get_filter_history.return_value = []
        self.mock_data_manager.get_profile_stats.return_value = {
            "starting_amount": 0, "income": 0, "expense": 0, "profit": 0, "current_balance": 0
        }
        self.mock_data_manager.get_category_data.return_value = []

        # Mock StyleManager
        patcher = patch('gui.tabs.generic_tab.StyleManager')
        self.MockStyleManager = patcher.start()
        self.MockStyleManager.get_theme.return_value = {
            'bg_secondary': '#2c3e50', 'text_secondary': '#ecf0f1', 'border': '#34495e',
            'bg_tertiary': '#34495e', 'text_main': '#ecf0f1', 'success': '#2ecc71', 'input_bg': '#34495e'
        }
        self.addCleanup(patcher.stop)

        # Patch refresh_data to avoid side effects during init
        patcher_refresh = patch('gui.tabs.generic_tab.GenericTab.refresh_data')
        self.mock_refresh = patcher_refresh.start()
        self.addCleanup(patcher_refresh.stop)

        # Initialize MiningTab
        self.mining_tab = MiningTab(self.mock_data_manager)
        self.mining_tab.resize(800, 600)
        self.mining_tab.show()
        
        # Ensure localization is initialized
        self.lm = LocalizationManager()

    def test_e2e_icon_click_shows_correct_table(self):
        """
        E2E Scenario:
        1. User clicks Info Icon.
        2. Popup appears.
        3. Table contains correct Price/Animal data.
        4. User presses ESC.
        5. Popup closes.
        """
        # 1. Locate Info Icon
        info_btn = self.mining_tab.info_btn
        self.assertIsNotNone(info_btn, "Info button should exist")
        self.assertTrue(info_btn.isVisible(), "Info button should be visible")

        # 2. Click Info Icon
        QTest.mouseClick(info_btn, Qt.MouseButton.LeftButton)
        
        # Verify Popup is created and shown
        popup = self.mining_tab.popup
        self.assertIsNotNone(popup, "Popup should be created after click")
        self.assertTrue(popup.isVisible(), "Popup should be visible after click")
        
        # 3. Verify Table Content
        # We expect a QGridLayout with labels.
        # Structure: 
        # Row 0: Headers
        # Row 1..5: Data
        
        # Helper to get text from grid layout at row, col
        def get_grid_text(grid, r, c):
            item = grid.itemAtPosition(r, c)
            if item and item.widget():
                return item.widget().text()
            return None

        # Find the grid layout inside popup layout
        # Popup layout is QVBoxLayout. 
        # Item 0: Title
        # Item 1: Grid Layout
        # Item 2: Integrity Info Label (New)
        
        main_layout = popup.layout
        self.assertEqual(main_layout.count(), 3, "Popup should have Title, Grid, and Integrity Info")
        
        # Item 0 is title widget
        title_widget = main_layout.itemAt(0).widget()
        self.assertEqual(title_widget.text(), self.lm.translations['ru']['harvest.price_comparison_title'])
        
        # Item 1 is grid layout
        grid_layout = main_layout.itemAt(1).layout()
        self.assertIsNotNone(grid_layout, "Grid layout should exist")
        
        # Item 2 is integrity info
        integrity_widget = main_layout.itemAt(2).widget()
        expected_integrity = self.lm.translations['ru']['harvest.price_comparison_integrity_info']
        self.assertEqual(integrity_widget.text(), expected_integrity)

        # Expected Data from specification
        expected_data = [
            ("rabbit", "1 000 $", "1 160 $"),
            ("boar", "2 500 $", "2 900 $"),
            ("deer", "4 000 $", "4 640 $"),
            ("coyote", "7 500 $", "8 700 $"),
            ("cougar", "15 000 $", "17 400 $")
        ]

        # Verify Headers (Row 0)
        headers = [
            self.lm.translations['ru']['harvest.price_comparison_animal'],
            self.lm.translations['ru']['harvest.price_comparison_buyer'],
            self.lm.translations['ru']['harvest.price_comparison_rednecks']
        ]
        for col, expected_header in enumerate(headers):
            text = get_grid_text(grid_layout, 0, col)
            self.assertEqual(text, expected_header.upper(), f"Header at col {col} mismatch")

        # Verify Data Rows (1 to 5)
        for i, (animal_key, buyer_price, rednecks_price) in enumerate(expected_data):
            row = i + 1
            animal_name = self.lm.translations['ru'][f'harvest.price_comparison_{animal_key}']
            
            # Col 0: Animal Name
            self.assertEqual(get_grid_text(grid_layout, row, 0), animal_name)
            # Col 1: Buyer Price
            self.assertEqual(get_grid_text(grid_layout, row, 1), buyer_price)
            # Col 2: Rednecks Price
            self.assertEqual(get_grid_text(grid_layout, row, 2), rednecks_price)

        # 4. Simulate ESC Key to close
        # We need to send KeyPress to the popup
        QTest.keyClick(popup, Qt.Key.Key_Escape)
        
        # 5. Verify Popup closes
        self.assertFalse(popup.isVisible(), "Popup should be hidden after pressing ESC")

    def tearDown(self):
        self.mining_tab.deleteLater()
