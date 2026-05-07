
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.main_window import MainWindow
from data_manager import DataManager

# Mock AuthManager
class MockAuthManager:
    def __init__(self):
        self.current_creds = {"login": "test_user", "key": "test_key"}
        
    def check_license(self):
        return True, "Active"

class TestStartup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance if it doesn't exist
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication(sys.argv)

    def test_mainwindow_initialization(self):
        """Test that MainWindow initializes and loads tabs without hanging."""
        print("Initializing DataManager...")
        data_manager = DataManager() # Should load fast
        auth_manager = MockAuthManager()
        
        print("Initializing MainWindow...")
        window = MainWindow(auth_manager=auth_manager, data_manager=data_manager)
        window.show() # Make sure window is visible so child widgets can be visible
        
        # Check initial state
        self.assertFalse(window.tabs.isVisible())
        
        # Wait for post_init_setup (which runs after 50ms)
        # We process events for 2 seconds to allow timer to fire and setup to complete
        print("Waiting for post_init_setup...")
        
        # Helper to check visibility
        def check_loaded():
            if window.tabs.isVisible():
                print("Interface loaded successfully!")
                return True
            return False

        # Process events loop
        start_time = 0
        timeout = 5000 # 5 seconds timeout
        interval = 100
        
        import time
        while start_time < timeout:
            self.app.processEvents()
            if check_loaded():
                break
            time.sleep(0.1)
            start_time += interval
            
        self.assertTrue(window.tabs.isVisible(), "MainWindow tabs did not become visible (Hang detected?)")
        
        # Verify all tabs are present
        self.assertIsNotNone(window.car_rental_tab)
        self.assertIsNotNone(window.settings_tab)
        
        print("Test passed.")
        window.close()

if __name__ == '__main__':
    unittest.main()
