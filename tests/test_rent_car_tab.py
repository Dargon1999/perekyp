
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from gui.tabs.rent_car_tab import RentCarTab

class MockDataManager:
    def __init__(self):
        self.settings = {}
        self.timers = [
            {
                "id": "1",
                "name": "Test Car",
                "type": "Аренда Транспорта",
                "duration": 3600,
                "start_time": 0,
                "end_time": 3600,
                "is_running": True,
                "paused_remaining": None
            },
            {
                "id": "2",
                "name": "Test Contract",
                "type": "Контракт", # Should be filtered out
                "duration": 3600,
                "start_time": 0,
                "end_time": 3600,
                "is_running": True,
                "paused_remaining": None
            }
        ]
        
    def get_setting(self, key, default=None):
        return self.settings.get(key, default)
        
    def get_category_stats(self, category):
        return {"starting_amount": 0, "income": 0, "expenses": 0, "current_balance": 0, "pure_profit": 0}
        
    def get_transactions(self, category):
        return []
        
    def get_timers(self):
        return self.timers

class TestRentCarTab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
            
    def setUp(self):
        self.data_manager = MockDataManager()
        self.rent_car_tab = RentCarTab(self.data_manager)
        
    def test_active_rentals_display(self):
        # Should have found 1 timer
        self.assertEqual(self.rent_car_tab.rentals_cards_layout.count(), 1)
        
        # Verify content
        widget = self.rent_car_tab.rentals_cards_layout.itemAt(0).widget()
        # widget is TimerCard
        self.assertEqual(widget.timer_data["name"], "Test Car")
        
    def test_no_active_rentals(self):
        self.data_manager.timers = [] # Clear timers
        self.rent_car_tab.update_active_rentals()
        
        # Container should be hidden
        self.assertFalse(self.rent_car_tab.active_rentals_container.isVisible())
        self.assertEqual(self.rent_car_tab.rentals_cards_layout.count(), 0)

if __name__ == '__main__':
    unittest.main()
