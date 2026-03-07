import sys
import os
import requests
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QPropertyAnimation, QEasingCurve, QThread, QSize, QRect, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QColor, QImage

class ImageLoader(QThread):
    loaded = pyqtSignal(QPixmap)
    failed = pyqtSignal()

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=10)
            if response.status_code == 200:
                img_data = response.content
                pixmap = QPixmap()
                if pixmap.loadFromData(img_data):
                    self.loaded.emit(pixmap)
                else:
                    self.failed.emit()
            else:
                self.failed.emit()
        except Exception:
            self.failed.emit()

class SmartImageWidget(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None, radius=10):
        super().__init__(parent)
        self.radius = radius
        self.pixmap = None
        self.placeholder_text = "No Image"
        self.keep_aspect_ratio = True
        self.hover_enabled = True
        self.is_loading = False
        
        # Opacity Effect for Fade In
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Hover Animation
        self.hover_scale = 1.0
        
        self.setMouseTracking(True)
        self.setMinimumSize(50, 50)

    def set_image_from_url(self, url):
        self.is_loading = True
        self.update()
        self.loader = ImageLoader(url)
        self.loader.loaded.connect(self.on_image_loaded)
        self.loader.failed.connect(self.on_load_failed)
        self.loader.start()

    def set_image_from_path(self, path):
        if os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                self.on_image_loaded(pix)
            else:
                self.on_load_failed()
        else:
            self.on_load_failed()

    def on_image_loaded(self, pixmap):
        self.pixmap = pixmap
        self.is_loading = False
        self.update()
        self.fade_in()

    def on_load_failed(self):
        self.is_loading = False
        self.pixmap = None
        self.placeholder_text = "Error"
        self.update()
        self.fade_in()

    def fade_in(self):
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clip Path (Rounded Corners)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)
        painter.setClipPath(path)
        
        # Background
        painter.fillPath(path, QColor("#2c3e50"))
        
        if self.pixmap:
            # Scale logic
            target_rect = self.rect()
            
            # Apply Hover Scale if enabled (simple zoom effect)
            if self.hover_enabled and self.hover_scale > 1.0:
                # Calculate center zoom
                w = target_rect.width() * self.hover_scale
                h = target_rect.height() * self.hover_scale
                x = target_rect.center().x() - w / 2
                y = target_rect.center().y() - h / 2
                target_rect = QRectF(x, y, w, h)
            
            if self.keep_aspect_ratio:
                scaled = self.pixmap.scaled(
                    self.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                # Center the image
                x = (self.width() - scaled.width()) / 2
                y = (self.height() - scaled.height()) / 2
                painter.drawPixmap(int(x), int(y), scaled)
            else:
                # Fill (Crop)
                scaled = self.pixmap.scaled(
                    self.size(), 
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                    Qt.TransformationMode.SmoothTransformation
                )
                # Draw center crop
                source_x = (scaled.width() - self.width()) / 2
                source_y = (scaled.height() - self.height()) / 2
                painter.drawPixmap(0, 0, scaled, int(source_x), int(source_y), self.width(), self.height())
                
        else:
            # Placeholder / Loading / Error
            painter.setPen(QColor("#7f8c8d"))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            
            text = "Loading..." if self.is_loading else self.placeholder_text
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def enterEvent(self, event):
        if self.hover_enabled and self.pixmap:
            self.hover_scale = 1.05
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.hover_enabled and self.pixmap:
            self.hover_scale = 1.0
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
