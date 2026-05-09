from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QFrame,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QComboBox,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QDialog,
    QSlider,
    QGraphicsOpacityEffect,
    QSizePolicy,
    QApplication
)
from PyQt6.QtCore import Qt, QSize, QEvent, QPoint, QTimer, QPropertyAnimation, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor
from datetime import datetime
import random
import os
import requests
import tempfile
import shutil
import atexit
import logging
from gui.styles import StyleManager
from gui.custom_dialogs import StyledDialogBase


class ImageDownloaderWorker(QThread):
    image_ready = pyqtSignal(str, str) # name, path
    finished = pyqtSignal()

    def __init__(self, image_map, temp_dir):
        super().__init__()
        self.image_map = image_map
        self.temp_dir = temp_dir
        self.base_url = "https://raw.githubusercontent.com/Dargon1999/taro/refs/heads/main/"
        self.logger = logging.getLogger("ImageDownloader")

    def run(self):
        self.logger.info(f"Starting image download to {self.temp_dir}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for name, filename in self.image_map.items():
            url = self.base_url + filename
            local_filename = filename.replace("%20", " ")
            local_path = os.path.join(self.temp_dir, local_filename)
            
            # Check if exists and valid
            if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
                try:
                    self.logger.info(f"Downloading {name} from {url}")
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                        self.logger.info(f"Saved {name} to {local_path}")
                    else:
                        self.logger.warning(f"Failed to download {name}: Status {response.status_code}")
                except Exception as e:
                    self.logger.error(f"Error downloading {name}: {e}")
            else:
                self.logger.debug(f"Image {name} already exists at {local_path}")
            
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                self.image_ready.emit(name, local_path)
        
        self.finished.emit()



class ImageZoomDialog(StyledDialogBase):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent, "Просмотр изображения")
        self.original_pixmap = pixmap
        self.current_scale = 1.0
        self.resize(600, 400)

        self.grabGesture(Qt.GestureType.PinchGesture)
        self._drag_active = False
        self._last_pos = None
        self._velocity = QPoint(0, 0)
        self._inertia_timer = QTimer(self)
        self._inertia_timer.setInterval(16)
        self._inertia_timer.timeout.connect(self.apply_inertia)

        # Use content_layout from StyledDialogBase
        self.content_layout.setSpacing(10)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("background: transparent;")

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.image_label)
        self.content_layout.addWidget(self.scroll, 1)
        self.scroll.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        self.scroll.viewport().installEventFilter(self)

        # Close Button (Top-Right)
        # StyledDialogBase has a header, but we want a visible close button overlay or in header
        # Actually, StyledDialogBase likely already has a close button in its custom title bar if it uses one.
        # But if the user asks for a specific "X" button, let's add it explicitly or check StyledDialogBase.
        # Since StyledDialogBase implementation isn't fully visible here, I'll add a floating close button 
        # to the top-right of the image area or ensure the dialog has one.
        
        # However, to be safe and simple, let's add a "Close" button in the bottom controls row 
        # OR add a top-right overlay button if strictly requested "in the top right corner of the window".
        # The user said: "visible close button in the right upper corner of the window with the photo".
        
        # Let's add it to the top-right of the content area using a layout overlay or just ensuring the dialog has it.
        # Assuming StyledDialogBase might be frameless custom dialog.
        
        # Let's add a floating close button on top of the scroll area
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(0, 0, 0, 0.5);
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.8); /* Red hover */
            }}
        """)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.raise_()

        controls = QHBoxLayout()
        
        t = StyleManager.get_theme(self._theme)
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {t['accent']};
                border: 1px solid {t['accent']};
                border-radius: 4px;
                font-weight: bold;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {t['accent']}1A;
            }}
        """
        
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(32, 32)
        zoom_out_btn.setStyleSheet(btn_style)
        
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(32, 32)
        zoom_in_btn.setStyleSheet(btn_style)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(50)
        self.slider.setMaximum(200)
        self.slider.setValue(100)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {t['border']};
                height: 8px;
                background: {t['bg_tertiary']};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {t['accent']};
                border: 1px solid {t['accent']};
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }}
        """)

        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_in_btn.clicked.connect(self.zoom_in)
        self.slider.valueChanged.connect(self.slider_changed)

        controls.addStretch()
        controls.addWidget(zoom_out_btn)
        controls.addWidget(self.slider)
        controls.addWidget(zoom_in_btn)
        controls.addStretch()

        self.content_layout.addLayout(controls)

        self.update_pixmap()

    def resizeEvent(self, event):
        # StyledDialogBase handles resize, but we need to update pixmap
        super().resizeEvent(event)
        self.update_pixmap()

    def event(self, event):
        if event.type() == QEvent.Type.Gesture:
            return self.handle_gesture(event)
        return super().event(event)

    def slider_changed(self, value):
        self.current_scale = value / 100.0
        self.update_pixmap()

    def zoom_in(self):
        value = min(self.slider.value() + 10, self.slider.maximum())
        self.slider.setValue(value)

    def zoom_out(self):
        value = max(self.slider.value() - 10, self.slider.minimum())
        self.slider.setValue(value)

    def update_pixmap(self):
        if self.original_pixmap.isNull():
            return
        base_size = self.scroll.viewport().size()
        if not base_size.isValid():
            return
        target_width = int(base_size.width() * self.current_scale)
        target_height = int(base_size.height() * self.current_scale)
        scaled = self.original_pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def handle_gesture(self, event):
        pinch = event.gesture(Qt.GestureType.PinchGesture)
        if pinch is None:
            return True
        factor = pinch.scaleFactor()
        new_scale = self.current_scale * factor
        min_scale = self.slider.minimum() / 100.0
        max_scale = self.slider.maximum() / 100.0
        if new_scale < min_scale:
            new_scale = min_scale
        if new_scale > max_scale:
            new_scale = max_scale
        self.current_scale = new_scale
        self.slider.blockSignals(True)
        self.slider.setValue(int(self.current_scale * 100))
        self.slider.blockSignals(False)
        self.update_pixmap()
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position close button in top-right corner
        padding = 10
        self.close_btn.move(self.width() - self.close_btn.width() - padding, padding)

    def eventFilter(self, obj, event):
        if hasattr(self, "scroll") and obj is self.scroll.viewport():
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_active = True
                self._last_pos = event.position()
                self._velocity = QPoint(0, 0)
                self._inertia_timer.stop()
                self.scroll.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_active:
                new_pos = event.position()
                delta = new_pos - self._last_pos
                self._last_pos = new_pos
                hbar = self.scroll.horizontalScrollBar()
                vbar = self.scroll.verticalScrollBar()
                hbar.setValue(hbar.value() - int(delta.x()))
                vbar.setValue(vbar.value() - int(delta.y()))
                self._velocity = QPoint(int(delta.x()), int(delta.y()))
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and self._drag_active:
                self._drag_active = False
                self.scroll.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
                if self._velocity.manhattanLength() > 0:
                    self._inertia_timer.start()
                return True
        return super().eventFilter(obj, event)

    def apply_inertia(self):
        if self._velocity.manhattanLength() < 1:
            self._inertia_timer.stop()
            return
        hbar = self.scroll.horizontalScrollBar()
        vbar = self.scroll.verticalScrollBar()
        hbar.setValue(hbar.value() - self._velocity.x())
        vbar.setValue(vbar.value() - self._velocity.y())
        self._velocity.setX(int(self._velocity.x() * 0.9))
        self._velocity.setY(int(self._velocity.y() * 0.9))


class ResizableImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )

    def setPixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.update_display()

    def resizeEvent(self, event):
        self.update_display()
        super().resizeEvent(event)

    def update_display(self):
        if self.original_pixmap and not self.original_pixmap.isNull():
            scaled = self.original_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled)
        else:
            super().setPixmap(QPixmap())


from utils import resource_path

class HelperTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        self.downloaded_images = {}
        self.pending_frames = {}
        self.is_initialized = False
        
        # Pre-load images from assets
        # self.load_local_images() # Deferred loading

    def showEvent(self, event):
        if not self.is_initialized:
            QTimer.singleShot(0, self.init_data)
            self.is_initialized = True
        super().showEvent(event)
    
    def init_data(self):
        self.load_local_images()
        
        self.effect_questions = {
            "Ровные ли сегодня дороги?": (
                "Эффект: расход бензина уменьшается в 2 раза до рестарта.",
                "Эффект: расход бензина увеличивается в 2 раза до рестарта."
            ),
            "Уважают ли меня в моем клубе?": (
                "Эффект: х2 репутация за задания в клубах (кроме Эпсилон).",
                "Эффект: репутация за задания в клубах уменьшается в 2 раза."
            ),
            "На подработках сегодня хорошо платят?": (
                "Эффект: +25% зарплаты на функциональных работах.",
                "Эффект: зарплата на функциональных работах уменьшена на 25%."
            ),
            "Вкусно ли я сегодня поем?": (
                "Эффект: голод отключен до ближайшего рестарта сервера.",
                "Эффект: сытость один раз опускается до нуля."
            ),
            "Буду ли я сегодня внимателен?": (
                "Эффект: шанс выпадения семян и обезболивающих повышен.",
                "Эффект: шанс выпадения семян и обезболивающих снижен."
            ),
            "Крепкое ли сегодня оружие?": (
                "Эффект: износ оружия отключен до рестарта.",
                "Эффект: износ оружия увеличен в 2 раза."
            ),
            "Пойдет ли сегодня торговля?": (
                "Эффект: стоимость выставления объявлений на 5vito снижена на 20%.",
                "Эффект: стоимость выставления объявлений на 5vito повышена на 20%."
            ),
            "Сегодня хороший улов?": (
                "Эффект: мини-игра рыбалки упрощена на один кружок, но не меньше трёх.",
                "Эффект: мини-игра рыбалки усложнена на один кружок, но не больше шести."
            ),
            "Смена будет продуктивной?": (
                "Эффект: +25% к пейдею во фракции.",
                "Эффект: пейдей во фракции уменьшен на 25%."
            )
        }
        self.no_effect_questions = [
            "Сегодня - мой день?",
            "Всё ли предрешено?",
            "Мне повезет сегодня?",
            "Улыбнется ли мне случай?",
            "Меня ждет успех сегодня?",
            "Судьба услышит мой шепот?",
            "Есть ли смысл в сегодняшнем дне?",
            "Молчание - это знак?",
            "Я встречу нового друга сегодня?",
            "Стоит ли доверять интуиции?",
            "Видит ли кто-то, что вижу я?"
        ]
        saved_no_effect = self.main_window.data_manager.get_setting("orb_no_effect_questions", None)
        if isinstance(saved_no_effect, list) and saved_no_effect:
            self.no_effect_questions = saved_no_effect
        self.positive_answers = [
            "Да, звезды сегодня на вашей стороне.",
            "Да, все складывается в вашу пользу.",
            "Да, сегодня удачный день для этого.",
            "Да, ваши шансы сегодня выше обычного."
        ]
        self.negative_answers = [
            "Нет, сегодня лучше не рассчитывать на это.",
            "Нет, обстоятельства сегодня против вас.",
            "Нет, перенесите это на другой день.",
            "Нет, удача сегодня капризна."
        ]
        self.neutral_answers = [
            "Ответ неясен, попробуйте позже.",
            "Шар молчит, исход не определен.",
            "Сейчас нельзя дать точный ответ.",
            "Ничего не ясно, наблюдайте за событиями."
        ]

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        header = QLabel("Помощник")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(header)

        self.setup_tabs()

    def load_local_images(self):
        """Loads helper images from local assets."""
        image_map = {
            "Death": "Death.png",
            "Judgement": "Judgement.png",
            "Justice": "Justice.png",
            "Strength": "Strenght.png", 
            "Temperance": "Temperance.png",
            "The Chariot": "The%20Chariot.png",
            "The Devil": "The%20Devil.png",
            "The Emperor": "The%20Emperor.png",
            "The Empress": "The%20Empress.png",
            "The Fool": "The%20Fool.png",
            "The Hanged Man": "The%20Hanged%20Man.png",
            "The Hermit": "The%20Hermit.png",
            "The Hierophant": "The%20Hierophant.png",
            "The High Priestess": "The%20High%20Priestess.png",
            "The Lovers": "The%20Lovers.png",
            "The Magician": "The%20Magician.png",
            "The Moon": "The%20Moon.png",
            "The Star": "The%20Star.png",
            "The Sun": "The%20Sun.png",
            "The Tower": "The%20Tower.png",
            "The World": "The%20World.png",
            "Wheel of Fortune": "Wheel%20of%20Fortune.png",
            "med": "med.png",
            "ohota1": "ohota1.png",
            "ohota2": "ohota2.jpg",
            "klad1": "klad1.png",
            "klad2": "klad2.png"
        }

        for name, filename in image_map.items():
            clean_filename = filename.replace("%20", " ")
            asset_path = resource_path(os.path.join("assets", "tarot", clean_filename))
            
            found_path = None
            if os.path.exists(asset_path):
                found_path = asset_path
            else:
                # Fallback to check if it's in the data dir
                data_dir = os.path.dirname(self.data_manager.filename)
                local_path = os.path.join(data_dir, "images", "helper", clean_filename)
                if os.path.exists(local_path):
                     found_path = local_path
            
            if found_path:
                self.downloaded_images[name] = found_path
                # Update pending frames
                if name in self.pending_frames:
                    for lbl in self.pending_frames[name]:
                        try:
                            pix = QPixmap(found_path)
                            if not pix.isNull():
                                if isinstance(lbl, ResizableImageLabel):
                                    lbl.setPixmap(pix)
                                else:
                                    lbl.setPixmap(pix.scaled(QSize(400, 300), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                                lbl.setText("")
                                lbl.mousePressEvent = lambda e, p=found_path: self.show_image_zoom(p)
                        except Exception:
                            pass
                    # Clear pending frames for this key
                    del self.pending_frames[name]

    def ensure_remote_images_loaded(self):
        # Deprecated, using load_local_images
        pass
        t = StyleManager.get_theme(theme_name)
        
        self.setStyleSheet(f"background-color: {t['bg_main']}; color: {t['text_main']};")
        
        # Style Tab Widget
        self.sub_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {t['border']};
                background: {t['bg_secondary']};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background: {t['bg_tertiary']};
                color: {t['text_secondary']};
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {t['bg_secondary']};
                color: {t['accent']};
                font-weight: bold;
                border-bottom: 2px solid {t['accent']};
            }}
            QTabBar::tab:hover {{
                background: {t['bg_main']};
                color: {t['text_main']};
            }}
        """)
        
        # Helper method to style frames inside tabs
        def style_frame(frame):
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {t['bg_secondary']}; 
                    border-radius: 10px; 
                    border: 1px solid {t['border']};
                }}
            """)
            
            # Find labels inside and style them if needed
            for child in frame.findChildren(QLabel):
                if not child.objectName(): # Don't overwrite specific object names if any
                     child.setStyleSheet(f"color: {t['text_main']}; background: transparent; border: none;")

        # Update text edit styles
        for text_edit in self.findChildren(QTextEdit):
             text_edit.setStyleSheet(f"""
                background-color: {t['input_bg']};
                color: {t['text_main']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 10px;
             """)
             
        # Update buttons
        for btn in self.findChildren(QPushButton):
            if not btn.objectName(): # Default style
                # Determine color based on existing text or default to accent
                # But since we can't easily get intent here, we use accent for all generic buttons
                # For specific buttons (like Zoom +/-), we might want to be careful, but they usually have fixed sizes/icons
                
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {t['accent']};
                        border: 1px solid {t['accent']};
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: {t['accent']}1A;
                        color: {t['text_main']};
                    }}
                """)

    def setup_tabs(self):
        if hasattr(self, "sub_tabs"):
            self.layout.removeWidget(self.sub_tabs)
            self.sub_tabs.deleteLater()

        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(self.create_treasure_tab(), "Клад")
        self.sub_tabs.addTab(self.create_hunt_tab(), "Охота")
        self.sub_tabs.addTab(self.create_med_tab(), "Медпомощь")
        self.sub_tabs.addTab(self.create_tarot_tab(), "Карты Таро")
        self.sub_tabs.addTab(self.create_pets_tab(), "Питомцы")
        self.sub_tabs.addTab(self.create_orb_tab(), "Шар")
        self.layout.addWidget(self.sub_tabs)

    def create_treasure_tab(self):
        return self.create_two_image_widget("klad1", "klad2")

    def create_hunt_tab(self):
        return self.create_two_image_widget("ohota1", "ohota2")

    def create_two_image_widget(self, img1_key, img2_key):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        path1 = self.downloaded_images.get(img1_key)
        frame1 = self.create_image_frame(path1, img1_key)
        layout.addWidget(frame1)

        path2 = self.downloaded_images.get(img2_key)
        frame2 = self.create_image_frame(path2, img2_key)
        layout.addWidget(frame2)

        return widget

    def create_image_gallery_widget(self, storage_key):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        images = self.data_manager.get_global_data(storage_key, [])

        if images and len(images) == 2:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)

            container = QWidget()
            grid = QGridLayout(container)
            grid.setSpacing(15)
            grid.setContentsMargins(0, 0, 0, 0)

            for i, path in enumerate(images):
                frame = self.create_image_frame(path)
                grid.addWidget(frame, 0, i)

            container.setLayout(grid)
            scroll.setWidget(container)
            layout.addWidget(scroll)

            info = QLabel("Изображения загружены. Изменение невозможно.")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(info)
        else:
            info = QLabel("Для этого раздела необходимо загрузить ровно 2 изображения.")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info.setStyleSheet("font-size: 16px; margin-bottom: 20px;")
            layout.addWidget(info)

            btn = QPushButton("Загрузить изображения (2 шт)")
            btn.setFixedSize(250, 50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda: self.upload_images(storage_key))

            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(btn)
            btn_layout.addStretch()

            layout.addLayout(btn_layout)
            layout.addStretch()

        return widget

    def load_pixmap(self, path):
        if not path:
            return QPixmap()
            
        resolved = self.data_manager.resolve_image_path(path)
        pix = QPixmap()
        
        if resolved.startswith("data:image"):
            try:
                header, data = resolved.split(',', 1)
                b64_data = QByteArray.fromBase64(data.encode())
                pix.loadFromData(b64_data)
            except:
                pass
        else:
            pix.load(resolved)
            
        return pix

    def upload_images(self, storage_key):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите 2 изображения",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )

        if not files:
            return

        if len(files) != 2:
            QMessageBox.warning(self, "Ошибка", "Необходимо выбрать ровно 2 изображения!")
            return

        saved_paths = []
        for f in files:
            pixmap = QPixmap(f)
            if pixmap.isNull():
                QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать файл: {f}")
                return

            rel_path = self.data_manager.save_pixmap_image(pixmap)
            if rel_path:
                saved_paths.append(rel_path)
            else:
                QMessageBox.warning(self, "Ошибка", "Ошибка при сохранении файла")
                return

        self.data_manager.set_global_data(storage_key, saved_paths)
        self.setup_tabs()
        QMessageBox.information(self, "Успех", "Изображения успешно загружены!")

    def create_med_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        cheat_label = QLabel("Шпаргалка по медицинской помощи")
        cheat_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(cheat_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        cheat_text = QTextEdit()
        cheat_text.setReadOnly(True)
        cheat_text.setPlainText(
            "Основные шаги:\n"
            "1. Оцените обстановку и обеспечьте безопасность.\n"
            "2. Проверьте сознание и дыхание пострадавшего.\n"
            "3. Используйте аптечку, обезболивающие и перевязочные материалы.\n"
            "4. При тяжелых травмах вызовите EMS и оставайтесь рядом.\n"
            "5. Следите за таймерами кровотечения и откатов препаратов.\n\n"
            "Подсказки:\n"
            "• Сначала стабилизируйте состояние, затем перемещайте персонажа.\n"
            "• Не тратьте сильные препараты на легкие травмы.\n"
            "• Координируйтесь с напарниками по рации или голосовому чату."
        )
        content_layout.addWidget(cheat_text)

        # Image section
        path = self.downloaded_images.get("med")
        img_frame = self.create_image_frame(path, "med")
        content_layout.addWidget(img_frame)
        
        layout.addLayout(content_layout)

        return widget

    def refresh_all_data(self):
        # Refresh Med Tab
        self.update_med_image_display()
        
        # Refresh Tarot Tab
        self.tarot_images = self.data_manager.get_global_data("tarot_images", {})
        if hasattr(self, 'tarot_layout'):
            for i in range(self.tarot_layout.count()):
                item = self.tarot_layout.itemAt(i)
                if item and item.widget():
                    frame = item.widget()
                    # Find image label inside frame
                    # Structure: QVBoxLayout -> [QLabel (img), QLabel (name), QLabel (desc)]
                    # Image label is at index 0 in layout
                    frame_layout = frame.layout()
                    if frame_layout and frame_layout.count() > 0:
                        img_lbl = frame_layout.itemAt(0).widget()
                        if isinstance(img_lbl, QLabel):
                            # Find name to lookup image
                            name_lbl = frame_layout.itemAt(1).widget()
                            if isinstance(name_lbl, QLabel):
                                name = name_lbl.text()
                                path = getattr(self, 'downloaded_images', {}).get(name)
                                if not path:
                                    path = self.tarot_images.get(name)
                                
                                # Update image
                                if path:
                                    resolved = self.data_manager.resolve_image_path(path)
                                    pix = QPixmap(resolved)
                                    if not pix.isNull():
                                        img_lbl.setPixmap(pix.scaled(130, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                                        img_lbl.setText("")
                                        img_lbl.setStyleSheet("background-color: rgba(0,0,0,0.3); border-radius: 5px; border: 1px solid rgba(255,255,255,0.1);")
                                    else:
                                        img_lbl.setText("Ошибка")
                                else:
                                    img_lbl.setText("Добавить\nфото")
                                    img_lbl.setPixmap(QPixmap()) # Clear
                                    img_lbl.setStyleSheet("background-color: rgba(46, 204, 113, 0.2); border-radius: 5px; border: 1px dashed rgba(46, 204, 113, 0.5); color: #2ecc71;")

    def create_image_frame(self, path, key=None):
        frame = QFrame()
        frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1);")
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        
        img_lbl = ResizableImageLabel()
        img_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        
        pix = self.load_pixmap(path)
        if not pix.isNull():
            img_lbl.setPixmap(pix)
            
            # Click to zoom
            # We need to capture path correctly in lambda
            img_lbl.mousePressEvent = lambda e, p=path: self.show_image_zoom(p)
        else:
            img_lbl.setText("Ошибка") if path else img_lbl.setText("Загрузка...")
            if not path and key:
                if key not in self.pending_frames:
                    self.pending_frames[key] = []
                self.pending_frames[key].append(img_lbl)
            
        layout.addWidget(img_lbl)
        return frame

    def ensure_remote_images_loaded(self):
        """Downloads helper images to temp directory from GitHub asynchronously."""
        self.downloaded_images = {}
        self.pending_frames = {} # map: image_name -> list of (label, path) to update

        # Tarot images map
        image_map = {
            "Death": "Death.png",
            "Judgement": "Judgement.png",
            "Justice": "Justice.png",
            "Strength": "Strenght.png", 
            "Temperance": "Temperance.png",
            "The Chariot": "The%20Chariot.png",
            "The Devil": "The%20Devil.png",
            "The Emperor": "The%20Emperor.png",
            "The Empress": "The%20Empress.png",
            "The Fool": "The%20Fool.png",
            "The Hanged Man": "The%20Hanged%20Man.png",
            "The Hermit": "The%20Hermit.png",
            "The Hierophant": "The%20Hierophant.png",
            "The High Priestess": "The%20High%20Priestess.png",
            "The Lovers": "The%20Lovers.png",
            "The Magician": "The%20Magician.png",
            "The Moon": "The%20Moon.png",
            "The Star": "The%20Star.png",
            "The Sun": "The%20Sun.png",
            "The Tower": "The%20Tower.png",
            "The World": "The%20World.png",
            "Wheel of Fortune": "Wheel%20of%20Fortune.png",
            # New sections
            "med": "med.png",
            "ohota1": "ohota1.png",
            "ohota2": "ohota2.jpg",
            "klad1": "klad1.png",
            "klad2": "klad2.png"
        }

        # Use persistent storage instead of temp
        # This ensures images are available offline and portable if data dir is portable
        data_dir = os.path.dirname(self.data_manager.filename)
        images_dir = os.path.join(data_dir, "images", "helper")
        
        if not os.path.exists(images_dir):
            os.makedirs(images_dir, exist_ok=True)
            
        self.helper_temp_dir = images_dir 
        # atexit.register(self.cleanup_helper_images) # Don't delete images on exit
        
        # Check existing files first (fast sync check)
        for name, filename in image_map.items():
            local_filename = filename.replace("%20", " ")
            local_path = os.path.join(images_dir, local_filename)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                self.downloaded_images[name] = local_path

        # Start async downloader for missing or all files (to ensure integrity)
        self.downloader = ImageDownloaderWorker(image_map, images_dir)
        self.downloader.image_ready.connect(self.on_image_ready)
        self.downloader.start()

    def on_image_ready(self, name, path):
        self.downloaded_images[name] = path
        
        # Update any pending frames
        if name in self.pending_frames:
            for lbl in self.pending_frames[name]:
                try:
                    pix = QPixmap(path)
                    if not pix.isNull():
                         # Use ResizableImageLabel logic if it's one
                         if isinstance(lbl, ResizableImageLabel):
                             lbl.setPixmap(pix)
                         else:
                             # Fallback for standard labels (e.g. Tarot thumbnails if they use this)
                             lbl.setPixmap(pix.scaled(QSize(400, 300), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                         
                         lbl.setText("")
                         lbl.mousePressEvent = lambda e, p=path: self.show_image_zoom(p)
                except Exception:
                    pass
            del self.pending_frames[name]

    def cleanup_helper_images(self):
        if hasattr(self, 'helper_temp_dir') and os.path.exists(self.helper_temp_dir):
            try:
                shutil.rmtree(self.helper_temp_dir)
            except Exception:
                pass

    def create_tarot_tab(self):
        # self.ensure_remote_images_loaded() # Called in __init__
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        tarot_label = QLabel("Карты Таро")
        tarot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tarot_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(tarot_label)

        # Scroll Area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        self.tarot_layout = content_layout
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tarot_data = [
            ("Death", "Мгновенно убивает игрока."),
            ("Judgement", "Временный розыск."),
            ("Justice", "+1 $."),
            ("Strength", "+50 единиц к силе."),
            ("Temperance", "Настроение и сытость на 100%, но здоровье уменьшается."),
            ("The Chariot", "Временный буст скорости бега."),
            ("The Devil", "Временный поджог игрока без нанесения урона."),
            ("The Emperor", "Включает походку «размахивание руками»."),
            ("The Empress", "Включает походку «женская походка»."),
            ("The Fool", "Временный звук смеха."),
            ("The Hanged Man", "Временно исчезает тело, остаётся только голова на петле."),
            ("The Hermit", "×2 зарплата на начальных работах в течение 1 часа."),
            ("The Hierophant", "Здоровье 100%, но настроение и сытость падают до 0."),
            ("The High Priestess", "Кровотечение."),
            ("The Lovers", "Автофокус на игрока противоположного пола, которого нужно обнять или поцеловать."),
            ("The Magician", "Временно все находящиеся рядом игроки копируют вашу внешность."),
            ("The Moon", "Временно делает кожу белой."),
            ("The Star", "Подбрасывает игрока в воздух без урона."),
            ("The Sun", "Временно делает кожу тёмной."),
            ("The Tower", "Временно забирает наличные деньги."),
            ("The World", "Перемещает игрока в случайное место."),
            ("Wheel of Fortune", "Сбрасывает счётчик колеса удачи.")
        ]
        
        self.tarot_images = self.data_manager.get_global_data("tarot_images", {})
        
        for index, (name, desc) in enumerate(self.tarot_data):
            card_widget = self.create_tarot_card_widget(name, desc)
            row = index // 6
            col = index % 6
            content_layout.addWidget(card_widget, row, col)
            
        content_layout.setRowStretch(content_layout.rowCount(), 1)
        content_layout.setColumnStretch(content_layout.columnCount(), 1)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        return widget

    def create_tarot_card_widget(self, name, desc):
        frame = QFrame()
        frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1);")
        frame.setFixedWidth(140)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Image area
        img_lbl = QLabel()
        img_lbl.setFixedSize(130, 200)
        img_lbl.setStyleSheet("background-color: rgba(0,0,0,0.3); border-radius: 5px; border: 1px solid rgba(255,255,255,0.1);")
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        
        current_img_path = self.downloaded_images.get(name)
        if not current_img_path:
            current_img_path = self.tarot_images.get(name)
            
        if current_img_path:
            resolved = self.data_manager.resolve_image_path(current_img_path)
            pix = QPixmap(resolved)
            if not pix.isNull():
                img_lbl.setPixmap(pix.scaled(img_lbl.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                img_lbl.setStyleSheet("background-color: rgba(0,0,0,0.3); border-radius: 5px; border: 1px solid rgba(255,255,255,0.1);")
            else:
                img_lbl.setText("Ошибка")
        else:
            img_lbl.setText("Добавить\nфото")
            img_lbl.setStyleSheet("background-color: rgba(46, 204, 113, 0.2); border-radius: 5px; border: 1px dashed rgba(46, 204, 113, 0.5); color: #2ecc71;")
            
        # Click handler
        img_lbl.mousePressEvent = lambda e: self.handle_tarot_image_click(name, current_img_path)
        
        layout.addWidget(img_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Text area
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        
        layout.addWidget(name_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch()
        
        return frame

    def handle_tarot_image_click(self, card_name, current_path):
        is_admin = False
        if hasattr(self.main_window, "settings_tab"):
            is_admin = self.main_window.settings_tab.admin_authenticated
            
        if not current_path:
             # Anyone can add first time
             self.upload_tarot_image(card_name)
        else:
            # View or Edit
            if is_admin:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Действие")
                dlg.setText(f"Карта: {card_name}")
                view_btn = dlg.addButton("Просмотреть", QMessageBox.ButtonRole.ActionRole)
                change_btn = dlg.addButton("Изменить (Админ)", QMessageBox.ButtonRole.ActionRole)
                dlg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
                dlg.exec()
                
                if dlg.clickedButton() == view_btn:
                    self.show_image_zoom(current_path)
                elif dlg.clickedButton() == change_btn:
                    self.upload_tarot_image(card_name)
            else:
                # Just view
                self.show_image_zoom(current_path)

    def upload_tarot_image(self, card_name):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Выберите изображение для {card_name}",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
            
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
             QMessageBox.warning(self, "Ошибка", "Не удалось открыть изображение.")
             return
             
        rel_path = self.data_manager.save_pixmap_image(pixmap)
        if rel_path:
            self.tarot_images[card_name] = rel_path
            self.data_manager.set_global_data("tarot_images", self.tarot_images)
            
            # Preserve index
            current_index = self.sub_tabs.currentIndex()
            self.setup_tabs() # Refresh UI
            self.sub_tabs.setCurrentIndex(current_index)
            
    def show_image_zoom(self, path):
        pix = self.load_pixmap(path)
        if not pix.isNull():
            ImageZoomDialog(pix, self).exec()


    def create_pets_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Инструкция по дрессировке")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Горизонтальный контейнер для текста и таблицы
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # Левая часть: Текст
        training_text = QTextEdit()
        training_text.setReadOnly(True)
        training_text.setPlainText(
            "Алгоритм дрессировки:\n"
            "• Выбирайте одну команду и повторяйте ее до закрепления.\n"
            "• 4 успешных выполнения команды без ошибок дают +1% дрессировки.\n"
            "• После серии попыток делайте паузу, чтобы избежать снижения эффективности.\n\n"
            "Временные ограничения:\n"
            "• Рекомендуемый КД между интенсивными сессиями около 15 минут.\n"
            "• Следите за состоянием питомца и не перегружайте его."
        )
        content_layout.addWidget(training_text, 1)

        # Правая часть: Таблица
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        treats_label = QLabel("Таблица лакомств")
        treats_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(treats_label)

        treats_table = QTableWidget()
        treats_table.setColumnCount(2)
        treats_table.setHorizontalHeaderLabels(["Питомец", "Лакомство"])
        treats_data = [
            ("Собака", "Молодог"),
            ("Кошка", "Лакомкот"),
            ("Пума", "Лакомкот"),
            ("Пантера", "Лакомкот"),
            ("Крыса", "Лакомгрыз"),
            ("Кролик", "Лакомгрыз"),
            ("Свинья", "Умнисвин"),
            ("Обезьяна", "Похвалобез"),
        ]
        treats_table.setRowCount(len(treats_data))
        for row, (pet, treat) in enumerate(treats_data):
            treats_table.setItem(row, 0, QTableWidgetItem(pet))
            treats_table.setItem(row, 1, QTableWidgetItem(treat))
        header = treats_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        right_layout.addWidget(treats_table)
        content_layout.addWidget(right_panel, 1)

        layout.addLayout(content_layout)

        return widget

    def create_orb_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        # 1. Заголовок и кнопка Шара
        container = QFrame()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        self.orb_button = QPushButton("Шар")
        self.orb_button.setObjectName("OrbButton")
        self.orb_button.setFixedSize(100, 100)
        self.orb_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.orb_button.setStyleSheet(
            """
            QPushButton#OrbButton {
                background-color: transparent;
                color: #8e44ad;
                border-radius: 50px;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #8e44ad;
            }
            QPushButton#OrbButton:hover {
                background-color: rgba(142, 68, 173, 0.1);
            }
            QPushButton#OrbButton:pressed {
                background-color: rgba(142, 68, 173, 0.2);
            }
            """
        )
        self.orb_button.clicked.connect(self.roll_orb)

        self.orb_label = QLabel("Нажмите на шар, чтобы получить предсказание.")
        self.orb_label.setWordWrap(True)
        self.orb_label.setStyleSheet("font-size: 14px;")
        
        container_layout.addWidget(self.orb_button)
        container_layout.addWidget(self.orb_label, 1) # Stretch factor 1
        
        layout.addWidget(container)

        # 2. Таблицы с вопросами
        # Используем QScrollArea, так как таблиц много и они могут не влезть
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Таблица вопросов с эффектами
        lbl_effects = QLabel("Вопросы с активными эффектами")
        lbl_effects.setStyleSheet("font-size: 16px; font-weight: bold; color: #a29bfe;")
        content_layout.addWidget(lbl_effects)

        self.effect_table = QTableWidget()
        self.effect_table.setColumnCount(3)
        self.effect_table.setHorizontalHeaderLabels(["Вопрос", "Успешный прогноз", "Неудачный прогноз"])
        
        # Данные из запроса пользователя
        self.effect_questions_data = [
            ("Ровные ли сегодня дороги?", "Уменьшает расход бензина в 2 раза", "Увеличивает расход бензина в 2 раза"),
            ("Уважают ли меня в моем клубе?", "×2 репутация за задания (кроме эпсилон)", "Уменьшает репутацию в 2 раза"),
            ("На подработках сегодня хорошо платят?", "+25% зарплаты на функциональных работах", "-25% зарплаты на функциональных работах"),
            ("Вкусно ли я сегодня поем?", "Отключает голод до рестарта", "Опускает сытость до нуля 1 раз"),
            ("Буду ли я сегодня внимателен?", "Увеличивает шанс выпадения семян/обезбола", "Уменьшает шанс выпадения"),
            ("Крепкое ли сегодня оружие?", "Отключает износ оружия до рестарта", "Износ оружия в 2 раза больше"),
            ("Пойдет ли сегодня торговля?", "Скидка 20% на выставление на 5vito", "+20% к цене выставления"),
            ("Сегодня хороший улов?", "Облегчает рыбалку (-1 кружок, мин 3)", "Усложняет рыбалку (+1 кружок, макс 6)"),
            ("Смена будет продуктивной?", "+25% к пейдею во фракции", "-25% к пейдею во фракции"),
        ]
        
        self.effect_table.setRowCount(len(self.effect_questions_data))
        for i, (q, pos, neg) in enumerate(self.effect_questions_data):
            self.effect_table.setItem(i, 0, QTableWidgetItem(q))
            self.effect_table.setItem(i, 1, QTableWidgetItem(pos))
            self.effect_table.setItem(i, 2, QTableWidgetItem(neg))
            
        self.effect_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.effect_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.effect_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.effect_table.setMinimumHeight(350) # Чтобы было видно больше строк
        content_layout.addWidget(self.effect_table)

        # Таблица вопросов БЕЗ эффектов
        lbl_neutral = QLabel("Вопросы без эффектов")
        lbl_neutral.setStyleSheet("font-size: 16px; font-weight: bold; color: #a29bfe;")
        content_layout.addWidget(lbl_neutral)

        self.neutral_table = QTableWidget()
        self.neutral_table.setColumnCount(1)
        self.neutral_table.setHorizontalHeaderLabels(["Вопрос"])
        
        self.neutral_questions_data = [
            "Сегодня - мой день?", "Всё ли предрешено?", "Мне повезет сегодня?",
            "Улыбнется ли мне случай?", "Меня ждет успех сегодня?", "Судьба услышит мой шепот?",
            "Есть ли смысл в сегодняшнем дне?", "Молчание - это знак?",
            "Я встречу нового друга сегодня?", "Стоит ли доверять интуиции?",
            "Видит ли кто-то, что вижу я?"
        ]
        
        self.neutral_table.setRowCount(len(self.neutral_questions_data))
        for i, q in enumerate(self.neutral_questions_data):
            self.neutral_table.setItem(i, 0, QTableWidgetItem(q))
            
        self.neutral_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.neutral_table.setMinimumHeight(300)
        content_layout.addWidget(self.neutral_table)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        return widget

    def roll_orb(self):
        # Логика шара:
        # 1. Проверяем, был ли уже эффект сегодня (храним дату в настройках)
        # 2. Если был -> просто случайный ответ без эффекта
        # 3. Если не было -> 70% шанс на вопрос с эффектом, 30% на нейтральный
        
        today = datetime.now().strftime("%Y-%m-%d")
        last_effect_date = self.data_manager.get_global_data("orb_last_effect_date", "")
        
        has_effect_today = (last_effect_date == today)
        
        # Списки ответов шара
        positive_answers = ["Да, безусловно.", "Звёзды говорят да.", "Перспективы хорошие.", "Вам повезёт."]
        negative_answers = ["Нет, не сегодня.", "Звёзды не благосклонны.", "Вряд ли.", "Ответ отрицательный."]
        neutral_answers = ["Туманное будущее.", "Спросите позже.", "Сейчас неясно.", "Шар молчит."]

        # Выбираем категорию вопроса
        if has_effect_today:
             # Эффект уже был, выбираем ТОЛЬКО нейтральные вопросы или говорим что эффект уже получен
             # Но по логике игры шар всё равно может выдавать вопросы, просто эффекты не накладываются повторно.
             # Для простоты: если эффект был, мы просто рандомим любой вопрос, но пишем "Эффект: Уже получен сегодня"
             is_effect_roll = False 
        else:
             # 70% шанс на вопрос с эффектом
             is_effect_roll = (random.random() < 0.7)

        result_question = ""
        result_answer = ""
        result_effect_desc = ""
        
        if is_effect_roll:
            # Выбираем вопрос с эффектом
            q_data = random.choice(self.effect_questions_data)
            result_question = q_data[0]
            
            # 50/50 успех или неудача
            is_success = (random.random() < 0.5)
            
            if is_success:
                result_answer = random.choice(positive_answers)
                result_effect_desc = f"Эффект (УСПЕХ): {q_data[1]}"
                # Записываем, что эффект получен
                self.data_manager.set_global_data("orb_last_effect_date", today)
            else:
                result_answer = random.choice(negative_answers)
                result_effect_desc = f"Эффект (НЕУДАЧА): {q_data[2]}"
                # Неудачный эффект тоже считается "эффектом" на сегодня? Обычно да.
                self.data_manager.set_global_data("orb_last_effect_date", today)
        else:
            # Нейтральный вопрос
            if random.random() < 0.5:
                # Берем из списка нейтральных
                result_question = random.choice(self.neutral_questions_data)
                result_effect_desc = "Без игрового эффекта."
            else:
                 # Или берем вопрос с эффектом, но говорим что эффект не сработал (если уже был сегодня)
                 q_data = random.choice(self.effect_questions_data)
                 result_question = q_data[0]
                 if has_effect_today:
                     result_effect_desc = "Эффект уже был получен сегодня."
                 else:
                     # Это ветка "30% шанс на нейтральный вопрос", но выпал вопрос из списка эффектов?
                     # Давайте упростим: если выпал нейтральный ролл, берем нейтральный вопрос.
                     result_question = random.choice(self.neutral_questions_data)
                     result_effect_desc = "Без игрового эффекта."

            result_answer = random.choice(positive_answers + negative_answers + neutral_answers)

        # Формируем текст
        final_text = (
            f"Вопрос: {result_question}\n"
            f"Ответ шара: {result_answer}\n"
            f"----------- \n"
            f"{result_effect_desc}"
        )
        
        self.orb_label.setText(final_text)

    def get_orb_answer_with_question(self, questions_effect, questions_neutral):
        pass

    def delete_selected_neutral_question(self):
        pass

    def apply_theme(self, theme_name):
        if theme_name == "light":
            text_color = "#2d3436"
        else:
            text_color = "#eceff4"
            
        if hasattr(self, "orb_label"):
            self.orb_label.setStyleSheet(f"font-size: 14px; color: {text_color};")

    def refresh_data(self):
        pass
