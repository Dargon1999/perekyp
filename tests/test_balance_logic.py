import unittest
from data_manager import DataManager
from utils import Money
import os
import json
import shutil

class TestBalanceLogic(unittest.TestCase):
    def setUp(self):
        # Use a temporary file for testing
        self.test_db = "test_data.json"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.dm = DataManager(self.test_db)
        # Create a test profile
        self.dm.create_profile("Test User", 8000000) # 8M starting capital

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists("backups"):
            shutil.rmtree("backups")

    def test_money_precision(self):
        m1 = Money.from_major(100.05)
        m2 = Money.from_major(200.10)
        m3 = m1 + m2
        self.assertEqual(m3.to_major(), 300.15)
        self.assertEqual(m3.amount, 30015)

    def test_car_purchase_impact(self):
        # 1. Start with 8M
        balance = self.dm.get_total_capital_balance()
        self.assertEqual(balance["liquid_cash"], 8000000.0)
        self.assertEqual(balance["net_worth"], 8000000.0)

        # 2. Buy a car for 4M
        self.dm.add_trade_item("cars_trade", "Bravado Banshee", 4000000.0, "Fresh import", None)
        
        balance = self.dm.get_total_capital_balance()
        # Cash should be 4M
        self.assertEqual(balance["liquid_cash"], 4000000.0)
        # Net worth should still be 8M (4M cash + 4M car)
        self.assertEqual(balance["net_worth"], 8000000.0)

    def test_car_sale_impact(self):
        # 1. Buy car for 4M
        self.dm.add_trade_item("cars_trade", "Bravado Banshee", 4000000.0, "Fresh import", None)
        item = self.dm.get_trade_inventory("cars_trade")[0]
        
        # 2. Sell car for 5M (1M profit)
        self.dm.sell_trade_item("cars_trade", item["id"], 5000000.0)
        
        balance = self.dm.get_total_capital_balance()
        # Cash should be 8M (starting) - 4M (buy) + 5M (sell) = 9M
        self.assertEqual(balance["liquid_cash"], 9000000.0)
        # Net worth should also be 9M (no inventory left)
        self.assertEqual(balance["net_worth"], 9000000.0)

    def test_fishing_profit(self):
        # 1. Fishing expense
        self.dm.add_transaction("fishing", -500.0, "Tackle", item_name="Rod I")
        # 2. Fishing income
        self.dm.add_transaction("fishing", 2000.0, "Sold Pike")
        
        balance = self.dm.get_total_capital_balance()
        # Profit = 1500
        # Total Cash = 8M + 1500 = 8001500
        self.assertEqual(balance["liquid_cash"], 8001500.0)

    def test_integration_chain(self):
        # Chain of operations
        self.dm.add_trade_item("cars_trade", "Car A", 1000.0, "", None) # Buy 1000
        self.dm.add_transaction("fishing", -200.0, "Bait") # Expense 200
        self.dm.add_transaction("mining", 500.0, "Gold") # Income 500
        
        item_a = self.dm.get_trade_inventory("cars_trade")[0]
        self.dm.sell_trade_item("cars_trade", item_a["id"], 1500.0) # Sell 1500 (Profit 500)
        
        balance = self.dm.get_total_capital_balance()
        # Start: 8,000,000
        # Car Profit: +500
        # Fishing: -200
        # Mining: +500
        # Total: 8,000,800
        self.assertEqual(balance["liquid_cash"], 8000800.0)

    def test_no_category_starting_amount(self):
        # Ensure category stats don't have starting_amount anymore
        stats = self.dm.get_category_stats("fishing")
        self.assertNotIn("starting_amount", stats)
        
    def test_global_balance_reflects_all_tabs(self):
        # 1. Start with 8M
        # 2. Add 1000 in fishing
        self.dm.add_transaction("fishing", 1000.0, "Sold fish")
        # 3. Add 500 in mining
        self.dm.add_transaction("mining", 500.0, "Mined gold")
        # 4. Subtract 200 in car rental
        self.dm.add_transaction("car_rental", -200.0, "Repairs")
        
        balance = self.dm.get_total_capital_balance()
        # 8,000,000 + 1000 + 500 - 200 = 8,001,300
        self.assertEqual(balance["liquid_cash"], 8001300.0)
        
    def test_group_fishing_transaction(self):
        # Simulate separate records logic from dialog
        items = ["удочка", "катушка"]
        total_amount = -1000.0
        split_amount = total_amount / len(items)
        
        for item in items:
            self.dm.add_transaction("fishing", split_amount, "Group buy", date_str="06.03.2026", item_name=item)
            
        txs = self.dm.get_transactions("fishing")
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0]["amount"], -500.0)
        self.assertEqual(txs[1]["amount"], -500.0)
        
        balance = self.dm.get_total_capital_balance()
        self.assertEqual(balance["liquid_cash"], 7999000.0)


if __name__ == "__main__":
    unittest.main()
