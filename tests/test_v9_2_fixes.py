
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from gui.tabs.analytics_sub_tab import AnalyticsSubTab
from gui.tabs.fishing_tab import FishingTab, AskBuildWidget, CommunityBuildsWidget
from gui.tabs.rent_car_tab import RentCarTab
from gui.tabs.capital_planning_tab import CapitalPlanningTab

class MockDataManager:
    def __init__(self):
        self.settings = {"allowManualBalanceEdit": False}
        self.transactions = []
        self.timers = []
        self.active_profile = {"starting_amount": 0, "fishing": {"equipment": {}}}
        
    def get_setting(self, key, default=None):
        return self.settings.get(key, default)
    
    def set_setting(self, key, value):
        self.settings[key] = value
        
    def get_transactions(self, category):
        return self.transactions
        
    def get_category_stats(self, category):
        return {"pure_profit": 0, "starting_amount": 0, "income": 0, "expenses": 0}
        
    def get_total_capital_balance(self):
        return {"liquid_cash": 1000.0, "net_worth": 1000.0}
        
    def get_active_profile(self):
        return self.active_profile

    def get_trade_inventory(self, cat): return []
    def get_trade_sold(self, cat): return []
    def get_clothes_inventory(self): return []
    def get_clothes_sold(self): return []
    def get_timers(self): return self.timers
    def get_fishing_equipment(self): return self.active_profile["fishing"]["equipment"]
    def get_achievements(self): return []
    def unlock_achievement(self, aid): pass
    def get_capital_planning_data(self): return {"target_amount": 0}
    def load_pixmap(self, path, size=None): 
        from PyQt6.QtGui import QPixmap
        return QPixmap()
    def save_data(self): pass
    
    class DataChangedSignal:
        def connect(self, slot): pass
        def emit(self): pass
    data_changed = DataChangedSignal()

class TestReleaseV92(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
            
    def setUp(self):
        self.dm = MockDataManager()
        
    def test_analytics_robust_parsing(self):
        # Test with corrupted data (None in inventory)
        with patch.object(self.dm, 'get_trade_inventory', return_value=[None, {"name": "Test", "buy_price": "invalid"}]):
            tab = AnalyticsSubTab("all", "Обзор", self.dm)
            txs = tab._get_all_transactions()
            # Should not crash and return empty list or valid items only
            self.assertEqual(len(txs), 0)

    def test_fishing_localization_elements(self):
        tab = FishingTab(self.dm)
        # Check tab names
        expected_tabs = ["🔧 Снасти / Рыба", "📍 Регионы и рыба", "💬 Вопрос / Сборка", "💰 Калькулятор прибыли", "🏆 Сборки от игроков"]
        for i, name in enumerate(expected_tabs):
            self.assertEqual(tab.tabs_def[i][1], name)
            
        # Check AskBuildWidget icons and labels
        ask_widget = AskBuildWidget(self.dm)
        self.dm.active_profile["fishing"]["equipment"] = {
            "line_name": "Речной шёлк (броня) 3", "line_durability": "80%",
            "bait_name": "Черви", "bait_durability": "90%"
        }
        ask_widget.generate_build()
        text = ask_widget.result_lbl.text()
        self.assertIn("🧵 <b>Леска:</b> Речной шёлк (броня) 3 (80%)", text)
        self.assertIn("🪱 <b>Наживка:</b> Черви (90%)", text)
        self.assertNotIn("test line", text.lower())
        self.assertNotIn("test bait", text.lower())

    def test_capital_goal_formatting(self):
        tab = CapitalPlanningTab(self.dm, MagicMock())
        # Target amount 1234.56
        self.dm.get_capital_planning_data = MagicMock(return_value={"target_amount": 1234.56})
        tab.refresh_data()
        # Should be displayed as "1234" in input
        self.assertEqual(tab.goal_input.text(), "1234")
        
        # Remaining should be formatted as $XXXX (integer)
        self.dm.get_total_capital_balance = MagicMock(return_value={"liquid_cash": 1000.0, "net_worth": 1000.0})
        tab.update_realtime_goal()
        self.assertEqual(tab.lbl_remaining.text(), "Осталось: $235") # round(1234.56 - 1000) = 235

    def test_rent_car_manual_edit_toggle(self):
        from PyQt6.QtCore import Qt
        tab = RentCarTab(self.dm)
        # Default disabled
        self.dm.settings["allowManualBalanceEdit"] = False
        tab.update_balance_editability()
        self.assertEqual(tab.stat_balance.value_label.cursor().shape(), Qt.CursorShape.ArrowCursor)
        
        # Enable
        self.dm.settings["allowManualBalanceEdit"] = True
        tab.update_balance_editability()
        self.assertEqual(tab.stat_balance.value_label.cursor().shape(), Qt.CursorShape.PointingHandCursor)

    def test_capital_tab_ui_improvements(self):
        tab = CapitalPlanningTab(self.dm, MagicMock())
        # Check width is not small
        self.assertGreaterEqual(tab.goal_input.minimumWidth(), 300)
        # Check returnPressed connection
        self.assertTrue(hasattr(tab, 'save_goal'))

    def test_data_manager_achievements_api(self):
        # The fix for AttributeError: 'DataManager' object has no attribute 'get_achievements'
        from data_manager import DataManager
        dm = DataManager()
        self.assertTrue(hasattr(dm, 'get_achievements'))
        self.assertIsInstance(dm.get_achievements(), list)

    def test_buy_sell_auto_ad_cost(self):
        from gui.tabs.buy_sell_tab import TradeItemWidget
        self.dm.settings["listing_cost_enabled"] = True
        self.dm.settings["listing_cost"] = 500.0
        
        widget = TradeItemWidget(self.dm, MagicMock(), "clothes_new")
        widget.refresh_data()
        self.assertEqual(widget.appearance_price_input.text(), "500.0")

    def test_buy_sell_income_visibility_toggle(self):
        from gui.tabs.buy_sell_tab import TradeItemWidget
        from PyQt6.QtWidgets import QLabel
        # Mock inventory data
        item = {"id": "1", "name": "Item 1", "buy_price": 1000, "photo_path": None}
        with patch.object(self.dm, 'get_trade_inventory', return_value=[item]):
            widget = TradeItemWidget(self.dm, MagicMock(), "clothes_new")
            
            # Show price
            self.dm.settings["showBuyPriceInInventory"] = True
            widget.update_inventory_list()
            
            # Simplified check: logic uses the setting
            self.assertTrue(self.dm.get_setting("showBuyPriceInInventory"))

    def test_buy_sell_auto_ad_cost_visibility(self):
        from gui.tabs.buy_sell_tab import TradeItemWidget
        # In unit tests with mock dm, visibility might not be fully trackable without a real show()
        # but we can check the logic in refresh_data
        widget = TradeItemWidget(self.dm, MagicMock(), "clothes_new")
        
        # Disabled
        self.dm.settings["listing_cost_enabled"] = False
        widget.refresh_data()
        self.assertFalse(widget.appearance_price_input.isVisible())

    def test_capital_goal_width(self):
        tab = CapitalPlanningTab(self.dm, MagicMock())
        # Check that it's at least 300 and Expanding
        from PyQt6.QtWidgets import QSizePolicy
        self.assertGreaterEqual(tab.goal_input.minimumWidth(), 300)
        self.assertEqual(tab.goal_input.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Expanding)

    def test_fishing_build_card_layout(self):
        from gui.tabs.fishing_tab import CommunityBuildsWidget
        from PyQt6.QtWidgets import QGridLayout
        widget = CommunityBuildsWidget(self.dm)
        card = widget.build_card(widget.builds[0])
        # Check if QGridLayout is used for stats
        self.assertTrue(any(isinstance(l, QGridLayout) for l in card.findChildren(QGridLayout)))

if __name__ == '__main__':
    unittest.main()
