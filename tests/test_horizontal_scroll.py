
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from PyQt6.QtWidgets import QApplication, QScrollBar
from PyQt6.QtCore import Qt

# Ensure we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need to mock these before importing CookingTab if they have top-level side effects or if we want to patch them easily
# But since they are imported inside cooking_tab.py, we can patch them where they are used.

from gui.tabs.cooking_tab import CookingTab

class TestHorizontalScroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    @patch('gui.tabs.cooking_tab.RecipeManager')
    @patch('gui.tabs.cooking_tab.StyleManager')
    def test_scroll_logic(self, MockStyleManager, MockRecipeManager):
        # Setup Mocks for StyleManager
        MockStyleManager.DARK_THEME = {
            'bg_card': '#000', 
            'border': '#fff', 
            'bg_tertiary': '#333', 
            'accent': '#f00', 
            'text_main': '#fff', 
            'text_secondary': '#ccc', 
            'success': '#0f0', 
            'warning': '#ff0', 
            'danger': '#f00',
            'input_bg': '#111'
        }
        
        # Setup Mock for RecipeManager
        mock_rm = MockRecipeManager.return_value
        mock_rm.get_all_recipes.return_value = [] # Start empty
        
        # Init Tab
        # We pass mocks for data_manager and main_window
        tab = CookingTab(MagicMock(), MagicMock())
        
        # 1. Check Initial State
        print("\nTesting Initial State...")
        # Columns should be dynamic now, not hardcoded to 3. 
        # Mocking viewport width to check logic.
        mock_viewport = MagicMock()
        mock_viewport.width.return_value = 1200 # Should be enough for 3 cols (1200 / 340 = 3.5 -> 3)
        with patch.object(tab.scroll, 'viewport', return_value=mock_viewport):
             self.assertEqual(tab.get_column_count(), 3, "Should be 3 columns for 1200px width")
        
        mock_viewport.width.return_value = 800 # 800 / 340 = 2.35 -> 2
        with patch.object(tab.scroll, 'viewport', return_value=mock_viewport):
             self.assertEqual(tab.get_column_count(), 2, "Should be 2 columns for 800px width")
             
        self.assertEqual(tab.scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff, "Initial HScroll should be OFF")
        
        # 2. Simulate Scrolling
        print("Testing Scroll Logic...")
        
        # We'll use a patch context for the scrollbar's maximum value
        # We need to patch the instance's method, but since it's a C++ wrapped object, it's tricky.
        # Instead, we rely on the fact that check_scroll_bottom calls self.scroll.verticalScrollBar().maximum()
        
        # Let's mock the verticalScrollBar method of the scroll area
        mock_vsb = MagicMock()
        mock_vsb.maximum.return_value = 100
        
        with patch.object(tab.scroll, 'verticalScrollBar', return_value=mock_vsb):
            # Case A: Not at bottom (Value = 50, Max = 100)
            print("  Scrolling to 50/100")
            tab.check_scroll_bottom(50)
            self.assertEqual(tab.scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff, "Should be OFF when not at bottom")
            
            # Case B: At bottom (Value = 100, Max = 100)
            print("  Scrolling to 100/100")
            tab.check_scroll_bottom(100)
            self.assertEqual(tab.scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAsNeeded, "Should be AsNeeded when at bottom")
            
            # Case C: Scroll up again (Value = 90, Max = 100)
            # Threshold is max - 5 = 95. So 90 should be OFF.
            print("  Scrolling back to 90/100")
            tab.check_scroll_bottom(90) 
            self.assertEqual(tab.scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff, "Should turn OFF when scrolling up")
            
            # Case D: Near bottom but not quite (Value = 94, Max = 100)
            # Should be OFF
            print("  Scrolling to 94/100")
            tab.check_scroll_bottom(94)
            self.assertEqual(tab.scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff, "Should be OFF just above threshold")

            # Case E: Just inside threshold (Value = 95, Max = 100)
            # Should be ON
            print("  Scrolling to 95/100")
            tab.check_scroll_bottom(95)
            self.assertEqual(tab.scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAsNeeded, "Should be ON at threshold")

if __name__ == '__main__':
    unittest.main()
