from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

class LoadingSpinner(QWidget):
    def __init__(self, parent=None, size=40, color=None):
        super().__init__(parent)
        self.size = size
        self.color = color or "#3b82f6"
        self.angle = 0
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.rotate)
        self._opacity = 1.0

    def start(self):
        self._timer.start(30)

    def stop(self):
        self._timer.stop()
        self.angle = 0
        self.update()

    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        
        pen = QPen(QColor(self.color))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        span = 90
        for i in range(8):
            alpha = int(255 * (i + 1) / 8)
            pen.setColor(QColor(self.color))
            pen.setAlpha(alpha)
            painter.setPen(pen)
            start_angle = i * (360 / 8)
            painter.drawArc(-self.size/4, -self.size/4, self.size/2, self.size/2, 
                           start_angle * 16, span * 16)
            painter.rotate(360 / 8)


class LoadingOverlay(QWidget):
    def __init__(self, parent=None, message="Загрузка..."):
        super().__init__(parent)
        self.message = message
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        self.spinner = LoadingSpinner(self, size=50)
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel(self.message)
        self.label.setStyleSheet("""
            QLabel {
                color: #f1f5f9;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.setStyleSheet("background-color: rgba(10, 15, 26, 0.85);")
        
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0)
        self.setGraphicsEffect(effect)
        self._show_anim = QPropertyAnimation(effect, b"opacity")
        self._show_anim.setDuration(200)
        self._show_anim.setStartValue(0)
        self._show_anim.setEndValue(1)
        self._show_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
    def showEvent(self, event):
        self.spinner.start()
        self._show_anim.start()
        super().showEvent(event)
        
    def hideEvent(self, event):
        self.spinner.stop()
        super().hideEvent(event)

    def setMessage(self, message):
        self.label.setText(message)


class SkeletonLoader(QWidget):
    def __init__(self, parent=None, width=200, height=20):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.setFixedSize(width, height)
        self._shimmer_pos = -width
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._shimmer)
        self.start = self._timer.start
        self.stop = self._timer.stop
        
    def _shimmer(self):
        self._shimmer_pos += 5
        if self._shimmer_pos > self.width:
            self._shimmer_pos = -self.width
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        bg_color = QColor("#1e293b")
        painter.fillRect(0, 0, self.width, self.height, bg_color)
        
        shimmer_width = self.width // 3
        gradient = QColor("#334155")
        painter.fillRect(self._shimmer_pos, 0, shimmer_width, self.height, gradient)
        
    def startAnimation(self):
        self._timer.start(30)
        
    def stopAnimation(self):
        self._timer.stop()
