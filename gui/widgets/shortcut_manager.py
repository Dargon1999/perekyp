from PyQt6.QtWidgets import QWidget, QShortcut
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt

class ShortcutManager:
    SHORTCUTS = {
        "Ctrl+S": "save",
        "Ctrl+N": "new_transaction",
        "Ctrl+F": "search",
        "Ctrl+,": "settings",
        "Ctrl+1": "tab_car_rental",
        "Ctrl+2": "tab_clothes",
        "Ctrl+3": "tab_mining",
        "Ctrl+4": "tab_farm_bp",
        "Ctrl+5": "tab_memo",
        "Ctrl+6": "tab_analytics",
        "Ctrl+Q": "quit",
        "Escape": "close_dialog",
        "F5": "refresh",
    }
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self._shortcuts = {}
        self._callbacks = {}
        self._register_shortcuts()
        
    def _register_shortcuts(self):
        for key, action in self.SHORTCUTS.items():
            try:
                sequence = QKeySequence(key)
                shortcut = QShortcut(sequence, self.parent)
                shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
                self._shortcuts[key] = shortcut
            except Exception:
                pass
                
    def connect(self, key, callback):
        if key in self._shortcuts:
            self._shortcuts[key].activated.connect(callback)
            self._callbacks[key] = callback
            
    def disconnect(self, key):
        if key in self._shortcuts and key in self._callbacks:
            self._shortcuts[key].activated.disconnect(self._callbacks[key])
            del self._callbacks[key]
            
    def disconnect_all(self):
        for key in list(self._callbacks.keys()):
            self.disconnect(key)


class GlobalSearch:
    def __init__(self):
        self._search_handlers = []
        
    def register_handler(self, handler):
        self._search_handlers.append(handler)
        
    def search(self, query):
        results = []
        for handler in self._search_handlers:
            try:
                result = handler(query)
                if result:
                    results.extend(result)
            except Exception:
                pass
        return results
