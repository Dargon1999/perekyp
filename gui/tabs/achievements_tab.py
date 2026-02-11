from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QScrollArea, QFrame,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from gui.styles import StyleManager

TROPHY_SVG = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M19 5H17C17 3.9 16.1 3 15 3H9C7.9 3 7 3.9 7 5H5C3.9 5 3 5.9 3 7V8C3 10.21 4.79 12 7 12H7.16C7.62 13.9 9.13 15.42 11 15.83V19H8V21H16V19H13V15.83C14.87 15.42 16.38 13.9 16.84 12H17C19.21 12 21 10.21 21 8V7C21 5.9 20.1 5 19 5ZM5 8V7H7V8C7 9.1 6.1 10 5 10C3.9 10 3 9.1 3 8ZM17 10C15.9 10 15 9.1 15 8V5H9V8C9 9.1 8.1 10 7 10H7.03C7.24 11.66 8.65 13 10.42 13.56C10.9 13.72 11.44 13.8 12 13.8C12.56 13.8 13.1 13.72 13.58 13.56C15.35 13 16.76 11.66 16.97 10H17ZM19 8C19 9.1 18.1 10 17 10V7H19V8Z" fill="currentColor"/>
</svg>
"""

ACHIEVEMENTS_DATA = {
    "first_income": {
        "title": "Первый доход",
        "description": "Заработать первые деньги",
        "icon_color": "#f1c40f"
    },
    "rent_master": {
        "title": "Рантье",
        "description": "Получить доход от аренды авто",
        "icon_color": "#3498db"
    },
    "miner_pro": {
        "title": "Шахтер",
        "description": "Получить доход от майнинга",
        "icon_color": "#9b59b6"
    },
    "shopaholic": {
        "title": "Шопоголик",
        "description": "Купить 5 предметов одежды",
        "icon_color": "#e74c3c"
    },
    "millionaire": {
        "title": "Миллионер",
        "description": "Накопить 1,000,000 на счету",
        "icon_color": "#2ecc71"
    },
    "time_keeper": {
        "title": "Хранитель времени",
        "description": "Создать 5 таймеров",
        "icon_color": "#e67e22"
    }
}

class AchievementCard(QFrame):
    def __init__(self, key, data, is_unlocked):
        super().__init__()
        self.key = key
        self.data = data
        self.is_unlocked = is_unlocked
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(100)
        
        # Determine colors
        self.bg_color = "#2c3e50" if is_unlocked else "#2c2c2c" # Darker if locked
        self.text_color = "#ecf0f1" if is_unlocked else "#7f8c8d" # Dimmed if locked
        self.icon_color = data["icon_color"] if is_unlocked else "#555555"
        
        # Styles
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.bg_color};
                border-radius: 10px;
                border: 1px solid {'#34495e' if is_unlocked else '#1a1a1a'};
            }}
        """)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(50, 50)
        
        # Create Icon Pixmap
        renderer = QSvgRenderer(QByteArray(TROPHY_SVG.encode('utf-8')))
        pixmap = QPixmap(50, 50)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        
        # Colorize icon
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(pixmap.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(self.icon_color))
        painter.end()
        
        icon_lbl.setPixmap(pixmap)
        layout.addWidget(icon_lbl)
        
        # Text Info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        
        title = QLabel(self.data["title"])
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.text_color}; border: none; background: transparent;")
        
        desc = QLabel(self.data["description"])
        desc.setStyleSheet(f"font-size: 12px; color: {self.text_color}; border: none; background: transparent;")
        desc.setWordWrap(True)
        
        text_layout.addWidget(title)
        text_layout.addWidget(desc)
        text_layout.addStretch()
        
        layout.addLayout(text_layout)
        
        # Status Icon (Optional checkmark or lock)
        status_lbl = QLabel("🔒" if not self.is_unlocked else "🏆")
        status_lbl.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        layout.addWidget(status_lbl)

class AchievementsTab(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Достижения")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(header)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)
        
        self.refresh_data()
        
    def refresh_data(self):
        # Clear existing
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        unlocked_ids = self.data_manager.get_achievements()
        
        row = 0
        col = 0
        columns = 2 # 2 columns of cards
        
        for key, data in ACHIEVEMENTS_DATA.items():
            is_unlocked = key in unlocked_ids
            card = AchievementCard(key, data, is_unlocked)
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1
