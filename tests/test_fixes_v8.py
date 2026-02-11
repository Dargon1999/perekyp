import unittest
import shutil
import os
import json
import uuid
from datetime import datetime
from data_manager import DataManager

class TestFixesV8(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_data_fixes_v8.json"
        self.dm = DataManager(self.test_file)
        # Create a clean profile
        self.dm.data = {"profiles": [], "active_profile_id": None}
        self.dm.create_profile("Test Profile", 1000.0)
        self.profile_id = self.dm.data["active_profile_id"]

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        # Cleanup backups if any
        backup_dir = os.path.join(os.path.dirname(self.test_file), "backups")
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)

    def test_item_stats_offset(self):
        # 1. Add a transaction
        self.dm.add_transaction("car_rental", 100, "Rent", item_name="Car A")
        
        # 2. Get stats
        stats = self.dm.get_item_stats("car_rental")
        self.assertIn("Car A", stats)
        self.assertEqual(stats["Car A"]["count"], 1) # 1 transaction
        
        # 3. Add offset
        # We want total to be 5. So offset = 4.
        self.dm.set_item_stat_offset("car_rental", "Car A", 4)
        
        # 4. Get stats again
        stats = self.dm.get_item_stats("car_rental")
        self.assertEqual(stats["Car A"]["count"], 5) # 1 calculated + 4 offset
        
        # 5. Add another transaction
        self.dm.add_transaction("car_rental", 200, "Rent 2", item_name="Car A")
        
        # 6. Get stats again
        stats = self.dm.get_item_stats("car_rental")
        self.assertEqual(stats["Car A"]["count"], 6) # 2 calculated + 4 offset

    def test_achievements(self):
        # 1. Get achievements (should be empty)
        achievements = self.dm.get_achievements()
        self.assertEqual(achievements, [])
        
        # 2. Unlock achievement
        self.dm.unlock_achievement("test_badge")
        
        # 3. Verify
        achievements = self.dm.get_achievements()
        self.assertIn("test_badge", achievements)
        
        # 4. Unlock same again (should not duplicate)
        self.dm.unlock_achievement("test_badge")
        achievements = self.dm.get_achievements()
        self.assertEqual(len(achievements), 1)

    def test_update_timer(self):
        # 1. Add timer
        self.dm.add_timer("Test Timer", "Work", 60)
        timers = self.dm.get_timers()
        self.assertEqual(len(timers), 1)
        t_id = timers[0]["id"]
        
        # 2. Update timer
        self.dm.update_timer(t_id, {"name": "Updated Timer", "type": "Rest"})
        
        # 3. Verify
        timers = self.dm.get_timers()
        self.assertEqual(timers[0]["name"], "Updated Timer")
        self.assertEqual(timers[0]["type"], "Rest")
        self.assertEqual(timers[0]["duration"], 60) # Should be unchanged

if __name__ == '__main__':
    unittest.main()
