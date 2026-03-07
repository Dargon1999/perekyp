from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect, QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QIcon, QPixmap
import os
from gui.styles import StyleManager
from utils import resource_path

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("TitleBar") # Set ObjectName for QSS
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 20, 0) # Adjusted margins
        self.layout.setSpacing(10) # Adjusted spacing
        self.setFixedHeight(50) 
        
        # App Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setScaledContents(True)
        
        icon_path = resource_path("icon.ico")
        
        # Try loading as QPixmap directly first (more reliable for QLabel)
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
             # Try QIcon fallback
             pixmap = QIcon(icon_path).pixmap(24, 24)
        
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap)
        else:
            # Last resort: solid color to indicate failure (for debug) or empty
            pass
            
        self.layout.addWidget(self.icon_label)
        
        # Update Button (Hidden by default)
        self.update_btn = QPushButton("🔄 Новое обновление")
        self.update_btn.setObjectName("UpdateBtn")
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setVisible(False)
        self.layout.addWidget(self.update_btn)

        # Title
        self.title_label = QLabel("GTA 5 RP Dargon")
        self.title_label.setObjectName("WindowTitle")
        
        # Add shadow effect to title
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.title_label.setGraphicsEffect(shadow)
        
        self.layout.addWidget(self.title_label)
        
        self.layout.addStretch()

        # Chat Button (AI Chat / Calculator)
        self.chat_btn = QPushButton("🤖 Чат ИИ")
        self.chat_btn.setObjectName("TitleBarButton")
        self.chat_btn.setFixedHeight(40)
        self.chat_btn.setMinimumWidth(150) # Increased from 120 to avoid "калькулято"
        self.chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_btn.setVisible(False) # Hidden by default
        self.layout.addWidget(self.chat_btn)

        # Active Profile Label
        self.active_profile_label = QLabel("")
        self.active_profile_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_profile_label.setStyleSheet("font-weight: bold; margin-right: 10px;")
        self.layout.addWidget(self.active_profile_label)

        # Profile Button
        self.profile_btn = QPushButton("⋮  Профили")
        self.profile_btn.setObjectName("TitleBarButton") # Set ObjectName
        self.profile_btn.setFixedHeight(40)
        self.profile_btn.setMinimumWidth(150)
        self.profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.layout.addWidget(self.profile_btn)

        # Window Controls Container
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(0)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)

        # Minimize Button
        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("TitleBarButton") # Set ObjectName
        self.min_btn.setFixedSize(45, 50) # Match bar height
        self.min_btn.clicked.connect(self.minimize_window)
        self.controls_layout.addWidget(self.min_btn)

        # Close Button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseButton") # Set ObjectName
        self.close_btn.setFixedSize(45, 50) # Match bar height
        self.close_btn.clicked.connect(self.close_window)
        self.controls_layout.addWidget(self.close_btn)
        
        self.layout.addLayout(self.controls_layout)

        # Movement tracking
        self.isDragging = False
        self.dragPosition = QPoint()
        
        # self.set_theme("dark") # Removed manual theme setting as it's handled by global QSS now

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Allow dragging from any point of the title bar that isn't a button
            if self.childAt(event.position().toPoint()) in [None, self.title_label, self.icon_label]:
                self.isDragging = True
                self.dragPosition = event.globalPosition().toPoint() - self.parent.pos()
                event.accept()

    def mouseMoveEvent(self, event):
        if self.isDragging and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.dragPosition
            
            # Ensure window stays within screen boundaries (optional, but requested)
            screen = QApplication.primaryScreen().availableGeometry()
            x = max(screen.left(), min(new_pos.x(), screen.right() - self.parent.width()))
            y = max(screen.top(), min(new_pos.y(), screen.bottom() - self.parent.height()))
            
            self.parent.move(x, y)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.isDragging = False
        event.accept()

    def minimize_window(self):
        self.parent.showMinimized()

    def close_window(self):
        self.parent.close()

    def set_theme(self, theme_name):
        t = StyleManager.get_theme(theme_name)
        
        # Background blending
        bg_color = "transparent"
        
        # Colors
        title_color = t['text_main']
        accent_color = t['accent']
        active_profile_color = t['accent']
        
        if theme_name == "light":
            btn_bg = "rgba(0, 0, 0, 0.05)"
            btn_hover = "rgba(0, 0, 0, 0.1)"
        else:
            btn_bg = "rgba(255, 255, 255, 0.1)"
            btn_hover = "rgba(255, 255, 255, 0.2)"
            
        btn_border = t['border']
        btn_text = t['text_main']
        
        min_color = t['text_secondary']
        min_hover = t['text_main']
        close_color = t['text_secondary']

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color}; 
                color: {title_color};
            }}
        """)
        
        # Beautiful Title
        self.title_label.setText(f'<span style="color: {title_color};">GTA 5 RP</span> <span style="color: {accent_color}; font-style: italic;">Dargon</span>')
        self.title_label.setStyleSheet(f"font-weight: 900; font-size: 20px; font-family: 'Segoe UI', sans-serif; border: none; letter-spacing: 1px;")
        
        self.active_profile_label.setStyleSheet(f"color: {active_profile_color}; background-color: transparent; font-weight: bold; margin-right: 10px; padding: 5px 15px; min-width: 150px; border-radius: 4px; border: 1px solid {active_profile_color};")
        
        self.update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #e67e22; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px; 
                padding: 5px 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #d35400;
            }}
        """)

        self.profile_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg}; 
                border: 1px solid {btn_border}; 
                border-radius: 4px;
                color: {btn_text};
                font-size: 13px;
                font-weight: bold;
                margin-right: 10px;
                padding-left: 10px;
                padding-right: 10px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: {btn_border};
            }}
        """)
        
        self.min_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {min_color};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                color: {title_color};
            }}
        """)
        
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {close_color};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #e74c3c;
                color: white;
            }}
        """)
