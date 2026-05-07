import unittest
import os
import shutil
import tempfile
import platform
from unittest.mock import MagicMock, patch
from gui.widgets.utility_widgets import InternalTempWorker

class TestCrossPlatformCleanup(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.worker = InternalTempWorker()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_deep_clean_removes_files(self):
        # Create a dummy file
        f_path = os.path.join(self.test_dir, "test_file.tmp")
        with open(f_path, "w") as f:
            f.write("test content")
        
        initial_size = os.path.getsize(f_path)
        freed, errors, locked = self.worker._deep_clean(self.test_dir)
        
        self.assertEqual(freed, initial_size)
        self.assertEqual(errors, 0)
        self.assertFalse(os.path.exists(f_path))

    def test_deep_clean_handles_nonexistent_path(self):
        freed, errors, locked = self.worker._deep_clean("/non/existent/path/at/all")
        self.assertEqual(freed, 0)
        self.assertEqual(errors, 0)

    @patch('platform.system')
    def test_os_specific_targets(self, mock_system):
        # Test Windows targets
        mock_system.return_value = "Windows"
        with patch.dict(os.environ, {"LOCALAPPDATA": "C:\\AppData", "USERPROFILE": "C:\\User", "SystemRoot": "C:\\Windows"}):
            # We just verify run() starts and emits correctly
            self.worker.log = MagicMock()
            self.worker.progress = MagicMock()
            self.worker.finished_data = MagicMock()
            
            # Use a short-circuit mock for _deep_clean
            with patch.object(InternalTempWorker, "_deep_clean", return_value=(0,0,0)):
                with patch('ctypes.windll.shell32.SHEmptyRecycleBinW', return_value=0):
                    self.worker.run()
                    self.worker.log.emit.assert_any_call("🔍 Диагностика и запуск очистки (Windows)...")

        # Test macOS targets
        mock_system.return_value = "Darwin"
        with patch.object(InternalTempWorker, "_deep_clean", return_value=(0,0,0)):
            with patch('subprocess.run') as mock_run:
                self.worker.run()
                self.worker.log.emit.assert_any_call("🔍 Диагностика и запуск очистки (Darwin)...")

if __name__ == "__main__":
    unittest.main()
