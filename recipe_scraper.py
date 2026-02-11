import requests
from bs4 import BeautifulSoup
import json
import re
import os

URL = "https://gta5rp.info/wiki/kulinariya/"
OUTPUT_FILE = "recipes.json"

def clean_text(text):
    if not text: return ""
    # Remove hidden characters and normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_ingredients(ing_text):
    """
    Parses ingredient string like "Мясо + Овощи + Огонь" into a list.
    """
    if not ing_text: return []
    
    # Split by + or ,
    parts = re.split(r'[+,]', ing_text)
    cleaned = []
    for p in parts:
        c = clean_text(p)
        # Remove parentheses notes if any (e.g. "Рыба (любая)") -> "Рыба"
        # But sometimes notes are important. For GTA5RP, usually "Мясо + Нож"
        # We'll keep it simple for now, maybe strip " (инструмент)"
        c = re.sub(r'\(.*?\)', '', c).strip()
        if c and c.lower() != "ингредиенты":
            cleaned.append(c)
    return cleaned

def scrape_recipes():
    print(f"Fetching {URL}...")
    try:
        response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    recipes = []
    
    # Find all tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables.")
    
    for table in tables:
        rows = table.find_all('tr')
        if not rows: continue
        
        # Check headers
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
        header_str = "".join(headers)
        print(f"Table headers: {headers}")
        
        # Valid recipe tables usually have "Блюдо" or "Название" and "Ингредиенты" or "Рецепт"
        if not ("блюдо" in header_str or "название" in header_str) or not ("ингредиенты" in header_str or "рецепт" in header_str):
            continue
            
        print(f"Processing potential recipe table...")
        
        # Determine column indices
        name_idx = -1
        ing_idx = -1
        stats_idx = -1 # Satiety usually follows ingredients
        
        for i, h in enumerate(headers):
            if "блюдо" in h or "название" in h: name_idx = i
            elif "ингредиенты" in h or "рецепт" in h: ing_idx = i
            elif "сыт" in h: stats_idx = i
        
        # Fallback if headers are images or unclear
        if name_idx == -1: name_idx = 0
        if ing_idx == -1: ing_idx = 1
        
        for row in rows[1:]:
            cols = row.find_all('td')
            if not cols or len(cols) < 3: continue
            
            try:
                # Name
                name_col = cols[name_idx]
                name = clean_text(name_col.get_text())
                if not name: continue
                
                # Ingredients
                ing_col = cols[ing_idx]
                # Use separator to avoid merging text like "Milk<br>Sugar" -> "MilkSugar"
                ing_text = clean_text(ing_col.get_text(separator=" "))
                ingredients = parse_ingredients(ing_text)
                
                # Stats (Satiety, Mood, Power)
                # Usually they are in subsequent columns or in one column
                stats = {"satiety": 0, "mood": 0, "power": 0}
                
                # Try to extract numbers from subsequent columns
                # GTA5RP Wiki: Name | Ingredients | Satiety | Mood | Power | Difficulty/Time
                
                current_col = ing_idx + 1
                if current_col < len(cols):
                    stats["satiety"] = int(clean_text(cols[current_col].get_text()) or 0)
                if current_col + 1 < len(cols):
                    stats["mood"] = int(clean_text(cols[current_col+1].get_text()) or 0)
                if current_col + 2 < len(cols):
                    # Power can be negative
                    p_text = clean_text(cols[current_col+2].get_text())
                    try:
                        stats["power"] = int(p_text)
                    except:
                        stats["power"] = 0
                
                recipe_obj = {
                    "name": name,
                    "type": "final", # Default
                    "ingredients": ingredients,
                    "stats": stats
                }
                
                # Heuristic for intermediate ingredients
                # If it doesn't have stats or stats are 0/0/0, it might be intermediate?
                # Actually, GTA RP wiki lists everything together.
                # We can manually flag known intermediate items
                if name in ["Сыр", "Масло", "Тесто", "Сваренный рис", "Рыбный фарш", "Мясной фарш"]:
                    recipe_obj["type"] = "intermediate"
                
                recipes.append(recipe_obj)
                print(f"Parsed: {name}")
                
            except Exception as e:
                print(f"Skipping row: {e}")
                continue

    # Post-processing: Identify base ingredients
    # Collect all ingredients mentioned
    all_ingredients = set()
    for r in recipes:
        for i in r["ingredients"]:
            all_ingredients.add(i)
            
    # Create base ingredient entries if they don't exist as recipes
    existing_names = {r["name"] for r in recipes}
    tools = ["Нож", "Огонь", "Венчик", "Блендер", "Гриль", "Вода", "Кастрюля"]
    
    for ing in all_ingredients:
        if ing not in existing_names and ing not in tools:
            # Create base ingredient
            recipes.append({
                "name": ing,
                "type": "base",
                "ingredients": [],
                "stats": {}
            })
            
    # Save to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(recipes)} recipes to {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_recipes()
