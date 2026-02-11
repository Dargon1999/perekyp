import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.recipe_manager import RecipeManager

class TestRecipeHierarchy(unittest.TestCase):
    def setUp(self):
        self.manager = RecipeManager()
        
    def test_burrito_hierarchy(self):
        # Burrito = Cooked Rice + Meat Mince + Bread + Veggies + Cheese + Fire
        # Cheese = Milk + Whisk + Fire
        # Cooked Rice = Rice + Water + Fire
        
        tree = self.manager.get_recipe_tree("Буррито")
        
        self.assertEqual(tree["name"], "Буррито")
        self.assertEqual(tree["type"], "final")
        
        # Check direct ingredients
        ing_names = [i["name"] for i in tree["ingredients"]]
        self.assertIn("Сваренный рис", ing_names)
        self.assertIn("Мясной фарш", ing_names)
        self.assertIn("Хлеб", ing_names)
        self.assertIn("Сыр", ing_names)
        
        # Check sub-recipe: Cheese
        cheese_node = next(i for i in tree["ingredients"] if i["name"] == "Сыр")
        cheese_ings = [x["name"] for x in cheese_node["ingredients"]]
        self.assertIn("Молоко", cheese_ings)
        self.assertIn("Венчик", cheese_ings)
        self.assertIn("Огонь", cheese_ings)
        
    def test_caprese_hierarchy(self):
        # Caprese = Cheese + Veggies + Knife
        tree = self.manager.get_recipe_tree("Салат Капрезе")
        
        self.assertEqual(tree["name"], "Салат Капрезе")
        
        ing_names = [i["name"] for i in tree["ingredients"]]
        self.assertIn("Сыр", ing_names)
        self.assertIn("Овощи", ing_names)
        
        # Check sub-recipe: Cheese (should be same as above)
        cheese_node = next(i for i in tree["ingredients"] if i["name"] == "Сыр")
        self.assertEqual(cheese_node["type"], "intermediate")

if __name__ == '__main__':
    unittest.main()
