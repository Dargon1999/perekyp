from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit
from event_bus import EventBus

class FishingUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("🎣 Fishing Tracker"))
        
        self.fish_input = QLineEdit()
        self.fish_input.setPlaceholderText("Fish Name")
        layout.addWidget(self.fish_input)
        
        self.profit_input = QLineEdit()
        self.profit_input.setPlaceholderText("Profit Amount")
        layout.addWidget(self.profit_input)
        
        self.catch_btn = QPushButton("Catch Fish!")
        self.catch_btn.clicked.connect(self.on_catch)
        layout.addWidget(self.catch_btn)
        
        layout.addStretch()

    def on_catch(self):
        fish_name = self.fish_input.text() or "Unknown Fish"
        try:
            profit = float(self.profit_input.text() or 0)
        except ValueError:
            profit = 0
            
        # Emit an event that the main app or other plugins can handle
        EventBus.get_instance().emit("catch_button_clicked", {"name": fish_name, "profit": profit})
        
        # Clear inputs
        self.fish_input.clear()
        self.profit_input.clear()

def create_ui(parent=None):
    return FishingUI(parent)
