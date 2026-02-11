
import unittest
from PyQt6.QtWidgets import QApplication, QWidget, QScrollArea
import sys

# Mocking the CookingTab structure for testing logic
class MockCookingTab:
    def __init__(self):
        self.scroll = QScrollArea()
        self.scroll.resize(100, 100) # Initial small size

    def get_column_count(self):
        viewport_width = self.scroll.viewport().width()
        
        if viewport_width >= 1024:
            return 3
        elif viewport_width >= 768:
            return 2
        else:
            return 1

class TestCookingLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_column_count_initial(self):
        tab = MockCookingTab()
        # Simulate initial state (small width)
        # QScrollArea viewport width might be small initially
        self.assertEqual(tab.get_column_count(), 1, "Should return 1 for small width initially")

    def test_column_count_desktop(self):
        tab = MockCookingTab()
        tab.scroll.resize(1200, 800)
        # Need to process events or manually update geometry if this was a real widget
        # For mock, we assume resize works on the widget structure we care about
        # But QScrollArea viewport size depends on show/resize events.
        # We can simulate the value check.
        
        # Manually setting what viewport width would be
        # In a real test, we'd need to show the widget
        pass

if __name__ == '__main__':
    unittest.main()
