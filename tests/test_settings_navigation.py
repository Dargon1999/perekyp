import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from PyQt6.QtWidgets import QApplication, QStackedWidget, QListWidget, QPushButton, QCheckBox, QComboBox

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock StyleManager
sys.modules['gui.styles'] = MagicMock()
from gui.styles import StyleManager
StyleManager.get_theme.return_value = {
    'bg_main': '#ffffff', 'text_main': '#000000', 'bg_tertiary': '#eeeeee',
    'success': '#00ff00', 'text_secondary': '#888888', 'border': '#cccccc',
    'input_bg': '#ffffff', 'accent': '#0000ff', 'bg_secondary': '#dddddd',
    'danger': '#ff0000', 'accent_hover': '#0000aa'
}

from gui.tabs.settings_tab import SettingsTab

app = QApplication.instance() or QApplication([])

class TestSettingsNavigation(unittest.TestCase):
    def setUp(self):
        self.mock_data_manager = MagicMock()
        self.mock_data_manager.get_setting.return_value = "dark" # Default theme
        self.mock_auth_manager = MagicMock()
        self.mock_main_window = MagicMock()
        
        # Patch SecurityManager to avoid init issues
        with patch('gui.tabs.settings_tab.SecurityManager'):
            self.tab = SettingsTab(self.mock_data_manager, self.mock_auth_manager, self.mock_main_window)

    def test_initial_structure(self):
        """Test that the main layout contains sidebar and stack."""
        self.assertIsInstance(self.tab.nav_list, QListWidget)
        self.assertIsInstance(self.tab.content_stack, QStackedWidget)
        
        # Check Sidebar items
        self.assertEqual(self.tab.nav_list.count(), 5)
        self.assertEqual(self.tab.nav_list.item(0).text(), "Основные")
        self.assertEqual(self.tab.nav_list.item(1).text(), "Обновление")
        self.assertEqual(self.tab.nav_list.item(2).text(), "Управление вкладками")
        self.assertEqual(self.tab.nav_list.item(3).text(), "Дополнительные")
        self.assertEqual(self.tab.nav_list.item(4).text(), "Связь с лидером")

    def test_navigation_switching(self):
        """Test that clicking nav items changes the stacked widget page."""
        # Initial state
        self.assertEqual(self.tab.content_stack.currentIndex(), 0)
        
        # Switch to "Update" (Index 1)
        self.tab.nav_list.setCurrentRow(1)
        # Note: setCurrentRow emits currentRowChanged, which is connected to on_nav_changed
        self.assertEqual(self.tab.content_stack.currentIndex(), 1)
        
        # Switch to "Contact" (Index 4)
        self.tab.nav_list.setCurrentRow(4)
        self.assertEqual(self.tab.content_stack.currentIndex(), 4)

    def test_subtab_content_existence(self):
        """Test that key widgets exist in sub-tabs."""
        # General Page (Index 0)
        general_page = self.tab.content_stack.widget(0)
        self.assertTrue(general_page)
        self.assertTrue(hasattr(self.tab, 'theme_combo'))
        self.assertIsInstance(self.tab.theme_combo, QComboBox)
        
        # Update Page (Index 1)
        update_page = self.tab.content_stack.widget(1)
        self.assertTrue(update_page)
        self.assertTrue(hasattr(self.tab, 'check_update_btn'))
        self.assertIsInstance(self.tab.check_update_btn, QPushButton)
        
        # Tab Mgmt Page (Index 2)
        mgmt_page = self.tab.content_stack.widget(2)
        self.assertTrue(mgmt_page)
        self.assertTrue(hasattr(self.tab, 'tab_toggles'))
        self.assertIn('clothes', self.tab.tab_toggles)
        
        # Advanced Page (Index 3)
        adv_page = self.tab.content_stack.widget(3)
        self.assertTrue(adv_page)
        self.assertTrue(hasattr(self.tab, 'admin_input'))
        
        # Contact Page (Index 4)
        contact_page = self.tab.content_stack.widget(4)
        self.assertTrue(contact_page)
        self.assertTrue(hasattr(self.tab, 'feedback_widget'))
        # Check FeedbackWidget elements
        fb = self.tab.feedback_widget
        self.assertTrue(hasattr(fb, 'topic_combo'))
        self.assertTrue(hasattr(fb, 'screen_btn'))
        self.assertTrue(hasattr(fb, 'send_btn'))

if __name__ == '__main__':
    unittest.main()
