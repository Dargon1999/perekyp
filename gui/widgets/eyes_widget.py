from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QCursor
import math

class EyesWidget(QWidget):
    def __init__(self, parent=None, eye_size=30, pupil_size=12, distance=10):
        super().__init__(parent)
        self.setFixedSize(eye_size * 2 + distance, eye_size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.eye_size = eye_size
        self.pupil_size = pupil_size
        self.distance = distance
        
        # Enable mouse tracking to update on hover
        self.setMouseTracking(True)
        
        # Timer for smooth updates if mouse is outside window (optional)
        # But for "following cursor" usually mouseMoveEvent is enough if inside,
        # or a timer if we want to track global cursor.
        # Let's use a timer to track global cursor for "always watching" effect.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._safe_update_eyes)
        self.timer.start(16) # ~60 FPS
        
    def _safe_update_eyes(self):
        """Wrapper to safely handle updates and catch interrupts."""
        try:
            self.update_eyes()
        except KeyboardInterrupt:
            pass

    def update_eyes(self):
        # Trigger repaint
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get cursor position mapped to widget
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        
        # Draw Left Eye
        left_center = QPoint(self.eye_size // 2, self.eye_size // 2)
        self.draw_eye(painter, left_center, cursor_pos)
        
        # Draw Right Eye
        right_center = QPoint(self.eye_size + self.distance + self.eye_size // 2, self.eye_size // 2)
        self.draw_eye(painter, right_center, cursor_pos)
        
    def draw_eye(self, painter, center, target):
        radius = self.eye_size / 2
        pupil_radius = self.pupil_size / 2
        
        # Convert center to QPointF for float precision drawing
        center_f = QPointF(center)

        # Draw White
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(QPen(QColor("black"), 2))
        painter.drawEllipse(center_f, radius, radius)
        
        # Calculate Pupil Position
        dx = target.x() - center.x()
        dy = target.y() - center.y()
        distance = math.sqrt(dx**2 + dy**2)
        
        max_dist = radius - pupil_radius - 2 # padding
        
        if distance > max_dist:
            angle = math.atan2(dy, dx)
            pupil_x = center.x() + max_dist * math.cos(angle)
            pupil_y = center.y() + max_dist * math.sin(angle)
        else:
            pupil_x = center.x() + dx
            pupil_y = center.y() + dy
            
        # Draw Pupil
        painter.setBrush(QBrush(QColor("black")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(pupil_x, pupil_y), pupil_radius, pupil_radius)
        
        # Optional: Shine
        painter.setBrush(QBrush(QColor("white")))
        painter.drawEllipse(QPointF(pupil_x - pupil_radius/3, pupil_y - pupil_radius/3), pupil_radius/4, pupil_radius/4)

