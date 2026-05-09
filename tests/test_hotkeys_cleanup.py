import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cleanup import clean_temp, empty_recycle_bin, safe_remove
from gui.widgets.utility_widgets import InternalMemWorker, InternalTempWorker

class TestCleanupLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_safe_remove_file(self):
        # Create dummy file
        f_path = os.path.join(self.test_dir, "test.tmp")
        with open(f_path, "w") as f:
            f.write("test data")
        
        self.assertTrue(os.path.exists(f_path))
        freed, errors, locked = safe_remove(f_path)
        self.assertEqual(freed, 9) # "test data" length
        self.assertEqual(errors, 0)
        self.assertFalse(os.path.exists(f_path))

    def test_safe_remove_locked_file_simulation(self):
        # Simulate PermissionError
        f_path = os.path.join(self.test_dir, "locked.tmp")
        with open(f_path, "w") as f:
            f.write("locked")
            
        with patch("os.remove", side_effect=PermissionError):
            # On Windows it will try MoveFileExW
            with patch("ctypes.WinDLL", return_value=MagicMock()) as mock_kernel:
                mock_kernel().MoveFileExW.return_value = 1 # Success for MoveFileEx
                freed, errors, locked = safe_remove(f_path)
                if sys.platform == "win32":
                    self.assertEqual(locked, 1)
                else:
                    self.assertEqual(errors, 1)

    @patch("utils.cleanup.safe_remove")
    def test_clean_temp_calls(self, mock_remove):
        mock_remove.return_value = (100, 0, 0)
        freed, errors, locked = clean_temp()
        self.assertEqual(freed, 300) # 3 targets in clean_temp
        self.assertTrue(mock_remove.called)

class TestWorkers(unittest.TestCase):
    @patch("psutil.process_iter")
    def test_mem_worker_logic(self, mock_iter):
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_iter.return_value = [mock_proc]
        
        worker = InternalMemWorker()
        worker.log = MagicMock()
        worker.progress = MagicMock()
        worker.finished_data = MagicMock()
        
        # Mock WinAPI calls
        with patch("ctypes.WinDLL"):
            worker.run()
            
        self.assertTrue(worker.log.emit.called)
        self.assertTrue(worker.finished_data.emit.called)
        
    def test_temp_worker_logic(self):
        worker = InternalTempWorker()
        worker.log = MagicMock()
        worker.progress = MagicMock()
        worker.finished_data = MagicMock()
        
        with patch("utils.cleanup.clean_temp", return_value=(1024, 0, 0)):
            with patch("utils.cleanup.empty_recycle_bin", return_value=True):
                worker.run()
                
        self.assertTrue(worker.log.emit.called)
        data = worker.finished_data.emit.call_args[0][0]
        self.assertEqual(data["status"], "success")

if __name__ == "__main__":
    unittest.main()
