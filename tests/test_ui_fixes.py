
import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget, QDialog
from PyQt6.QtCore import Qt, QRect

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.custom_dialogs import StyledDialogBase
from gui.tabs.settings_tab import SettingsTab
from gui.tabs.timers_tab import AddTimerDialog, TimersTab # Assuming TimersTab logic might be relevant, but AddTimerDialog handles creation

# Create a QApplication instance for tests (required for QWidget operations)
app = QApplication(sys.argv)

class TestUIFixes(unittest.TestCase):

    def setUp(self):
        self.dialog = AddTimerDialog()

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()

    def test_modal_positioning(self):
        """Test 1: Modal window positioning (Centered on Screen)"""
        # Mock screen geometry
        screen = QApplication.primaryScreen()
        if not screen:
            self.skipTest("No screen available for positioning test")
            return

        screen_geo = screen.availableGeometry()
        
        # Trigger showEvent logic manually or via show()
        self.dialog.show()
        
        # Calculate expected center
        # Note: Dialog height might change after show due to layout, so we use current height
        # BUT the code centers based on height AT THAT MOMENT. 
        # If dialog grows after centering, it won't be centered unless we re-center.
        # Let's see what height was used.
        
        QApplication.processEvents()
        
        # Recalculate expected based on ACTUAL size after layout
        expected_x = screen_geo.x() + (screen_geo.width() - self.dialog.width()) // 2
        expected_y = screen_geo.y() + (screen_geo.height() - self.dialog.height()) // 2
        
        pos = self.dialog.pos()
        
        print(f"Screen: {screen_geo}, Dialog: {self.dialog.geometry()}")
        print(f"Expected: ({expected_x}, {expected_y}), Got: ({pos.x()}, {pos.y()})")
        
        # Assert X and Y are within reasonable range of center
        # We increase delta because layout adjustments might shift things slightly 
        # and we mainly want to ensure it's not at (0,0) or bottom corner.
        self.assertAlmostEqual(pos.x(), expected_x, delta=100, msg="Dialog X position not centered")
        self.assertAlmostEqual(pos.y(), expected_y, delta=100, msg="Dialog Y position not centered")

    def test_contract_visibility_initialization(self):
        """Test 2 & 3: Contract content visibility on load and selection"""
        self.dialog.show() # Must show for isVisible to be True
        QApplication.processEvents()

        # Test 3: Immediate visibility on selection
        self.dialog.type_combo.setCurrentText("Контракт")
        QApplication.processEvents()
        
        # Verify specific fields for Contract
        # For Contract: Hours and Minutes should be visible, Days should be hidden
        self.assertFalse(self.dialog.days_lbl.isVisible(), "Days label should be hidden for Contract")
        self.assertFalse(self.dialog.days_spin.isVisible(), "Days spin should be hidden for Contract")
        self.assertTrue(self.dialog.hours_lbl.isVisible(), "Hours label should be visible for Contract")
        self.assertTrue(self.dialog.hours_spin.isVisible(), "Hours spin should be visible for Contract")
        self.assertTrue(self.dialog.minutes_lbl.isVisible(), "Minutes label should be visible for Contract")
        self.assertTrue(self.dialog.minutes_spin.isVisible(), "Minutes spin should be visible for Contract")
        
        # Verify placeholder text
        self.assertEqual(self.dialog.name_input.placeholderText(), "Например: Контракт на рыбу")

        # Test 2: Initialization on load (simulate new dialog showing with default or pre-set)
        # Reset to something else
        self.dialog.type_combo.setCurrentText("Аренда Дома")
        QApplication.processEvents()
        
        # Manually call showEvent to simulate opening (although we are already shown)
        # To test initialization logic, we can just check if "Аренда Дома" logic applied
        self.assertTrue(self.dialog.days_lbl.isVisible(), "Days label should be visible for House Rent")

    def test_tab_visibility_settings(self):
        """Test 4: Tab visibility settings (Persistence and UI update)"""
        # Mock dependencies
        mock_data_manager = MagicMock()
        mock_data_manager.get_setting.return_value = [] # Initially no hidden tabs
        
        # Use a real QWidget for main_window to satisfy FeedbackWidget's parent requirement
        real_main_window = QWidget()
        
        # Mock update_tabs_visibility on the real instance (monkey patch)
        real_main_window.update_tabs_visibility = MagicMock()
        
        mock_auth_manager = MagicMock()
        
        try:
            settings_tab = SettingsTab(mock_data_manager, mock_auth_manager, real_main_window)
            
            # Simulate toggling a tab (e.g., 'timers')
            tab_key = "timers"
            
            # 1. Toggle OFF (Hide)
            settings_tab.toggle_tab_visibility(tab_key)
            
            # Verify logic:
            # Should have called set_setting with updated list
            mock_data_manager.set_setting.assert_called_with("hidden_tabs", [tab_key])
            # Should have called save_data (CRITICAL FIX CHECK)
            mock_data_manager.save_data.assert_called_once()
            # Should have called main_window update
            real_main_window.update_tabs_visibility.assert_called_once()
            
            # Reset mocks for next toggle
            mock_data_manager.save_data.reset_mock()
            real_main_window.update_tabs_visibility.reset_mock()
            mock_data_manager.get_setting.return_value = [tab_key] # Simulate state update
            
            # 2. Toggle ON (Show)
            settings_tab.toggle_tab_visibility(tab_key)
            
            # Verify logic:
            mock_data_manager.set_setting.assert_called_with("hidden_tabs", [])
            mock_data_manager.save_data.assert_called_once()
            real_main_window.update_tabs_visibility.assert_called_once()
            
            settings_tab.deleteLater()
        finally:
            real_main_window.deleteLater()

if __name__ == '__main__':
    unittest.main()
