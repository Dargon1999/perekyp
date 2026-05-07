
import logging

import json
import os

class Ingredient:
    def __init__(self, name, type="base", recipe=None, stats=None, details=None):
        self.name = name
        self.type = type  # "base", "intermediate", "final", "tool"
        self.recipe = recipe  # List of component names needed to make this
        self.stats = stats or {}  # {satiety, mood, power, difficulty}
        self.details = details or {} # {description, steps, proportions, time, temperature, serving}

    def __repr__(self):
        return f"<Ingredient {self.name} ({self.type})>"

class RecipeManager:
    def __init__(self):
        self.ingredients = {}  # name -> Ingredient
        self.load_from_file("recipes.json")
        self.load_initial_data()
        self.load_detailed_descriptions() # New method to load rich text data

    def load_detailed_descriptions(self):
        """Loads extended descriptions, steps, and nuances for recipes."""
        
        # Borsch Details
        borsch_details = {
            "description": "Классический борщ — сытное и согревающее блюдо с богатым вкусом. Требует тщательной подготовки ингредиентов и соблюдения последовательности закладки продуктов для сохранения цвета и аромата.",
            "proportions": [
                "Мясо: 500г (говядина на кости)",
                "Вода: 2.5л",
                "Свекла: 2 шт. (средние)",
                "Морковь: 1 шт.",
                "Лук: 1 шт.",
                "Картофель: 3 шт.",
                "Капуста: 300г",
                "Томатная паста: 2 ст.л.",
                "Уксус/Лимонный сок: 1 ч.л. (для сохранения цвета)"
            ],
            "time": "1.5 - 2 часа",
            "temperature": "Варка на медленном огне (90-95°C)",
            "serving": "Подавать горячим со сметаной, свежей зеленью и пампушками с чесноком.",
            "steps": [
                "1. Приготовление бульона: Мясо залить холодной водой, довести до кипения, снять пену. Варить на медленном огне 1-1.5 часа.",
                "2. Подготовка овощей: Нарезать лук кубиками, морковь и свеклу — соломкой. Капусту нашинковать, картофель нарезать брусочками.",
                "3. Зажарка: Обжарить лук и морковь до золотистости. Отдельно тушить свеклу с томатной пастой и уксусом 10 минут.",
                "4. Сборка: В бульон добавить картофель, варить 10 минут. Добавить капусту, варить 5 минут. Ввести зажарку и тушеную свеклу.",
                "5. Финал: Добавить специи, лавровый лист, зелень. Дать настояться под крышкой 15-20 минут."
            ]
        }
        self.set_details("Борщ", borsch_details)
        
        # Risotto Details
        risotto_details = {
            "description": "Итальянское блюдо из риса, приготовленное на бульоне. Консистенция должна быть кремовой, 'текучей' (all'onda), а рис — аль денте.",
            "proportions": [
                "Рис Арборио/Карнароли: 300г",
                "Бульон (куриный/овощной): 1л",
                "Белое сухое вино: 100мл",
                "Лук шалот: 1 шт.",
                "Сливочное масло: 50г",
                "Пармезан: 50г",
                "Шафран (опционально)"
            ],
            "time": "20-25 минут",
            "temperature": "Средний огонь, постоянное помешивание",
            "serving": "Подавать немедленно на плоской тарелке, посыпав свежим пармезаном.",
            "steps": [
                "1. Подготовка: Разогреть бульон (он должен быть кипящим). Мелко нарезать лук.",
                "2. Обжарка (Tostatura): Обжарить лук на масле до прозрачности. Добавить рис и обжаривать 1-2 минуты, пока зерна не станут полупрозрачными по краям.",
                "3. Деглазирование: Влить вино и выпарить его полностью.",
                "4. Варка: Постепенно вливать горячий бульон по одному половнику, постоянно помешивая. Ждать, пока бульон впитается, прежде чем добавлять следующий.",
                "5. Мантекатура (Mantecatura): Снять с огня. Ввести холодное сливочное масло и тертый сыр. Энергично перемешать для кремовости."
            ]
        }
        self.set_details("Ризотто", risotto_details)

    def set_details(self, name, details):
        if name in self.ingredients:
            self.ingredients[name].details = details

    def load_from_file(self, filename):
        if not os.path.exists(filename):
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data:
                # Expecting item to be {name, ingredients: [], stats: {}, type}
                # or the format from scraper {name, ingredients: [], stats: {}}
                
                name = item.get('name')
                if not name: continue
                
                recipe = item.get('ingredients', [])
                stats = item.get('stats', {})
                itype = item.get('type', 'final') # Default to final if loaded from external
                
                # Heuristic for type if not provided
                if not item.get('type'):
                    if not recipe:
                        itype = "base"
                    else:
                        itype = "final"
                
                self.add_ingredient(name, itype, recipe, stats)
                
        except Exception as e:
            print(f"Error loading recipes from {filename}: {e}")

    def get_dish_type(self, name):
        # Mapping based on user images (Dish Name -> Skill Level)
        skill_mapping = {
            # Навык 0
            "Фруктовый салат": "Навык 0",
            "Овощной салат": "Навык 0",
            "Тесто": "Навык 0",
            "Бульон": "Навык 0",
            
            # Навык 1
            "Макароны": "Навык 1",
            
            # Навык 2
            "Овощной смузи": "Навык 2",
            "Фруктовый смузи": "Навык 2",
            "Фруктовый лёд": "Навык 2",
            "Масло": "Навык 2",
            "Рыбный фарш": "Навык 2",
            "Сухая рыбная котлета": "Навык 2",
            "Рыбная котлета": "Навык 2",
            "Мясной фарш": "Навык 2",
            "Мясная котлета": "Навык 2",
            "Сухая мясная котлета": "Навык 2",
            "Картофельное пюре": "Навык 2",
            "Вареный рис": "Навык 2",
            "Сваренный рис": "Навык 2",
            "Рыбная котлета с рисом": "Навык 2",
            "Котлета с рисом": "Навык 2",
            "Овощной ролл": "Навык 2",
            "Рыба с рисом": "Навык 2",
            "Рыба с овощами": "Навык 2",
            "Мясо с овощами": "Навык 2",
            "Яичница": "Навык 2",
            "Омлет": "Навык 2",
            "Мороженое": "Навык 2",
            "Хлеб": "Навык 2",
            "Сыр": "Навык 2",
            "Макароны с сыром": "Навык 2",
            "Стейк с рисом": "Навык 2",
            "Стейк с салатом": "Навык 2",
            "Стейк с макаронами": "Навык 2",
            
            # Навык 3
            "Мясная котлета с пюре": "Навык 3",
            "Рыбная котлета с пюре": "Навык 3",
            "Яичница с беконом": "Навык 3",
            "Овощной омлет": "Навык 3",
            "Компот": "Навык 3",
            "Оладьи": "Навык 3",
            "Молочный коктейль": "Навык 3",
            "Борщ": "Навык 3",
            "Пицца": "Навык 3",
            "Пельмени": "Навык 3",
            "Рагу": "Навык 3",
            "Тако с мясом": "Навык 3",
            "Тако с рыбой": "Навык 3",
            
            # Навык 4
            "Крем-брюле": "Навык 4",
            "Карамель": "Навык 4",
            "Чизкейк": "Навык 4",
            "Яблоко в карамели": "Навык 4",
            "Паста Болоньезе": "Навык 4",
            "Паста Карбонара": "Навык 4",
            "Поке": "Навык 4",
            "Сашими из лосося": "Навык 4",
            "Сашими из тунца": "Навык 4",
            
            # Навык 5
            "Суфле": "Навык 5",
            "Карамельный чизкейк": "Навык 5",
            "Фруктовый чизкейк": "Навык 5",
            "Стейк с фруктовым соусом": "Навык 5",
            "Стейк с фруктовым соусом и рисом": "Навык 5",
            "Стейк с фруктовым соусом и пюре": "Навык 5",
            "Рыба с фруктовым соусом": "Навык 5",
            "Рыба с фруктовым соусом и рисом": "Навык 5",
            "Рыба с фруктовым соусом и пюре": "Навык 5",
            "Лазанья": "Навык 5",
            "Мальма в сливочном соусе": "Навык 5",
            "Мясо по-французски": "Навык 5",
            "Оливье": "Навык 5"
        }
        
        return skill_mapping.get(name, "Другое")

    def get_ingredient(self, name):
        return self.ingredients.get(name)

    def get_all_recipes(self):
        return [ing for ing in self.ingredients.values() if ing.type in ["final", "intermediate"]]

    def add_ingredient(self, name, type, recipe=None, stats=None):
        # Heuristic to detect intermediate ingredients if type is not strictly set
        # If an ingredient appears in another recipe but has its own recipe, it's intermediate
        self.ingredients[name] = Ingredient(name, type, recipe, stats)
        
        # Auto-register unknown ingredients as base or tool
        if recipe:
            for item in recipe:
                item = item.strip()
                if item not in self.ingredients:
                    itype = "base"
                    # Simple tool detection
                    if item in ["Нож", "Огонь", "Венчик", "Блендер", "Гриль", "Вода"]:
                        itype = "tool"
                    self.add_ingredient(item, itype)

    def get_recipe_tree(self, name, visited=None):
        """
        Returns a hierarchical dictionary representing the full recipe tree.
        Format:
        {
            "name": "Dish Name",
            "type": "final",
            "ingredients": [
                { "name": "Sub-Ingredient", "type": "intermediate", "ingredients": [...] },
                { "name": "Base Ingredient", "type": "base", "ingredients": [] }
            ],
            "tools": ["Knife", "Fire"]
        }
        """
        if visited is None:
            visited = set()
        
        if name in visited:
            return {"name": name, "type": "cycle_detected", "ingredients": []}
        
        visited.add(name)
        
        ingredient = self.get_ingredient(name)
        if not ingredient:
            # It might be a tool or a base ingredient not explicitly defined
            # Check if it's a known tool
            tools = ["Нож", "Огонь", "Венчик", "Блендер", "Гриль", "Вода", "Кастрюля"]
            itype = "tool" if name in tools else "base"
            return {"name": name, "type": itype, "ingredients": []}
            
        tree = {
            "name": ingredient.name,
            "type": ingredient.type,
            "stats": ingredient.stats,
            "ingredients": []
        }
        
        if ingredient.recipe:
            for comp_name in ingredient.recipe:
                # Recursively resolve components
                comp_tree = self.get_recipe_tree(comp_name.strip(), visited.copy())
                tree["ingredients"].append(comp_tree)
                
        return tree

    def get_flat_ingredients(self, name):
        """Returns a list of all base ingredients needed."""
        tree = self.get_recipe_tree(name)
        base_ingredients = []
        
        def traverse(node):
            if not node["ingredients"] and node["type"] == "base":
                base_ingredients.append(node["name"])
            for child in node.get("ingredients", []):
                traverse(child)
                
        traverse(tree)
        return base_ingredients

    def load_initial_data(self):
        # Format: Name | Ingredients (separated by +) | Satiety | Mood | Power
        # Base ingredients will be inferred if not explicitly defined
        raw_data = """
Фруктовый салат | Фрукты + Нож | 15 | 40 | -3
Овощной салат | Овощи + Нож | 10 | 5 | 0
Рыбный фарш | Любая рыба (кроме лосося, тунца, фугу) + Нож | 0 | 0 | 0
Мясной фарш | Мясо + Нож | 0 | 0 | 0
Сашими из лосося | Лосось + Нож | 10 | 30 | -1
Сашими из тунца | Тунец + Нож | 10 | 30 | -1
Сашими из фугу | Фугу + Нож | 20 | 60 | 0
Жареная рыба | Любая рыба + Огонь | 20 | 10 | -5
Сухая рыбная котлета | Рыбный фарш + Огонь | 10 | 0 | -3
Сухая мясная котлета | Мясной фарш + Огонь | 10 | 0 | -3
Яичница | Яйцо + Огонь | 15 | 5 | -3
Хлеб | Тесто + Огонь | 10 | 0 | -2
Карамель | Сахар + Огонь | 5 | 10 | -5
Стейк | Мясо + Огонь | 25 | 20 | -8
Масло | Молоко + Венчик | 5 | 0 | -1
Сыр | Молоко + Венчик + Огонь | 15 | 5 | -1
Фруктовый смузи | Фрукты + Вода + Венчик | 20 | 50 | -7
Овощной смузи | Овощи + Вода + Венчик | 20 | 35 | 0
Молочный коктейль | Мороженое + Молоко + Венчик | 20 | 70 | -15
Ролл с лососем | Лосось + Сваренный рис + Нож | 25 | 20 | -3
Ролл с тунцом | Тунец + Сваренный рис + Нож | 25 | 20 | -3
Овощной ролл | Овощи + Сваренный рис + Нож | 20 | 10 | -2
Салат Капрезе | Сыр + Овощи + Нож | 15 | 10 | 0
Рыбная котлета | Рыбный фарш + Масло + Огонь | 25 | 10 | -10
Мясная котлета | Мясной фарш + Масло + Огонь | 25 | 10 | -10
Сваренный рис | Рисовая крупа + Вода + Огонь | 10 | 0 | -2
Рыба с рисом | Любая рыба + Сваренный рис + Огонь | 40 | 10 | -5
Рыба с овощами | Любая рыба + Овощи + Огонь | 35 | 15 | -3
Мясо с овощами | Мясо + Овощи + Огонь | 40 | 10 | -3
Овощной суп | Бульон + Овощи + Огонь | 25 | 10 | -1
Макароны с сыром | Макароны + Сыр + Огонь | 20 | 25 | -15
Бульон | Мясо + Вода + Огонь | 10 | 0 | -2
Стейк с рисом | Сваренный рис + Стейк + Огонь | 50 | 30 | -10
Омлет | Яйцо + Молоко + Венчик + Огонь | 20 | 10 | -4
Суфле | Яйцо + Сахар + Венчик + Огонь | 20 | 80 | -2
Сэндвич с сыром | Сыр + Хлеб + Нож + Огонь | 10 | 20 | -9
Макароны | Тесто + Вода + Нож + Огонь | 10 | 0 | -2
Фруктовый лёд | Фрукты + Лёд + Сахар + Венчик | 10 | 65 | -7
Тесто | Мука + Яйцо + Вода + Венчик | 0 | 0 | 0
Пельмени | Мясной фарш + Тесто + Вода + Огонь | 45 | 45 | -15
Яичница с беконом | Мясо + Яйцо + Масло + Огонь | 25 | 15 | -6
Компот | Фрукты + Сахар + Вода + Огонь | 5 | 50 | -7
Борщ | Мясо + Овощи + Бульон + Огонь | 50 | 40 | -13
Жареная на масле рыба с овощами | Любая рыба + Овощи + Масло + Огонь | 60 | 50 | -15
Жареное на масле мясо с овощами | Мясо + Овощи + Масло + Огонь | 60 | 50 | -15
Рагу | Мясо + Овощи + Вода + Огонь | 60 | 45 | -20
Крем-брюле | Молоко + Сахар + Яйцо + Огонь | 10 | 80 | -7
Стейк с фруктовым соусом | Мясо + Фрукты + Сахар + Огонь | 60 | 50 | -10
Рыба с фруктовым соусом | Любая рыба + Фрукты + Сахар + Огонь | 60 | 50 | -10
Ризотто | Рисовая крупа + Бульон + Сыр + Огонь | 40 | 20 | -20
Мальма в сливочном соусе | Мальма + Овощи + Молоко + Огонь | 75 | 75 | -13
Мясо по-французски | Мясо + Овощи + Сыр + Огонь | 60 | 40 | -15
Картофельное пюре | Овощи + Масло + Молоко + Венчик + Огонь | 10 | 10 | -5
Овощной омлет | Овощи + Яйцо + Молоко + Венчик + Огонь | 25 | 10 | -4
Чизкейк | Тесто + Сыр + Сахар + Венчик + Огонь | 30 | 60 | -15
Мороженое | Яйцо + Молоко + Сахар + Лёд + Венчик | 10 | 70 | -15
Пицца | Мясо + Тесто + Овощи + Сыр + Огонь | 30 | 50 | -25
Паста Болоньезе | Мясной фарш + Макароны + Овощи + Сыр + Огонь | 60 | 40 | -25
Паста Карбонара | Мясо + Макароны + Сыр + Яйцо + Огонь | 60 | 40 | -25
Рамен | Мясо + Макароны + Яйцо + Бульон + Огонь | 90 | 70 | -17
Оладьи | Яйцо + Молоко + Сахар + Мука + Венчик + Огонь | 20 | 20 | -10
Буррито | Сваренный рис + Мясной фарш + Хлеб + Овощи + Сыр + Огонь | 50 | 50 | -13
Оливье | Мясо + Яйцо + Овощи + Вода + Нож + Огонь | 60 | 50 | -25
Мясная котлета с пюре | Картофельное пюре + Мясная котлета | 50 | 50 | -20
Рыбная котлета с пюре | Картофельное пюре + Рыбная котлета | 50 | 50 | -20
Рыбная котлета с рисом | Сваренный рис + Рыбная котлета | 45 | 40 | -12
Мясная котлета с рисом | Сваренный рис + Мясная котлета | 45 | 40 | -12
Карамельный чизкейк | Чизкейк + Карамель | 35 | 85 | -25
Фруктовый чизкейк | Чизкейк + Фрукты | 35 | 70 | -20
Яблоко в карамели | Фрукты + Карамель | 20 | 55 | -7
Фруктовый салат с карамелью | Фруктовый салат + Карамель | 25 | 60 | -10
Карамельное мороженое | Мороженое + Карамель | 15 | 80 | -20
Карамельный молочный коктейль | Молочный коктейль + Карамель | 25 | 80 | -20
Макароны с мясной котлетой | Макароны + Мясная котлета | 45 | 40 | -15
Рыбная котлета с макаронами | Макароны + Рыбная котлета | 45 | 40 | -15
Стейк с салатом | Стейк + Овощной салат | 45 | 30 | -8
Стейк с макаронами | Стейк + Макароны | 30 | 25 | -8
Бургер | Мясная котлета + Овощи + Хлеб | 40 | 0 | -15
Стейк с фруктовым соусом и рисом | Стейк с фруктовым соусом + Сваренный рис | 80 | 60 | -13
Стейк с фруктовым соусом и пюре | Стейк с фруктовым соусом + Картофельное пюре | 80 | 80 | -15
Рыба с фруктовым соусом и рисом | Рыба с фруктовым соусом + Сваренный рис | 80 | 60 | -13
Рыба с фруктовым соусом и пюре | Рыба с фруктовым соусом + Картофельное пюре | 80 | 80 | -15
Поке | Сваренный рис + Лосось + Овощи + Сыр | 70 | 50 | -15
"""
        lines = raw_data.strip().split('\n')
        
        # First pass: Create ingredients for everything defined
        for line in lines:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 2: continue
            
            name = parts[0]
            recipe_str = parts[1]
            satiety = int(parts[2]) if len(parts) > 2 and parts[2] else 0
            mood = int(parts[3]) if len(parts) > 3 and parts[3] else 0
            power = int(parts[4]) if len(parts) > 4 and parts[4] else 0
            
            recipe_list = [r.strip() for r in recipe_str.split('+')]
            
            # Determine type
            ing_count = len(recipe_list)
            # Rough heuristic for type, can be refined
            if name in ["Мясной фарш", "Рыбный фарш", "Сваренный рис", "Тесто", "Бульон", "Масло", "Сыр", "Макароны", "Крем"]:
                i_type = "intermediate"
            else:
                i_type = "final"
                
            stats = {
                "satiety": satiety,
                "mood": mood,
                "power": power,
                "difficulty": "Простой" if ing_count <= 2 else "Средний" if ing_count <= 4 else "Сложный"
            }
            
            self.add_ingredient(name, i_type, recipe_list, stats)

        # Second pass: Ensure all base ingredients exist
        # If an ingredient in a recipe doesn't exist in self.ingredients, create it as base
        existing_names = list(self.ingredients.keys())
        for name in existing_names:
            item = self.ingredients[name]
            if item.recipe:
                for sub_ing in item.recipe:
                    if sub_ing not in self.ingredients:
                        # Create base ingredient
                        # Check if it's a tool
                        tools = ["Нож", "Огонь", "Венчик", "Сковорода", "Кастрюля", "Духовка", "Костёр", "Турка"]
                        i_type = "tool" if sub_ing in tools else "base"
                        self.add_ingredient(sub_ing, i_type)

    def get_hierarchy(self, name, level=0):
        """Returns a nested structure describing the recipe hierarchy."""
        item = self.get_ingredient(name)
        if not item:
            return {"name": name, "type": "unknown", "children": []}
            
        result = {
            "name": item.name,
            "type": item.type,
            "stats": item.stats,
            "children": []
        }
        
        if item.recipe:
            for sub_name in item.recipe:
                result["children"].append(self.get_hierarchy(sub_name, level + 1))
                
        return result

    def get_crafting_steps(self, name):
        """Returns a list of ingredients (Ingredient objects) that have recipes,
        sorted by dependency order (topological sort).
        The final item is the requested recipe itself.
        """
        visited = set()
        steps = []
        
        def visit(n):
            if n in visited:
                return
            
            item = self.get_ingredient(n)
            if not item:
                return
                
            # Visit children first
            if item.recipe:
                for sub_name in item.recipe:
                    visit(sub_name)
            
            # Add self if it has a recipe (is craftable)
            if item.recipe:
                steps.append(item)
                
            visited.add(n)
            
        visit(name)
        return steps
