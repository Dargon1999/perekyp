import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.tabs.fishing_tab import FishCard, RegionsFishWidget
from data_manager import DataManager

# Create application for testing UI components
app = QApplication(sys.argv)

class TestFishingGallery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_manager = DataManager()
        cls.theme = "dark"

    def test_fish_card_initialization(self):
        fish_data = {
            "id": "rainbow_trout",
            "name_ru": "Радужная форель",
            "name_lat": "Oncorhynchus mykiss",
            "description": "Test description",
            "habitat": "Озеро",
            "photo_url": "https://example.com/image.png"
        }
        card = FishCard(fish_data, self.data_manager, self.theme)
        
        self.assertEqual(card.name_ru.text(), "Радужная форель")
        self.assertEqual(card.name_lat.text(), "Oncorhynchus mykiss")
        self.assertEqual(card.desc_lbl.text(), "Test description")
        self.assertIn("Озеро", card.info_lbl.text())
        
    def test_fish_gallery_filtering(self):
        widget = RegionsFishWidget(self.data_manager)
        
        # Test search filter
        widget.search_input.setText("Радужная")
        widget.on_filter_changed()
        self.assertTrue(len(widget.filtered_fish) >= 1)
        self.assertEqual(widget.filtered_fish[0]["name_ru"], "Радужная форель")
        
        # Test habitat filter
        widget.search_input.setText("")
        widget.habitat_filter.setCurrentText("Океан")
        widget.on_filter_changed()
        for fish in widget.filtered_fish:
            habitat = fish.get("habitat", fish.get("region", ""))
            self.assertIn("Океан", habitat)

    def test_smart_image_loading_logic(self):
        # This is a unit test for logic, not a full network test
        fish_data = {
            "id": "test_fish",
            "photo_url": "https://raw.githubusercontent.com/Dargon1999/perekyp/main/fishing/rainbow_trout.png?raw=true"
        }
        card = FishCard(fish_data, self.data_manager, self.theme)
        self.assertTrue(card.img_widget.is_loading)

if __name__ == '__main__':
    unittest.main()
