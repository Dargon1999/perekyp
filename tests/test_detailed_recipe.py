
import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.recipe_manager import RecipeManager

class TestDetailedRecipe(unittest.TestCase):
    def setUp(self):
        self.manager = RecipeManager()

    def test_borsch_details(self):
        borsch = self.manager.get_ingredient("Борщ")
        self.assertIsNotNone(borsch)
        self.assertTrue(hasattr(borsch, 'details'))
        self.assertIn('description', borsch.details)
        self.assertIn('steps', borsch.details)
        self.assertIn('proportions', borsch.details)
        self.assertIn('time', borsch.details)
        
        # Verify content
        self.assertIn("Классический борщ", borsch.details['description'])
        self.assertTrue(len(borsch.details['steps']) > 0)
        self.assertEqual(borsch.details['time'], "1.5 - 2 часа")

    def test_risotto_details(self):
        risotto = self.manager.get_ingredient("Ризотто")
        self.assertIsNotNone(risotto)
        self.assertIn('Мантекатура', str(risotto.details['steps']))

    def test_simple_recipe_no_details(self):
        # "Яичница" should not have manual details yet (unless I added them implicitly via some other means, but I didn't)
        egg = self.manager.get_ingredient("Яичница")
        self.assertIsNotNone(egg)
        # It has 'details' attr (default empty dict) but should be empty
        self.assertEqual(egg.details, {})

if __name__ == '__main__':
    unittest.main()
