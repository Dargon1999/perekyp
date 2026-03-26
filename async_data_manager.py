from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication
import logging
import threading
from collections import deque

class Worker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(object)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(e)

class AsyncDataManager:
    def __init__(self, data_manager):
        self.dm = data_manager
        self._thread_pool = deque(maxlen=50)
        self._pool_lock = threading.Lock()
        self._cleanup_threshold = 30

    def _cleanup_finished_threads(self):
        with self._pool_lock:
            while self._thread_pool and not self._thread_pool[0].isRunning():
                self._thread_pool.popleft()
            if len(self._thread_pool) > self._cleanup_threshold:
                self._thread_pool.extend([t for t in self._thread_pool if not t.isFinished()])
                while len(self._thread_pool) > self._cleanup_threshold:
                    if self._thread_pool:
                        self._thread_pool.popleft()

    def _run_async(self, method_name, callback, *args, **kwargs):
        method_name_str = method_name
        try:
            logging.debug(f"Async: starting {method_name_str}")
            method = getattr(self.dm, method_name_str)
            
            thread = QThread()
            worker = Worker(method, *args, **kwargs)
            worker.moveToThread(thread)
            
            def on_finished(res):
                logging.debug(f"Async: finished {method_name_str}")
                callback(res)
                self._cleanup_finished_threads()

            worker.finished.connect(on_finished)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            
            def on_error(e):
                logging.error(f"Async error in {method_name_str}: {e}")
            worker.error.connect(on_error)
            worker.error.connect(thread.quit)
            worker.error.connect(worker.deleteLater)
            
            thread.started.connect(worker.run)
            thread.finished.connect(thread.deleteLater)
            
            if thread.isRunning():
                thread.start()
                with self._pool_lock:
                    self._thread_pool.append(thread)
            else:
                logging.warning(f"Thread for {method_name_str} failed to start")
        except AttributeError as e:
            logging.error(f"Method {method_name_str} not found in DataManager: {e}")
        except Exception as e:
            logging.error(f"Failed to start async task {method_name_str}: {e}")

    # --- Async Wrappers for Read Operations ---
    def get_total_capital_balance(self, callback):
        self._run_async("get_total_capital_balance", callback)

    def get_category_stats(self, callback, category):
        self._run_async("get_category_stats", callback, category)

    def get_transactions(self, callback, category):
        self._run_async("get_transactions", callback, category)

    # --- Async Wrappers for Write Operations (fire-and-forget or with callback) ---
    def save_data(self, callback=None):
        if callback is None: callback = lambda r: logging.info("Async save completed.")
        self._run_async("save_data", callback)

    def add_transaction(self, callback, category, amount, comment, **kwargs):
        self._run_async("add_transaction", callback, category, amount, comment, **kwargs)
