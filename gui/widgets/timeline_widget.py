from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSlot
from datetime import datetime

class TimelineItem(QFrame):
    def __init__(self, title, amount, timestamp, category=None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("TimelineItem")
        self.setStyleSheet("""
            #TimelineItem {
                background-color: #2c3e50;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 5px;
            }
        """)
        
        layout = QHBoxLayout(self)
        
        # Icon/Category placeholder
        icon_label = QLabel("💰" if amount >= 0 else "💸")
        icon_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon_label)
        
        # Info layout
        info_layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: white;")
        
        time_str = timestamp.strftime("%H:%M") if isinstance(timestamp, datetime) else str(timestamp)
        time_label = QLabel(f"{time_str} | {category or 'General'}")
        time_label.setStyleSheet("font-size: 10px; color: #95a5a6;")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(time_label)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # Amount
        amount_label = QLabel(f"{'+' if amount >= 0 else ''}{amount:,.2f} $")
        amount_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {'#2ecc71' if amount >= 0 else '#e74c3c'};")
        layout.addWidget(amount_label)

class TimelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.header = QLabel("Activity Feed")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(self.header)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.container)
        
        self.layout.addWidget(self.scroll)

    @pyqtSlot(str, object)
    def add_event(self, event_name, data):
        """Adds an event to the timeline based on event bus signal."""
        if event_name == "transaction_added":
            item = TimelineItem(
                title=data.get("note", "Transaction"),
                amount=data.get("amount", 0),
                timestamp=data.get("timestamp", datetime.now()),
                category=data.get("module")
            )
            self.container_layout.insertWidget(0, item)
        elif event_name == "asset_added":
            item = TimelineItem(
                title=f"New Asset: {data.get('name')}",
                amount=-data.get("purchase_price", 0),
                timestamp=datetime.now(),
                category="Asset"
            )
            self.container_layout.insertWidget(0, item)
