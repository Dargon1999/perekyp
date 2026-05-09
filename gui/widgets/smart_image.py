import sys
import os
import requests
import logging
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import (
    Qt, QUrl, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QThreadPool, QRunnable, QObject, QSize, QRect, QRectF
)
import hashlib
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QColor, QImage

# --- Global Thread Pool ---
# Using a single thread pool for all image loading operations application-wide
# This prevents creating hundreds of threads and improves stability.
global_image_thread_pool = QThreadPool()
global_image_thread_pool.setMaxThreadCount(10) # Limit concurrent downloads

# --- Cache Directory Setup ---
app_data = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
IMAGE_CACHE_DIR = os.path.join(app_data, "MoneyTracker", "image_cache")
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

class ImageLoaderSignals(QObject):
    """Custom signals for the QRunnable image loader."""
    loaded = pyqtSignal(QImage) # Changed from QPixmap to QImage for thread safety
    failed = pyqtSignal(str)

class ImageLoader(QRunnable):
    """A QRunnable task to download an image in the background via the global thread pool."""
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = ImageLoaderSignals()

    def run(self):
        try:
            # 1. Check Local Cache
            url_hash = hashlib.md5(self.url.encode()).hexdigest()
            cache_path = os.path.join(IMAGE_CACHE_DIR, url_hash)
            
            if os.path.exists(cache_path):
                image = QImage()
                if image.load(cache_path):
                    logging.info(f"[SmartImage] Loaded from local cache: {self.url}")
                    self.signals.loaded.emit(image)
                    return
            
            # 2. If not in cache, download
            logging.info(f"[SmartImage] Starting download from thread pool: {self.url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
            }
            
            response = requests.get(self.url, headers=headers, stream=True, timeout=20, allow_redirects=True)
            
            if response.status_code == 200:
                img_data = response.content
                # Save to cache
                try:
                    with open(cache_path, 'wb') as f:
                        f.write(img_data)
                except Exception as e:
                    logging.warning(f"[SmartImage] Failed to save cache: {e}")
                    
                # Use QImage for background loading (QPixmap is not thread-safe)
                image = QImage()
                if image.loadFromData(img_data):
                    logging.info(f"[SmartImage] Successfully loaded image data: {self.url} ({len(img_data)} bytes)")
                    self.signals.loaded.emit(image)
                else:
                    logging.error(f"[SmartImage] Error parsing image data: {self.url}")
                    self.signals.failed.emit("Parse Error")
            else:
                logging.error(f"[SmartImage] HTTP Error {response.status_code}: {self.url}")
                self.signals.failed.emit(f"HTTP {response.status_code}")
        except Exception as e:
            logging.error(f"[SmartImage] Exception during download {self.url}: {str(e)}")
            self.signals.failed.emit(str(e))

class SmartImageWidget(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None, radius=10):
        super().__init__(parent)
        self.radius = radius
        self.pixmap = None
        self.placeholder_text = "Loading..."
        self.error_text = ""
        self.keep_aspect_ratio = True
        self.hover_enabled = True
        self.is_loading = False
        self.current_url = None # To track the active URL
        
        # Simple fade-in without QGraphicsEffect for better stability
        self.opacity = 1.0 
        
        # Hover Animation
        self.hover_scale = 1.0
        
        self.setMouseTracking(True)
        self.setMinimumSize(50, 50)

    def set_image_from_url(self, url):
        if not url:
            self.on_load_failed("No URL")
            return

        # Fix GitHub URLs (Independent checks for robustness)
        fixed_url = url
        if "github.com" in fixed_url:
            fixed_url = fixed_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        
        # Always remove query params for raw content if they exist
        if "raw.githubusercontent.com" in fixed_url:
            fixed_url = fixed_url.split("?")[0]
        
        # If a new URL is set while one is loading, this prevents the old one from displaying
        self.current_url = fixed_url
        
        self.is_loading = True
        self.error_text = ""
        self.pixmap = None # Clear previous image
        self.placeholder_text = "Загрузка..."
        self.update()
        
        # Use the global thread pool
        loader = ImageLoader(fixed_url)
        loader.signals.loaded.connect(lambda p, u=fixed_url: self.on_image_loaded(p, u))
        loader.signals.failed.connect(lambda e, u=fixed_url: self.on_load_failed(e, u))
        global_image_thread_pool.start(loader)

    def set_image_from_path(self, path):
        self.current_url = None # It's a local path
        if os.path.exists(path):
            img = QImage(path)
            if not img.isNull():
                self.on_image_loaded(img, path)
            else:
                self.on_load_failed("Invalid local image", path)
        else:
            self.on_load_failed("Path not found", path)

    def on_image_loaded(self, image, url):
        # Only display the image if the URL is the one we currently want
        if self.current_url == url:
            # Convert QImage to QPixmap on the GUI thread
            self.pixmap = QPixmap.fromImage(image)
            self.is_loading = False
            self.error_text = ""
            self.update()

    def on_load_failed(self, error_msg="Error", url=None):
        if self.current_url == url:
            self.is_loading = False
            self.pixmap = None
            self.error_text = error_msg
            self.placeholder_text = "❌"
            self.update()

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
