
import unittest
import json
import uuid
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

# Mock the DataManager to avoid GUI dependencies if necessary
# But we want to test the REAL logic in DataManager methods.
# So we will import DataManager and mock its file operations.

from data_manager import DataManager

class TestDealCounting(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = "test_data_temp"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
            
        # Patch DATA_DIR and DATA_FILE in data_manager module if possible, 
        # or just use the default since we can't easily inject it into __init__ 
        # based on previous error.
        # But wait, DataManager uses global DATA_FILE. 
        # We can try to monkeypatch or just rely on it not overwriting real data 
        # if we are careful. 
        # Actually, let's look at DataManager.__init__. It takes `filename`.
        
        self.data_file = os.path.join(self.test_dir, "data.json")
        self.dm = DataManager(filename=self.data_file)
        
        # Initialize with clean data
        self.dm.data = {
            "active_profile_id": "test_profile",
            "profiles": [
                {
                    "id": "test_profile",
                    "car_rental": {
                        "transactions": []
                    }
                }
            ]
        }
        # Mock save_data to avoid writing to disk or write to temp
        self.dm.save_data = lambda: None

    def test_count_increase_on_expense(self):
        # 1. Add Income
        self.dm.add_transaction(
            category="car_rental",
            amount=1000,
            comment="Income",
            date_str="01.01.2023",
            item_name="Toyota",
            ad_cost=0
        )
        
        stats = self.dm.get_item_stats("car_rental")
        self.assertEqual(stats["Toyota"]["count"], 1, "Count should be 1 after income")

        # 2. Add Expense
        self.dm.add_transaction(
            category="car_rental",
            amount=-200,
            comment="Expense",
            date_str="02.01.2023",
            item_name="Toyota",
            ad_cost=0
        )
        
        stats = self.dm.get_item_stats("car_rental")
        # THIS IS WHAT WE EXPECT TO FAIL if the user is right
        self.assertEqual(stats["Toyota"]["count"], 2, "Count should be 2 after expense")
        
    def test_count_with_ad_cost_only(self):
        # Case: Transaction with 0 amount but has ad_cost (simulated auto-expense merged?)
        # Actually, merged transaction has positive amount (income) and ad_cost.
        self.dm.add_transaction(
            category="car_rental",
            amount=1000,
            comment="Income+Ad",
            date_str="01.01.2023",
            item_name="Honda",
            ad_cost=100
        )
        
        stats = self.dm.get_item_stats("car_rental")
        self.assertEqual(stats["Honda"]["count"], 1, "Count should be 1 for merged transaction")
        self.assertEqual(stats["Honda"]["expenses"], 100, "Expenses should be 100")
        self.assertEqual(stats["Honda"]["profit"], 900, "Profit should be 900")

if __name__ == '__main__':
    unittest.main()
