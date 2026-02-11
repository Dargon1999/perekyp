from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QScrollArea, QFrame, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    pyqtProperty, QSize, QParallelAnimationGroup, QPoint
)
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QIcon

class ModernTabButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(45)
        
        # Properties for animation
        self._indicator_width = 0.0
        self._bg_opacity = 0.0
        
        # Setup animations
        self.indicator_anim = QPropertyAnimation(self, b"indicator_width")
        self.indicator_anim.setDuration(250)
        self.indicator_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.bg_anim = QPropertyAnimation(self, b"bg_opacity")
        self.bg_anim.setDuration(200)
        
        # Colors (defaults)
        self.text_active = QColor("#3b82f6")
        self.text_inactive = QColor("#94a3b8")
        self.indicator_color = QColor("#3b82f6")
        self.hover_bg = QColor(255, 255, 255, 10)
        
        # Accessibility
        self.setAccessibleName(text)
        self.setAccessibleDescription(f"Tab button for {text}")

    @pyqtProperty(float)
    def indicator_width(self):
        return self._indicator_width
        
    @indicator_width.setter
    def indicator_width(self, val):
        self._indicator_width = val
        self.update()
        
    @pyqtProperty(float)
    def bg_opacity(self):
        return self._bg_opacity
        
    @bg_opacity.setter
    def bg_opacity(self, val):
        self._bg_opacity = val
        self.update()

    def enterEvent(self, event):
        if not self.isChecked():
            self.bg_anim.stop()
            self.bg_anim.setEndValue(1.0)
            self.bg_anim.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        if not self.isChecked():
            self.bg_anim.stop()
            self.bg_anim.setEndValue(0.0)
            self.bg_anim.start()
        super().leaveEvent(event)

    def setChecked(self, checked):
        super().setChecked(checked)
        self.indicator_anim.stop()
        self.indicator_anim.setEndValue(1.0 if checked else 0.0)
        self.indicator_anim.start()
        
        # Reset bg opacity if checked (we don't want hover effect when active usually, or different one)
        if checked:
            self.bg_anim.stop()
            self.bg_anim.setEndValue(0.0)
            self.bg_anim.start()

    def set_colors(self, text_active, text_inactive, indicator, hover_bg):
        self.text_active = QColor(text_active)
        self.text_inactive = QColor(text_inactive)
        self.indicator_color = QColor(indicator)
        self.hover_bg = QColor(hover_bg)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # Draw Hover Background
        if self._bg_opacity > 0.01:
            bg_color = QColor(self.hover_bg)
            bg_color.setAlpha(int(self.hover_bg.alpha() * self._bg_opacity))
            painter.setBrush(bg_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 6, 6)
            
        # Draw Text
        font = self.font()
        font.setBold(self.isChecked())
        size = 11 if self.isChecked() else 10
        if size > 0:
            font.setPointSize(size)
        painter.setFont(font)
        
        if self.isChecked():
            painter.setPen(self.text_active)
        else:
            painter.setPen(self.text_inactive)
            
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        
        # Draw Indicator
        if self._indicator_width > 0.01:
            ind_height = 3
            # Width grows from center
            target_w = rect.width() - 20 # padding
            current_w = target_w * self._indicator_width
            
            x = rect.center().x() - (current_w / 2)
            y = rect.bottom() - ind_height - 2
            
            painter.setBrush(self.indicator_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(current_w), ind_height, 1.5, 1.5)


class ModernTabWidget(QWidget):
    currentChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Tab Bar Container (Scrollable)
        self.tab_bar_scroll = QScrollArea()
        self.tab_bar_scroll.setWidgetResizable(True)
        self.tab_bar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.tab_bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tab_bar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tab_bar_scroll.setFixedHeight(60) # Fixed height for tab bar
        self.tab_bar_scroll.setStyleSheet("background: transparent;")
        
        self.tab_bar_container = QWidget()
        self.tab_bar_container.setStyleSheet("background: transparent;")
        self.tab_bar_layout = QHBoxLayout(self.tab_bar_container)
        self.tab_bar_layout.setContentsMargins(10, 5, 10, 5)
        self.tab_bar_layout.setSpacing(10)
        self.tab_bar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.tab_bar_scroll.setWidget(self.tab_bar_container)
        self.layout.addWidget(self.tab_bar_scroll)
        
        # Content Area
        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)
        
        self.buttons = []
        self.pages = []
        
        # Theme data placeholder
        self.current_theme = None

    def addTab(self, widget, label):
        """Compatible API with QTabWidget"""
        btn = ModernTabButton(label)
        btn.clicked.connect(lambda: self.set_current_index(self.buttons.index(btn)))
        
        self.tab_bar_layout.addWidget(btn)
        self.stacked_widget.addWidget(widget)
        
        self.buttons.append(btn)
        self.pages.append(widget)
        
        # Apply theme if we have one
        if self.current_theme:
            self._style_button(btn, self.current_theme)
            
        # Select first tab by default
        if len(self.buttons) == 1:
            btn.setChecked(True)
            
    def set_current_index(self, index):
        if 0 <= index < len(self.buttons):
            # Update buttons
            for i, btn in enumerate(self.buttons):
                btn.setChecked(i == index)
                
            # Switch page with animation (optional, for now simple switch)
            # self.stacked_widget.setCurrentIndex(index)
            self.animate_page_switch(index)
            
            self.currentChanged.emit(index)

    def animate_page_switch(self, index):
        current_idx = self.stacked_widget.currentIndex()
        if current_idx == index:
            return
            
        # Simple fade transition could go here, but for now standard switch
        self.stacked_widget.setCurrentIndex(index)
        
        # If we wanted to add slide animation:
        # We would need to grab pixmaps of widgets and animate a label
        # Keeping it simple and snappy for now as requested "smooth" usually applies to the tab bar interaction too.

    def apply_theme(self, theme):
        self.current_theme = theme
        
        # Style the scroll area background if needed (usually transparent)
        # self.tab_bar_scroll.setStyleSheet(f"background-color: {theme['bg_main']};")
        
        for btn in self.buttons:
            self._style_button(btn, theme)
            
    def _style_button(self, btn, theme):
        btn.set_colors(
            text_active=theme['accent'],
            text_inactive=theme['text_secondary'],
            indicator=theme['accent'],
            hover_bg=theme['text_main'] # Use text color with low alpha in paint event
        )
        # Set hover alpha for the button internal logic
        # We passed the base color, the button handles opacity
        
        # We also need to set the font family globally for the button via stylesheet or font
        # But paintEvent handles font drawing.
