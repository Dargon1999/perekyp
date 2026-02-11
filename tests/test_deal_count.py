import unittest
import shutil
import os
import json
from datetime import datetime
from data_manager import DataManager

class TestDealCount(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_data_deal_count"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        self.db_file = os.path.join(self.test_dir, "data.json")
        self.dm = DataManager(filename=self.db_file)
        self.dm.create_profile("Test User", 0)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except PermissionError:
                pass

    def test_income_and_expense_count(self):
        """Verify that ONLY income transactions increment the deal count."""
        category = "car_rental"
        item_name = "Toyota Camry"
        
        # 1. Initial State
        stats = self.dm.get_item_stats(category)
        self.assertEqual(stats.get(item_name, {}).get("count", 0), 0)
        
        # 2. Add Income Transaction
        self.dm.add_transaction(
            category=category,
            amount=1000,
            comment="Rental Income",
            date_str=datetime.now().strftime("%d.%m.%Y"),
            item_name=item_name
        )
        
        stats = self.dm.get_item_stats(category)
        self.assertEqual(stats.get(item_name, {}).get("count", 0), 1, "Income should increment count to 1")
        
        # 3. Add Expense Transaction
        self.dm.add_transaction(
            category=category,
            amount=-200,
            comment="Repair Cost",
            date_str=datetime.now().strftime("%d.%m.%Y"),
            item_name=item_name
        )
        
        stats = self.dm.get_item_stats(category)
        self.assertEqual(stats.get(item_name, {}).get("count", 0), 1, "Expense should NOT increment count")

    def test_mixed_transactions_count(self):
        """Verify count with multiple mixed transactions."""
        category = "car_rental"
        item_name = "BMW X5"
        
        # Add 2 incomes and 3 expenses
        for i in range(2):
            self.dm.add_transaction(category, 100, f"Inc {i}", item_name=item_name)
        for i in range(3):
            self.dm.add_transaction(category, -50, f"Exp {i}", item_name=item_name)
            
        stats = self.dm.get_item_stats(category)
        self.assertEqual(stats.get(item_name, {}).get("count", 0), 2, "Total count should be 2 (only incomes)")

    def test_farm_bp_count(self):
        """Verify count logic for farm_bp category (previously missing)."""
        category = "farm_bp"
        item_name = "Battle Pass Season 1"
        
        self.dm.add_transaction(category, 1000, "Buy", item_name=item_name)
        
        stats = self.dm.get_item_stats(category)
        self.assertEqual(stats.get(item_name, {}).get("count", 0), 1)


if __name__ == "__main__":
    unittest.main()
