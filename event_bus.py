from PyQt6.QtCore import QObject, pyqtSignal
import logging

class EventBus(QObject):
    """
    A simple event bus using PyQt6 signals for decoupled communication between modules.
    """
    # Define generic signals that modules can emit and subscribe to.
    # We can use a single signal with a name and data, or specific signals.
    # For flexibility, a generic signal is often easier.
    
    event_emitted = pyqtSignal(str, object) # (event_name, data)

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit(self, event_name, data=None):
        """Emits an event with the given name and optional data."""
        logging.info(f"EventBus: Emitting event '{event_name}' with data: {data}")
        self.event_emitted.emit(event_name, data)

    def subscribe(self, event_name, callback):
        """
        Subscribes a callback to a specific event name.
        Note: This is a helper method. In PyQt, you usually connect directly to the signal
        and then filter by event_name in the slot.
        """
        def wrapper(name, data):
            if name == event_name:
                callback(data)
        
        self.event_emitted.connect(wrapper)
        return wrapper # Return the wrapper so it can be disconnected if needed
