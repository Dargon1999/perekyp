
from PyQt6.QtWidgets import QWidget, QCheckBox
from PyQt6.QtCore import Qt, pyqtProperty, QPropertyAnimation, QRect, QPoint, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, width=50, height=28, bg_color="#777", circle_color="#DDD", active_color="#00BCff"):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._bg_color = bg_color
        self._circle_color = circle_color
        self._active_color = active_color
        
        self._circle_position = 3
        self._checked = False

        self.animation = QPropertyAnimation(self, b"circle_position", self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setDuration(200)

    @pyqtProperty(int)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def setChecked(self, checked):
        self._checked = checked
        self.start_animation()
        self.toggled.emit(self._checked)

    def isChecked(self):
        return self._checked

    def toggle(self):
        self.setChecked(not self._checked)

    def mousePressEvent(self, event):
        self.toggle()

    def start_animation(self):
        self.animation.stop()
        if self._checked:
            self.animation.setEndValue(self.width() - self.height() + 3)
        else:
            self.animation.setEndValue(3)
        self.animation.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Background
        rect = self.rect()
        if self._checked:
            bg_color = QColor(self._active_color)
        else:
            bg_color = QColor(self._bg_color)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg_color))
        p.drawRoundedRect(0, 0, rect.width(), rect.height(), rect.height() / 2, rect.height() / 2)

        # Draw Circle
        p.setBrush(QBrush(QColor(self._circle_color)))
        p.drawEllipse(self._circle_position, 3, self.height() - 6, self.height() - 6)
        p.end()
