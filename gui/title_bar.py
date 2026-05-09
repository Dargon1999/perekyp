from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect, QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter
import os
import logging
from gui.styles import StyleManager
from utils import resource_path

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("TitleBar") # Set ObjectName for QSS
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 20, 0)
        self.layout.setSpacing(10)
        self.setFixedHeight(40) # Reduced from 50
        
        # App Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20) # Reduced from 24
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

        self.title_label = QLabel()
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

        # Global Balance Label
        self.balance_label = QLabel("💳 $0")
        self.balance_label.setObjectName("BalanceLabel")
        self.balance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.balance_label.setStyleSheet("""
            QLabel#BalanceLabel {
                font-weight: 900;
                font-size: 16px;
                color: #f1c40f;
                background-color: rgba(241, 196, 15, 0.1);
                border: 1px solid rgba(241, 196, 15, 0.3);
                border-radius: 8px;
                padding: 5px 15px;
                margin-right: 10px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        self.layout.addWidget(self.balance_label)

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

        # SVG icon paths
        self.MIN_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 13H5V11H19V13Z" fill="currentColor"/></svg>"""
        self.CLOSE_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 6.41L17.59 5L12 10.59L6.41 5L5 6.41L10.59 12L5 17.59L6.41 19L12 13.41L17.59 19L19 17.59L13.41 12L19 6.41Z" fill="currentColor"/></svg>"""

        # Minimize Button
        self.min_btn = QPushButton()
        self.min_btn.setObjectName("MinimizeButton")
        self.min_btn.setFixedSize(45, 40)
        self.min_btn.clicked.connect(self.minimize_window)
        self.controls_layout.addWidget(self.min_btn)

        # Close Button
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(45, 40)
        self.close_btn.clicked.connect(self.close_window)
        self.controls_layout.addWidget(self.close_btn)
        
        self.layout.addLayout(self.controls_layout)

        # Movement tracking (Requirement 2: Back to TitleBar)
        self.isDragging = False
        self.dragPosition = QPoint()

    def setup_svg_icon(self, btn, svg_content, color=None):
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtCore import QByteArray
        
        # Replace currentColor with specific hex if provided
        if color:
            svg_content = svg_content.replace("currentColor", color)
            
        renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
        pixmap = QPixmap(16, 16) # Smaller icon size for controls
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        btn.setIcon(QIcon(pixmap))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Allow dragging from the title bar background and labels
            # The user specifically mentioned the area where profile and controls are.
            child = self.childAt(event.position().toPoint())
            
            # We allow dragging from empty space (None) or non-interactive labels
            if child in [None, self.title_label, self.icon_label, self.active_profile_label, self.balance_label]:
                self.isDragging = True
                self.dragPosition = event.globalPosition().toPoint() - self.parent.pos()
                event.accept()

    def mouseMoveEvent(self, event):
        if self.isDragging and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.dragPosition
            self.parent.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.isDragging = False
        event.accept()

    def minimize_window(self):
        self.parent.showMinimized()

    def close_window(self):
        self.parent.close()

    def set_theme(self, theme_name):
        # We need data_manager to get custom colors
        try:
            from data_manager import DataManager
            dm = DataManager()
            gta_color = dm.get_setting("header_gta_color", "#ffffff")
            dargon_color = dm.get_setting("header_dargon_color", "#3b82f6")
            show_dargon = dm.get_setting("header_show_dargon", True)
        except Exception as e:
            logging.warning(f"Failed to load header settings: {e}")
            gta_color = "#ffffff"
            dargon_color = "#3b82f6"
            show_dargon = True

        try:
            t = StyleManager.get_theme(theme_name)
        except Exception as e:
            logging.error(f"Failed to get theme {theme_name}: {e}")
            t = StyleManager.get_theme("dark")
        
        # Background blending
        bg_color = "transparent"
        
        # Colors
        title_color = t['text_main']
        accent_color = t['accent']
        active_profile_color = t['accent']
        
        # Use more contrast colors for controls (Requirement 1)
        # White for dark themes, dark for light themes
        control_icon_color = "#ffffff" if theme_name != "light" else "#2c3e50"
        
        if theme_name == "light":
            btn_bg = "rgba(0, 0, 0, 0.05)"
            btn_hover = "rgba(0, 0, 0, 0.1)"
        else:
            btn_bg = "rgba(255, 255, 255, 0.1)"
            btn_hover = "rgba(255, 255, 255, 0.2)"
            
        btn_border = t['border']
        btn_text = t['text_main']
        
        # Override with high contrast colors
        min_color = control_icon_color
        close_color = control_icon_color
        
        # Re-render icons with high contrast colors (Requirement 1)
        self.setup_svg_icon(self.min_btn, self.MIN_SVG, min_color)
        self.setup_svg_icon(self.close_btn, self.CLOSE_SVG, close_color)

        try:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg_color}; 
                    color: {title_color};
                }}
            """)
        except Exception as e:
            logging.warning(f"Failed to set title bar stylesheet: {e}")
        
        # App Icon update (ensure it's visible)
        try:
            icon_path = resource_path("icon.ico")
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self.icon_label.setPixmap(pixmap)
        except Exception as e:
            logging.warning(f"Failed to load app icon: {e}")
        
        # Beautiful Title with custom colors
        try:
            dargon_html = f' <span style="color: {dargon_color}; font-style: italic;">Dargon</span>' if show_dargon else ''
            self.title_label.setText(f'<span style="color: {gta_color};">GTA 5 RP</span>{dargon_html}')
            self.title_label.setStyleSheet(f"font-weight: 900; font-size: 20px; font-family: 'Segoe UI', sans-serif; border: none; letter-spacing: 1px;")
        except Exception as e:
            logging.warning(f"Failed to update title label: {e}")
        
        try:
            # Point 1: Ensure profile label is highly visible and has enough width
            self.active_profile_label.setStyleSheet(f"""
                QLabel {{
                    color: {active_profile_color}; 
                    background-color: rgba(255, 255, 255, 0.05); 
                    font-weight: 900; 
                    font-size: 14px;
                    margin-right: 10px; 
                    padding: 5px 15px; 
                    min-width: 180px; 
                    border-radius: 6px; 
                    border: 2px solid {active_profile_color};
                }}
            """)
        except Exception as e:
            logging.warning(f"Failed to update profile label: {e}")
        
        try:
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
        except Exception as e:
            logging.warning(f"Failed to set update_btn stylesheet: {e}")

        try:
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
        except Exception as e:
            logging.warning(f"Failed to set profile_btn stylesheet: {e}")
        
        try:
            self.min_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {min_color};
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                    color: {title_color};
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 255, 255, 0.05);
                }}
            """)
        except Exception as e:
            logging.warning(f"Failed to set min_btn stylesheet: {e}")
        
        try:
            self.close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {close_color};
                }}
                QPushButton:hover {{
                    background-color: #e74c3c;
                    color: white;
                }}
                QPushButton:pressed {{
                    background-color: #c0392b;
                }}
            """)
        except Exception as e:
            logging.warning(f"Failed to set close_btn stylesheet: {e}")
