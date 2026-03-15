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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = psutil.Process() if psutil else None
        self.startup_time = 0
        self.last_frame_time = time.time()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(2000) # Every 2 seconds
        
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
