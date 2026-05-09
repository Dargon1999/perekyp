import time
import logging
try:
    import psutil
except ImportError:
    psutil = None
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class PerformanceMonitor(QObject):
    """
    Monitors application performance metrics:
    - Startup Time (LCP equivalent)
    - UI Thread Responsiveness (FID equivalent)
    - Memory Usage
    - CPU Usage
    """
    metrics_updated = pyqtSignal(dict)
    hang_detected = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = psutil.Process() if psutil else None
        self.startup_time = 0
        self.last_heartbeat = time.time()
        self._hang_threshold = 5.0 # seconds
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(2000) # Every 2 seconds
        
        # UI Heartbeat to detect main thread hangs
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self._ui_heartbeat)
        self.heartbeat_timer.start(1000)

    def _ui_heartbeat(self):
        self.last_heartbeat = time.time()

    def check_responsiveness(self):
        """Called from a watchdog thread or similar to check if UI is alive."""
        if time.time() - self.last_heartbeat > self._hang_threshold:
            logging.critical("UI Hang Detected!")
            self.hang_detected.emit()
            return False
        return True
        
    def start_timer(self):
        self._start_mark = time.time()
        
    def end_startup(self):
        self.startup_time = time.time() - self._start_mark
        logging.info(f"Startup Performance (LCP): {self.startup_time:.2f}s")
        
    def update_metrics(self):
        if not self.process:
            return
            
        try:
            mem_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            metrics = {
                "memory_mb": mem_info.rss / (1024 * 1024),
                "cpu_percent": cpu_percent,
                "startup_time": self.startup_time,
                "threads": len(self.process.threads())
            }
            self.metrics_updated.emit(metrics)
        except Exception as e:
            logging.error(f"Performance monitor error: {e}")
