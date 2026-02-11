import unittest
import shutil
import os
import json
import uuid
from datetime import datetime
from data_manager import DataManager

class TestFixesV8_2(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_data_fixes_v8_2.json"
        self.dm = DataManager(self.test_file)
        self.dm.data = {"profiles": [], "active_profile_id": None}
        self.dm.create_profile("Test Profile", 1000.0)

    def tearDown(self):
        if os.path.exists(self.test_file):
            try:
                os.remove(self.test_file)
            except:
                pass

    def test_get_unique_item_names(self):
        # Add transactions with item names
        self.dm.add_transaction("car_rental", 100, "Rent 1", item_name="Car A")
        self.dm.add_transaction("car_rental", 200, "Rent 2", item_name="Car B")
        self.dm.add_transaction("car_rental", 300, "Rent 3", item_name="Car A") # Duplicate name
        
        # Test car_rental
        names = self.dm.get_unique_item_names("car_rental")
        self.assertEqual(names, ["Car A", "Car B"])
        
        # Test general transaction (legacy)
        self.dm.add_transaction("general", 50, "Food", item_name="Burger")
        names_gen = self.dm.get_unique_item_names("general")
        self.assertEqual(names_gen, ["Burger"])

    def test_add_clothes_item(self):
        success = self.dm.add_clothes_item("Shirt", 25.50, "Blue cotton", "path/to/img.png")
        self.assertTrue(success)
        
        inventory = self.dm.get_clothes_inventory()
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0]["name"], "Shirt")
        self.assertEqual(inventory[0]["buy_price"], 25.50)
        self.assertEqual(inventory[0]["note"], "Blue cotton")
        self.assertEqual(inventory[0]["photo_path"], "path/to/img.png")
        self.assertEqual(inventory[0]["status"], "in_stock")

if __name__ == '__main__':
    unittest.main()
