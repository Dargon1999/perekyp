from PyQt6.QtCore import QObject, pyqtSignal
import logging
import threading

class EventBus(QObject):
    """
    A simple event bus using PyQt6 signals for decoupled communication between modules.
    Thread-safe singleton implementation.
    """
    
    event_emitted = pyqtSignal(str, object)

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def emit(self, event_name, data=None):
        logging.debug(f"EventBus: Emitting event '{event_name}' with data: {data}")
        self.event_emitted.emit(event_name, data)

    def subscribe(self, event_name, callback):
        def wrapper(name, data):
            if name == event_name:
                callback(data)
        
        self.event_emitted.connect(wrapper)
        return wrapper

    def unsubscribe(self, wrapper):
        try:
            self.event_emitted.disconnect(wrapper)
        except TypeError:
            pass
