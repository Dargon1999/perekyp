from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, QEvent, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from gui.tabs.generic_tab import GenericTab
from gui.localization_manager import LocalizationManager

class PricePopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            PricePopup {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 8px;
            }
            QLabel {
                color: #ecf0f1;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel#Header {
                font-weight: 600;
                color: #bdc3c7;
                font-size: 10px; /* Reduced font size for headers */
                padding: 4px;
                border-bottom: 1px solid #546e7a;
            }
            QLabel#Cell {
                padding: 4px 8px;
                font-size: 12px;
            }
            QLabel#CellMoney {
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
                color: #2ecc71;
            }
            QLabel#Title {
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 8px;
                color: #f1c40f;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)
        
        self.lm = LocalizationManager()
        self.setup_ui()
        
    def setup_ui(self):
        title = QLabel(self.lm.translations['ru']['harvest.price_comparison_title'])
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)
        
        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setColumnStretch(0, 1) # Animal
        grid.setColumnStretch(1, 1) # Buyer
        grid.setColumnStretch(2, 1) # Rednecks
        
        headers = [
            self.lm.translations['ru']['harvest.price_comparison_animal'],
            self.lm.translations['ru']['harvest.price_comparison_buyer'],
            self.lm.translations['ru']['harvest.price_comparison_rednecks']
        ]
        
        for col, h in enumerate(headers):
            lbl = QLabel(h.upper())
            lbl.setObjectName("Header")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, 0, col)
            
        data = [
            ("rabbit", "1 000 $", "1 160 $"),
            ("boar", "2 500 $", "2 900 $"),
            ("deer", "4 000 $", "4 640 $"),
            ("coyote", "7 500 $", "8 700 $"),
            ("cougar", "15 000 $", "17 400 $")
        ]
        
        for row, (animal_key, buyer, rednecks) in enumerate(data, 1):
            animal_name = self.lm.translations['ru'][f'harvest.price_comparison_{animal_key}']
            
            # Animal Name
            lbl_name = QLabel(animal_name)
            lbl_name.setObjectName("Cell")
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Prices
            lbl_buyer = QLabel(buyer)
            lbl_buyer.setObjectName("CellMoney")
            lbl_buyer.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            lbl_rednecks = QLabel(rednecks)
            lbl_rednecks.setObjectName("CellMoney")
            lbl_rednecks.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Alternating row background (simulated with QFrame or just implicit visual flow)
            # For simplicity and compactness, we rely on spacing and text alignment.
            
            grid.addWidget(lbl_name, row, 0)
            grid.addWidget(lbl_buyer, row, 1)
            grid.addWidget(lbl_rednecks, row, 2)
            
        self.layout.addLayout(grid)
        
        # Additional Info
        info_label = QLabel(self.lm.translations['ru'].get('harvest.price_comparison_integrity_info', ''))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #95a5a6; font-size: 10px; margin-top: 8px; font-style: italic;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(info_label)
        
        # Accessibility
        self.setAccessibleName(title.text())
        
        # Adjust size to fit content tightly
        self.adjustSize()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def show_at(self, pos):
        # Adjust position to not go off-screen
        screen = QApplication.primaryScreen().geometry()
        size = self.sizeHint()
        
        x = pos.x()
        y = pos.y()
        
        # Responsive check (width < 768)
        # Note: In a real responsive web app, we check viewport. Here we check main window or screen.
        # User req: "width < 768 px tooltip centers"
        # We can check parent window width if available.
        parent_window = self.parent()
        if parent_window and parent_window.width() < 768:
            # Center in parent
            parent_rect = parent_window.geometry()
            x = parent_rect.center().x() - size.width() // 2
            y = parent_rect.center().y() - size.height() // 2
        else:
            # Default positioning (bottom-right of cursor/icon)
            if x + size.width() > screen.right():
                x = screen.right() - size.width() - 10
            if y + size.height() > screen.bottom():
                y = screen.bottom() - size.height() - 10
        
        self.move(x, y)
        self.show()
        self.raise_()

class MiningTab(GenericTab):
    def __init__(self, data_manager, parent=None):
        super().__init__(data_manager, "mining", parent)
        self.popup = None
        self.setup_info_icon()

    def get_extra_fields(self):
        return []

    def setup_info_icon(self):
        self.info_btn = QPushButton()
        self.info_btn.setFixedSize(24, 24) # Slightly larger for hit area, icon will be 16x16
        self.info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_btn.setToolTip(LocalizationManager().translations['ru']['harvest.price_comparison_title'])
        self.info_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        # Create SVG Icon
        svg_data = """<svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="8" r="7" stroke="#3498db" stroke-width="1.5" fill="none"/>
            <text x="8" y="12" text-anchor="middle" font-size="10" font-family="Arial" font-weight="bold" fill="#3498db">i</text>
        </svg>"""
        
        renderer = QSvgRenderer(bytearray(svg_data, 'utf-8'))
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        self.info_btn.setIcon(QIcon(pixmap))
        self.info_btn.clicked.connect(self.show_popup)
        
        # Insert next to export button
        # self.header_layout is available from GenericTab (modified)
        try:
            index = self.header_layout.indexOf(self.export_btn)
            if index != -1:
                self.header_layout.insertWidget(index + 1, self.info_btn)
                # Add a small spacing
                self.header_layout.insertSpacing(index + 1, 5)
            else:
                self.header_layout.addWidget(self.info_btn)
        except AttributeError:
            # Fallback if header_layout is not accessible (should not happen with my fix)
            pass

    def show_popup(self):
        if not self.popup:
            self.popup = PricePopup(self.window()) # Use window() as parent to handle positioning relative to window
            
        # Position logic
        # Map button position to global
        pos = self.info_btn.mapToGlobal(QPoint(0, self.info_btn.height()))
        self.popup.show_at(pos)
