from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

class ToastNotification(QWidget):
    closed = pyqtSignal()
    
    TOAST_TYPES = {
        "info": {"bg": "#1e293b", "border": "#3b82f6", "icon": "ℹ️"},
        "success": {"bg": "#1e293b", "border": "#10b981", "icon": "✅"},
        "warning": {"bg": "#1e293b", "border": "#f59e0b", "icon": "⚠️"},
        "error": {"bg": "#1e293b", "border": "#ef4444", "icon": "❌"},
    }
    
    def __init__(self, parent=None, message="", toast_type="info", duration=3000):
        super().__init__(parent)
        self.message = message
        self.toast_type = toast_type
        self.duration = duration
        self.config = self.TOAST_TYPES.get(toast_type, self.TOAST_TYPES["info"])
        
        self.setup_ui()
        self.setup_animation()
        
    def setup_ui(self):
        self.setFixedHeight(60)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        self.icon_label = QLabel(self.config["icon"])
        self.icon_label.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        layout.addWidget(self.icon_label)
        
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("""
            QLabel {
                color: #f1f5f9;
                font-size: 14px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.message_label, stretch=1)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #9ca3af;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #f1f5f9;
            }
        """)
        self.close_btn.clicked.connect(self.hide_notification)
        layout.addWidget(self.close_btn)
        
        border_color = self.config["border"]
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.config["bg"]};
                border: 1px solid {border_color};
                border-left: 3px solid {border_color};
                border-radius: 8px;
            }}
        """)
        
    def setup_animation(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self.opacity_effect)
        
        self._fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0)
        self._fade_in.setEndValue(1)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self._fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self._fade_out.setDuration(200)
        self._fade_out.setStartValue(1)
        self._fade_out.setEndValue(0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._fade_out.finished.connect(self._on_fade_out_finished)
        
    def show_notification(self):
        self._fade_in.start()
        if self.duration > 0:
            QTimer.singleShot(self.duration, self.hide_notification)
        
    def hide_notification(self):
        self._fade_out.start()
        
    def _on_fade_out_finished(self):
        self.closed.emit()
        self.close()


class ToastManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._toasts = []
            cls._instance._container = None
        return cls._instance
    
    def set_container(self, container):
        self._container = container
        
    def show(self, message, toast_type="info", duration=3000):
        if self._container is None:
            return
            
        toast = ToastNotification(message=message, toast_type=toast_type, duration=duration)
        toast.closed.connect(lambda: self._remove_toast(toast))
        
        self._toasts.append(toast)
        self._reposition_toasts()
        
        self._container.layout().addWidget(toast)
        toast.show_notification()
        
    def _remove_toast(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition_toasts()
        
    def _reposition_toasts(self):
        spacing = 10
        offset_y = 10
        for toast in self._toasts:
            toast.move(10, offset_y)
            offset_y += toast.height() + spacing
            
    def info(self, message, duration=3000):
        self.show(message, "info", duration)
        
    def success(self, message, duration=3000):
        self.show(message, "success", duration)
        
    def warning(self, message, duration=4000):
        self.show(message, "warning", duration)
        
    def error(self, message, duration=5000):
        self.show(message, "error", duration)
