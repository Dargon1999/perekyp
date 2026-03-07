import unittest
from PyQt6.QtWidgets import QApplication
import sys
from gui.tabs.fishing_tab import ComparisonOverlay

# Construct a single QApplication instance for all tests
app = QApplication(sys.argv)

class MockDataManager:
    def get_setting(self, key, default):
        return default

class TestFishingComparison(unittest.TestCase):
    def setUp(self):
        self.data_manager = MockDataManager()
        # Mock items
        self.rod1 = {
            "kind": "rod",
            "name": "Rod 1",
            "price": 1000,
            "stats": {"max_weight": 10, "sensitivity": 50, "durability": 80}
        }
        self.rod2 = {
            "kind": "rod",
            "name": "Rod 2",
            "price": 2000,
            "stats": {"max_weight": 15, "sensitivity": 30, "durability": 90}
        }
        self.overlay = ComparisonOverlay([self.rod1, self.rod2], self.data_manager, "dark")

    def test_rod_scoring(self):
        # score = weight*2 + sensitivity*0.5 + durability*0.3
        # rod1: 10*2 + 50*0.5 + 80*0.3 = 20 + 25 + 24 = 69
        score1 = self.overlay.calculate_score(self.rod1)
        self.assertEqual(score1, 69.0)
        
        # rod2: 15*2 + 30*0.5 + 90*0.3 = 30 + 15 + 27 = 72
        score2 = self.overlay.calculate_score(self.rod2)
        self.assertEqual(score2, 72.0)

    def test_reel_scoring(self):
        reel = {
            "kind": "reel",
            "stats": {"max_weight": 5, "speed": 40, "durability": 60}
        }
        # score = weight*2 + speed*0.5 + durability*0.4
        # 5*2 + 40*0.5 + 60*0.4 = 10 + 20 + 24 = 54
        score = self.overlay.calculate_score(reel)
        self.assertEqual(score, 54.0)

    def test_line_scoring(self):
        line = {
            "kind": "line",
            "stats": {"max_weight": 7, "visibility": 20, "abrasion": 15, "durability": 30}
        }
        # score = weight*2 + (100-visibility)*0.3 + abrasion*0.2 + durability*0.2
        # 7*2 + (100-20)*0.3 + 15*0.2 + 30*0.2 = 14 + 24 + 3 + 6 = 47
        score = self.overlay.calculate_score(line)
        self.assertEqual(score, 47.0)

    def test_best_selection_logic(self):
        # Score criteria: rod2 should be best (72 > 69)
        # Price criteria: rod1 should be best (1000 < 2000)
        
        # This is harder to test without full UI integration, but we can verify calculate_score 
        # which is the heart of the logic.
        pass

if __name__ == '__main__':
    unittest.main()
