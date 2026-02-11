import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime

# Ensure we can import modules from project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication

# We need a QApplication instance for QWidget to work
# Check if one exists
if not QApplication.instance():
    app = QApplication(sys.argv)
else:
    app = QApplication.instance()

from gui.tabs.timers_tab import TimersTab

class TestAutoDeleteContracts(unittest.TestCase):
    def setUp(self):
        self.mock_data_manager = MagicMock()
        self.mock_main_window = MagicMock()
        
    def create_tab(self):
        # Helper to create tab with UI setup mocked out
        # and process_expired_contracts mocked out during init so we can test it manually
        with patch('gui.tabs.timers_tab.TimersTab.setup_ui'), \
             patch('gui.tabs.timers_tab.QTimer'), \
             patch('gui.tabs.timers_tab.TimersTab.process_expired_contracts'), \
             patch('gui.tabs.timers_tab.TimersTab.refresh_data'):
            tab = TimersTab(self.mock_data_manager, self.mock_main_window)
        return tab

    def test_auto_delete_enabled_expired_contract(self):
        # Arrange
        self.mock_data_manager.get_setting.return_value = True
        
        expired_time = datetime.now().timestamp() - 100 # 100 seconds ago
        timers = [
            {
                "id": "t1",
                "name": "Contract 1",
                "type": "Контракт",
                "is_running": True,
                "end_time": expired_time,
                "duration": 3600
            }
        ]
        self.mock_data_manager.get_timers.return_value = timers
        self.mock_data_manager.delete_timer.return_value = True
        
        tab = self.create_tab()
        
        # Act
        # We call the method directly. Since it's an instance method, we can just call it.
        # Wait, we mocked it in create_tab using patch on the CLASS.
        # But patch context manager exits after create_tab.
        # So tab.process_expired_contracts should be the real method again.
        
        tab.process_expired_contracts()
        
        # Assert
        self.mock_data_manager.delete_timer.assert_called_with("t1")
        
    def test_auto_delete_disabled_expired_contract(self):
        # Arrange
        self.mock_data_manager.get_setting.return_value = False
        
        expired_time = datetime.now().timestamp() - 100
        timers = [
            {
                "id": "t1",
                "name": "Contract 1",
                "type": "Контракт",
                "is_running": True,
                "end_time": expired_time
            }
        ]
        self.mock_data_manager.get_timers.return_value = timers
        
        tab = self.create_tab()
        
        # Act
        tab.process_expired_contracts()
        
        # Assert
        self.mock_data_manager.delete_timer.assert_not_called()

    def test_auto_delete_enabled_active_contract(self):
        # Arrange
        self.mock_data_manager.get_setting.return_value = True
        
        future_time = datetime.now().timestamp() + 3600
        timers = [
            {
                "id": "t1",
                "name": "Contract 1",
                "type": "Контракт",
                "is_running": True,
                "end_time": future_time
            }
        ]
        self.mock_data_manager.get_timers.return_value = timers
        
        tab = self.create_tab()
        
        # Act
        tab.process_expired_contracts()
        
        # Assert
        self.mock_data_manager.delete_timer.assert_not_called()

    def test_auto_delete_enabled_expired_other_type(self):
        # Arrange
        self.mock_data_manager.get_setting.return_value = True
        
        expired_time = datetime.now().timestamp() - 100
        timers = [
            {
                "id": "t1",
                "name": "Car 1",
                "type": "Аренда Транспорта",
                "is_running": True,
                "end_time": expired_time
            }
        ]
        self.mock_data_manager.get_timers.return_value = timers
        
        tab = self.create_tab()
        
        # Act
        tab.process_expired_contracts()
        
        # Assert
        self.mock_data_manager.delete_timer.assert_not_called()

if __name__ == "__main__":
    unittest.main()
