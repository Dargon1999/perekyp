
import sys
import os
import unittest
from unittest.mock import MagicMock
import tempfile
import shutil
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock PyQt6
class MockWidget:
    def __init__(self, *args, **kwargs):
        self.clicked = MagicMock()
        self.valueChanged = MagicMock()
    def setLayout(self, layout): pass
    def layout(self): return MagicMock()
    def setStyleSheet(self, style): pass
    def setCursor(self, cursor): pass
    def setAlignment(self, align): pass
    def deleteLater(self): pass
    def addWidget(self, *args): pass
    def installEventFilter(self, filter): pass
    def setMouseTracking(self, enable): pass
    def setAttribute(self, attr, on): pass
    def update(self): pass
    def show(self): pass
    def hide(self): pass
    def setVisible(self, visible): pass
    def setEnabled(self, enabled): pass
    def setFixedSize(self, *args): pass
    def setMinimum(self, *args): pass
    def setMaximum(self, *args): pass
    def setValue(self, *args): pass
    def blockSignals(self, *args): pass
    def viewport(self): return MagicMock()
    def horizontalScrollBar(self): return MagicMock()
    def verticalScrollBar(self): return MagicMock()
    def setFrameShape(self, *args): pass
    def setWidgetResizable(self, *args): pass
    def setWidget(self, *args): pass
    def setAlignment(self, *args): pass
    def setReadOnly(self, *args): pass
    def setPlainText(self, *args): pass
    def setPixmap(self, *args): pass
    def scaled(self, *args): return MagicMock()
    def isNull(self): return False
    def size(self): return MagicMock()
    def text(self): return ""
    def setText(self, *args): pass
    def clear(self): pass
    def count(self): return 0
    def itemAt(self, i): return MagicMock()
    def widget(self): return MagicMock()
    def addTab(self, *args): pass
    def removeWidget(self, *args): pass
    def addLayout(self, *args): pass
    def addStretch(self, *args): pass
    def setContentsMargins(self, *args): pass
    def setSpacing(self, *args): pass
    def clicked(self): return MagicMock()
    def valueChanged(self): return MagicMock()
    def mousePressEvent(self, e): pass
    def setFocus(self): pass
    def setProperty(self, name, value): pass
    
    def setFixedWidth(self, *args): pass
    def setFixedHeight(self, *args): pass
    def setWordWrap(self, *args): pass
    def setFrameShadow(self, *args): pass
    def setRowStretch(self, *args): pass
    def setColumnStretch(self, *args): pass
    def rowCount(self): return 0
    def columnCount(self): return 0

    class Shape:
        NoFrame = 0

class MockEvent:
    def type(self): return MagicMock()
    def button(self): return MagicMock()
    def position(self): return MagicMock()
    def gesture(self, t): return MagicMock()

mock_qt_widgets = MagicMock()
mock_qt_widgets.QWidget = MockWidget
mock_qt_widgets.QLabel = MockWidget
mock_qt_widgets.QPushButton = MockWidget
mock_qt_widgets.QVBoxLayout = MockWidget
mock_qt_widgets.QHBoxLayout = MockWidget
mock_qt_widgets.QGridLayout = MockWidget
mock_qt_widgets.QScrollArea = MockWidget
mock_qt_widgets.QFrame = MockWidget
mock_qt_widgets.QSlider = MockWidget
mock_qt_widgets.QTextEdit = MockWidget
mock_qt_widgets.QTabWidget = MockWidget
mock_qt_widgets.QMessageBox = MagicMock()
mock_qt_widgets.QFileDialog = MagicMock()

sys.modules['PyQt6.QtWidgets'] = mock_qt_widgets
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

# Now import HelperTab
from gui.tabs.helper_tab import HelperTab

class TestTaroDownload(unittest.TestCase):
    def setUp(self):
        self.data_manager = MagicMock()
        self.main_window = MagicMock()
        self.data_manager.get_global_data.return_value = {}
        
        self.tab = HelperTab(self.data_manager, self.main_window)
        
    def test_download(self):
        # Trigger download
        print("Starting download test...")
        print(f"Type of tab: {type(self.tab)}")
        print(f"Type of ensure_tarot_images_loaded: {type(self.tab.ensure_tarot_images_loaded)}")
        self.tab.ensure_tarot_images_loaded()
        
        # Check temp dir
        temp_dir = os.path.join(tempfile.gettempdir(), "MoneyTracker_Taro")
        self.assertTrue(os.path.exists(temp_dir))
        
        # Check if files are downloaded
        # We check a few sample files
        files_to_check = ["Death.png", "The Fool.png", "Strenght.png"]
        for f in files_to_check:
            path = os.path.join(temp_dir, f)
            exists = os.path.exists(path)
            size = os.path.getsize(path) if exists else 0
            print(f"File {f}: Exists={exists}, Size={size}")
            
            # Note: If network fails, this might fail. 
            # We assume network is available as per environment.
            # If GitHub is blocked, this test will fail.
            if exists:
                self.assertGreater(size, 0)
        
        # Check dictionary
        self.assertIn("Death", self.tab.downloaded_tarot_images)
        self.assertIn("The Fool", self.tab.downloaded_tarot_images)
        
        print("Download test passed.")

    def tearDown(self):
        # Cleanup is handled by atexit in the code, but we can verify it manually or clean up our test artifacts
        # self.tab.cleanup_tarot_images() 
        pass

if __name__ == '__main__':
    unittest.main()
