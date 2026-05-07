import os
import json
from typing import Dict
from widgets.common import SettingsManager


class IngredientInventory:
    def __init__(self):
        self.settings = SettingsManager()
        self.section = "cooking_inventory"
        self._data: Dict[str, int] = self.settings.get(self.section, "items", {}) or {}

    def get(self, key: str) -> int:
        return int(self._data.get(key, 0))

    def add(self, key: str, amount: int = 1):
        self._data[key] = self.get(key) + int(amount)
        self._save()

    def use(self, key: str, amount: int = 1) -> bool:
        current = self.get(key)
        if current < amount:
            return False
        self._data[key] = current - amount
        self._save()
        return True

    def set(self, key: str, amount: int):
        self._data[key] = max(0, int(amount))
        self._save()

    def clear(self):
        self._data = {}
        self._save()

    def all(self) -> Dict[str, int]:
        return dict(self._data)

    def _save(self):
        self.settings.save_group(self.section, {"items": self._data})


def load_cooking_config(config_path: str = None) -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = config_path or os.path.join(base_dir, "config", "cooking.json")
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # fallback to minimal inline config
        return {
            "ingredients": [
                {"key": "frukti", "name": "Фрукты", "asset": "frukti.png"},
                {"key": "ovoshi", "name": "Овощи", "asset": "ovoshi.png"},
                {"key": "voda", "name": "Вода", "asset": "voda2.png"},
                {"key": "myaso", "name": "Мясо", "asset": "myaso.png"},
                {"key": "knife", "name": "Нож", "asset": "knife2.png"},
                {"key": "whisk", "name": "Венчик", "asset": "whisk2.png"},
                {"key": "fire", "name": "Огонь", "asset": "fire2.png"},
                {"key": "start", "name": "Старт готовки", "asset": "startCoocking.png"}
            ],
            "recipes": []
        }

