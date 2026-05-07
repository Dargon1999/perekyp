import unittest
import os
import json
import uuid
from datetime import datetime
from data_manager import DataManager

class TestClothesModule(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_clothes_module.json"
        self.dm = DataManager(self.test_file)
        self.dm.data = {"profiles": [], "active_profile_id": None}
        self.dm.create_profile("Test Profile", 1000.0)

    def tearDown(self):
        if os.path.exists(self.test_file):
            try:
                os.remove(self.test_file)
            except:
                pass

    def test_clothes_lifecycle(self):
        """Test adding, selling, and deleting clothes items."""
        # 1. Add item
        self.dm.add_clothes_item("Shirt", 50, "Test Note", None)
        inventory = self.dm.get_clothes_inventory()
        self.assertEqual(len(inventory), 1)
        item_id = inventory[0]["id"]
        
        # 2. Sell item
        success = self.dm.sell_clothes_item(item_id, 80)
        self.assertTrue(success)
        
        # Check moved to sold
        inventory = self.dm.get_clothes_inventory()
        self.assertEqual(len(inventory), 0)
        
        sold = self.dm.get_clothes_sold()
        self.assertEqual(len(sold), 1)
        self.assertEqual(sold[0]["sell_price"], 80.0)
        self.assertEqual(sold[0]["status"], "sold")
        self.assertIn("date_sold", sold[0]) # Ensure date_sold is present
        
        # 3. Delete sold item
        success = self.dm.delete_clothes_item(item_id, is_sold=True)
        self.assertTrue(success)
        sold = self.dm.get_clothes_sold()
        self.assertEqual(len(sold), 0)

    def test_delete_inventory_item(self):
        """Test deleting an item directly from inventory."""
        self.dm.add_clothes_item("Pants", 40, "Test Note", None)
        inventory = self.dm.get_clothes_inventory()
        item_id = inventory[0]["id"]
        
        success = self.dm.delete_clothes_item(item_id, is_sold=False)
        self.assertTrue(success)
        inventory = self.dm.get_clothes_inventory()
        self.assertEqual(len(inventory), 0)

    def test_migration_adds_date_sold(self):
        """Test that missing date_sold field is added by migration."""
        # Manually inject bad data
        profile = self.dm.get_active_profile()
        bad_item = {
            "id": str(uuid.uuid4()),
            "name": "Old Item",
            "sell_price": 100,
            "status": "sold",
            "date_added": "01.01.2020 12:00"
            # Missing date_sold
        }
        if "clothes" not in profile:
            profile["clothes"] = {}
        if "sold_history" not in profile["clothes"]:
            profile["clothes"]["sold_history"] = []
            
        profile["clothes"]["sold_history"].append(bad_item)
        self.dm.save_data()
        
        # Reload DataManager to trigger migration (simulating app restart)
        # Note: In our implementation, migration is called in __init__
        new_dm = DataManager(self.test_file)
        
        profile = new_dm.get_active_profile()
        item = profile["clothes"]["sold_history"][0]
        self.assertIn("date_sold", item)
        self.assertEqual(item["date_sold"], "01.01.2020 12:00") # Should fallback to date_added

    def test_sell_validation(self):
        """Test validation during sale."""
        self.dm.add_clothes_item("Hat", 20, "Note", None)
        inventory = self.dm.get_clothes_inventory()
        item_id = inventory[0]["id"]
        
        # Try to sell with negative price
        success = self.dm.sell_clothes_item(item_id, -10)
        self.assertFalse(success)
        
        # Try to sell with invalid price
        success = self.dm.sell_clothes_item(item_id, "abc")
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
