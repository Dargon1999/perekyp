
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCloseEvent

# Mock DataManager and others to avoid loading real data/UI
sys.modules['data_manager'] = MagicMock()
sys.modules['gui.styles'] = MagicMock()
sys.modules['gui.custom_dialogs'] = MagicMock()
sys.modules['gui.tabs.generic_tab'] = MagicMock()
# We need real MainWindow import, but we mocked dependencies
# However, MainWindow imports a lot. It might be better to just mock the parts we need.
# But MainWindow is what we are testing.

# Let's try to import MainWindow after mocking
from gui.main_window import MainWindow

class TestCloseBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Mock dependencies for MainWindow
        self.mock_auth = MagicMock()
        # Fix license check unpacking error
        self.mock_auth.check_license_status.return_value = (True, "Active", "Never")
        
        self.mock_data = MagicMock()
        self.mock_data.get_setting.return_value = "dark" # For apply_styles
        
        # Patch UpdateManager to verify stop() is called
        self.patcher_um = patch('gui.main_window.UpdateManager')
        self.MockUpdateManager = self.patcher_um.start()
        
        # Patch QSystemTrayIcon to avoid creating real system resources
        self.patcher_tray = patch('gui.main_window.QSystemTrayIcon')
        self.MockTray = self.patcher_tray.start()

    def tearDown(self):
        self.patcher_um.stop()
        self.patcher_tray.stop()

    def test_close_event_cleanup(self):
        """Test that closeEvent triggers cleanup and quit."""
        window = MainWindow(auth_manager=self.mock_auth, data_manager=self.mock_data)
        
        # Mock QApplication.quit to verify it's called
        with patch('PyQt6.QtWidgets.QApplication.quit') as mock_quit:
            # Create a close event
            event = QCloseEvent()
            
            # Call closeEvent directly
            window.closeEvent(event)
            
            # Assertions
            
            # 1. Check UpdateManager stopped
            window.update_manager.stop.assert_called_once()
            
            # 2. Check Tray Icon hidden/removed
            window.tray_icon.hide.assert_called_once()
            window.tray_icon.deleteLater.assert_called_once()
            
            # 3. Check Event Accepted
            self.assertTrue(event.isAccepted())
            
            # 4. Check QApplication.quit called
            mock_quit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
