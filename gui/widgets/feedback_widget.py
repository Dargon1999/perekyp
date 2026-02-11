from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, 
    QCheckBox, QFileDialog, QProgressBar, QMessageBox, QComboBox, QFrame, QGraphicsOpacityEffect,
    QScrollArea, QSizePolicy, QGridLayout, QToolButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect
from PyQt6.QtGui import QColor, QIcon, QMovie
import requests
import json
import os
import platform
import time
import sys
import logging
from datetime import datetime, timezone

# Worker for Async Feedback Sending (Unchanged logic, improved error handling)
class FeedbackWorker(QThread):
    finished = pyqtSignal(bool, str, int) # success, message, status_code

    def __init__(self, api_url, token, data, screenshot_path=None):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.data = data
        self.screenshot_path = screenshot_path

    def run(self):
        retries = 3
        delay = 1
        
        # Prepare Discord Payload
        try:
            tech_data = json.loads(self.data.get("technical_data", "{}"))
            tech_str = "\n".join([f"**{k}:** {v}" for k, v in tech_data.items()])
            
            payload = {
                "embeds": [{
                    "title": f"Feedback: {self.data.get('topic', 'General')}",
                    "description": self.data.get("message", ""),
                    "color": 3447003, # Blue
                    "fields": [
                        {"name": "Technical Data", "value": tech_str if tech_str else "None", "inline": False},
                        {"name": "Contact", "value": f"Name: {self.data.get('name')}", "inline": False}
                    ],
                    "footer": {
                        "text": f"MoneyTracker V8 • {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }]
            }
        except Exception as e:
            payload = {"content": f"Error formatting payload: {e}"}

        # Prepare Files
        files = None
        data_kwargs = {}
        
        if self.screenshot_path and os.path.exists(self.screenshot_path):
            try:
                files = {
                    'file': (os.path.basename(self.screenshot_path), open(self.screenshot_path, 'rb'))
                }
                data_kwargs = {
                    'data': {'payload_json': json.dumps(payload)},
                    'files': files
                }
            except Exception as e:
                logging.error(f"Failed to attach file: {e}")
                data_kwargs = {'json': payload}
        else:
            data_kwargs = {'json': payload}

        for attempt in range(retries):
            try:
                headers = {
                    "User-Agent": "MoneyTracker/V8 (Discord Webhook)"
                }
                if not files:
                    headers["Content-Type"] = "application/json"
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    timeout=30,
                    **data_kwargs
                )
                
                if files:
                    files['file'][1].close()
                
                if 200 <= response.status_code < 300:
                    self.finished.emit(True, "Отзыв успешно отправлен!", response.status_code)
                    return
                elif response.status_code == 429:
                    retry_after = response.json().get('retry_after', delay)
                    time.sleep(float(retry_after))
                    continue
                elif 500 <= response.status_code < 600:
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay *= 2 
                        continue
                    else:
                        self.finished.emit(False, f"Ошибка сервера: {response.status_code}", response.status_code)
                        return
                else:
                    self.finished.emit(False, f"Ошибка: {response.status_code}", response.status_code)
                    return

            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    self.finished.emit(False, "Ошибка сети. Проверьте интернет.", 0)
                    return
            except Exception as e:
                self.finished.emit(False, f"Внутренняя ошибка: {str(e)}", 0)
                return

class FeedbackHistoryItem(QFrame):
    def __init__(self, data, theme, parent=None):
        super().__init__(parent)
        self.data = data
        self.theme = theme
        self.is_expanded = False
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(8)
        
        self.apply_theme(self.theme)

        # Header: Topic + Date
        header = QHBoxLayout()
        self.topic_lbl = QLabel(self.data.get('topic', 'Без темы'))
        self.topic_lbl.setStyleSheet(f"font-weight: bold; color: {self.theme['text_main']}; font-size: 14px;")
        
        self.date_lbl = QLabel(self.data.get('date', ''))
        self.date_lbl.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: 11px;")
        
        header.addWidget(self.topic_lbl)
        header.addStretch()
        header.addWidget(self.date_lbl)
        self.layout.addLayout(header)

        # Message Text
        self.msg_lbl = QLabel(self.data.get('message', ''))
        self.msg_lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 13px;")
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Initial check for length
        full_text = self.data.get('message', '')
        if len(full_text) > 80:
            self.msg_lbl.setText(full_text[:80] + "...")
            self.has_more = True
        else:
            self.has_more = False
            
        self.layout.addWidget(self.msg_lbl)

        # Expand Button
        if self.has_more:
            self.expand_btn = QPushButton("Показать")
            self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update_btn_style()
            self.expand_btn.clicked.connect(self.toggle_expand)
            self.layout.addWidget(self.expand_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        full_text = self.data.get('message', '')
        
        if self.is_expanded:
            self.msg_lbl.setText(full_text)
            self.expand_btn.setText("Свернуть")
        else:
            self.msg_lbl.setText(full_text[:80] + "...")
            self.expand_btn.setText("Показать")

    def update_btn_style(self):
        if hasattr(self, 'expand_btn'):
            self.expand_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {self.theme['accent']};
                    border: none;
                    text-align: left;
                    font-weight: bold;
                    background: transparent;
                    padding: 0;
                }}
                QPushButton:hover {{
                    text-decoration: underline;
                }}
            """)

    def apply_theme(self, theme):
        self.theme = theme
        self.setStyleSheet(f"""
            FeedbackHistoryItem {{
                background-color: {self.theme['input_bg']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
            }}
        """)
        if hasattr(self, 'topic_lbl'):
            self.topic_lbl.setStyleSheet(f"font-weight: bold; color: {self.theme['text_main']}; font-size: 14px;")
        if hasattr(self, 'date_lbl'):
            self.date_lbl.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: 11px;")
        if hasattr(self, 'msg_lbl'):
            self.msg_lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 13px;")
        self.update_btn_style()

class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.toggle_animation = QParallelAnimationGroup(self)
        self.content_area = QScrollArea(maximumHeight=0, minimumHeight=0)
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)

        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.toggle_animation.addAnimation(self.animation)

    def on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if not checked else Qt.ArrowType.RightArrow)
        self.toggle_button.setChecked(not checked)
        self.animation.setDirection(
            QPropertyAnimation.Direction.Forward if not checked else QPropertyAnimation.Direction.Backward
        )
        self.animation.setStartValue(0)
        self.animation.setEndValue(300) # Max height for history
        self.animation.start()

    def set_content_layout(self, layout):
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)

class FeedbackWidget(QWidget):
    def __init__(self, data_manager, auth_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.auth_manager = auth_manager
        self.api_url = "https://discord.com/api/webhooks/1467522942718972087/hM8IIiKwxUlXeio0IgIDo6iesRq_iwF2Og35w0jM7igTafQ_4OIroCSb4IjGnKxMLwo2"
        self.last_sent_time = 0
        self.screenshot_path = None
        self.history_items = []
        
        self.setup_ui()
        self.load_history()
        
        # Initial Animation
        self.setWindowOpacity(0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

    def setup_ui(self):
        # Main Layout (No global scroll to fit screen)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # 1. Header
        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.setSpacing(5)
        
        self.title_lbl = QLabel("Связь")
        self.title_lbl.setStyleSheet("font-size: 26px; font-weight: bold;")
        
        self.subtitle_lbl = QLabel("Мы ценим ваше мнение! Сообщите об ошибке или предложите идею.")
        self.subtitle_lbl.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        self.subtitle_lbl.setWordWrap(True)
        
        header_layout.addWidget(self.title_lbl)
        header_layout.addWidget(self.subtitle_lbl)
        self.main_layout.addWidget(self.header_frame)

        # 2. Form Area (Grid Layout for compactness)
        self.form_frame = QFrame()
        self.form_frame.setObjectName("FeedbackForm")
        self.form_layout = QGridLayout(self.form_frame)
        self.form_layout.setContentsMargins(25, 25, 25, 25)
        self.form_layout.setSpacing(20)
        
        # Name Input
        self.name_label = QLabel("Ваше имя")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Иван Иванов")
        self.name_input.setMinimumHeight(45)
        
        # Topic Input
        self.topic_label = QLabel("Тема сообщения")
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("Баг, Идея, Вопрос...")
        self.topic_input.setMinimumHeight(45)
        
        # Grid placement: Row 0 (Labels), Row 1 (Inputs)
        self.form_layout.addWidget(self.name_label, 0, 0)
        self.form_layout.addWidget(self.topic_label, 0, 1)
        self.form_layout.addWidget(self.name_input, 1, 0)
        self.form_layout.addWidget(self.topic_input, 1, 1)
        
        # Message Input
        self.msg_label = QLabel("Текст сообщения")
        self.msg_input = QTextEdit()
        self.msg_input.setPlaceholderText("Подробно опишите ситуацию...")
        self.msg_input.setMinimumHeight(120)
        self.msg_input.setStyleSheet("border-radius: 8px; padding: 12px; font-size: 14px;")
        self.msg_input.textChanged.connect(self.update_char_count)
        
        self.form_layout.addWidget(self.msg_label, 2, 0, 1, 2)
        self.form_layout.addWidget(self.msg_input, 3, 0, 1, 2)
        
        # Attachment
        self.attach_layout = QHBoxLayout()
        self.attach_btn = QPushButton(" 📎 Прикрепить скриншот")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setFixedWidth(200)
        self.attach_btn.clicked.connect(self.browse_file)
        
        self.file_lbl = QLabel("")
        self.file_lbl.setStyleSheet("color: #7f8c8d; font-style: italic; margin-left: 10px;")
        
        self.attach_layout.addWidget(self.attach_btn)
        self.attach_layout.addWidget(self.file_lbl)
        self.attach_layout.addStretch()
        
        self.form_layout.addLayout(self.attach_layout, 4, 0, 1, 2)
        
        self.main_layout.addWidget(self.form_frame)

        # 3. History (Collapsible)
        self.history_box = CollapsibleBox("История ваших обращений")
        self.history_content = QWidget()
        self.history_list_layout = QVBoxLayout(self.history_content)
        self.history_list_layout.setContentsMargins(10, 10, 10, 10)
        self.history_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.history_box.content_area.setWidget(self.history_content)
        self.history_box.content_area.setWidgetResizable(True)
        
        self.main_layout.addWidget(self.history_box)

        # 4. Spacer to push footer down
        self.main_layout.addStretch()

        # 5. Footer (Status & Action)
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 10, 0, 0)
        
        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setVisible(False)
        
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0) # Infinite loading
        self.loading_bar.setFixedWidth(150)
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("QProgressBar { height: 4px; border: none; background: #e0e0e0; } QProgressBar::chunk { background: #3498db; }")
        
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setMinimumHeight(50)
        self.send_btn.setMinimumWidth(180)
        self.send_btn.clicked.connect(self.send_feedback)
        
        self.footer_layout.addWidget(self.status_lbl)
        self.footer_layout.addWidget(self.loading_bar)
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.send_btn)
        
        self.main_layout.addLayout(self.footer_layout)

        # Initial validation state
        self.update_char_count()

    def resizeEvent(self, event):
        # Responsive Layout: Stack inputs if width is small
        width = event.size().width()
        if width < 600:
            # Switch to vertical stacking
            self.form_layout.addWidget(self.name_label, 0, 0, 1, 2)
            self.form_layout.addWidget(self.name_input, 1, 0, 1, 2)
            self.form_layout.addWidget(self.topic_label, 2, 0, 1, 2)
            self.form_layout.addWidget(self.topic_input, 3, 0, 1, 2)
            self.form_layout.addWidget(self.msg_label, 4, 0, 1, 2)
            self.form_layout.addWidget(self.msg_input, 5, 0, 1, 2)
            self.form_layout.addLayout(self.attach_layout, 6, 0, 1, 2)
        else:
            # Restore grid
            self.form_layout.addWidget(self.name_label, 0, 0)
            self.form_layout.addWidget(self.topic_label, 0, 1)
            self.form_layout.addWidget(self.name_input, 1, 0)
            self.form_layout.addWidget(self.topic_input, 1, 1)
            self.form_layout.addWidget(self.msg_label, 2, 0, 1, 2)
            self.form_layout.addWidget(self.msg_input, 3, 0, 1, 2)
            self.form_layout.addLayout(self.attach_layout, 4, 0, 1, 2)
            
        super().resizeEvent(event)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 8:
                self.show_status("Файл слишком большой (>8MB)", False)
                return
            self.screenshot_path = file_path
            self.file_lbl.setText(os.path.basename(file_path))
            self.attach_btn.setText(" 📷 Фото выбрано")
            self.attach_btn.setStyleSheet(f"background-color: {self.current_theme['success']}20; border: 1px solid {self.current_theme['success']}; color: {self.current_theme['success']};")
        else:
            self.screenshot_path = None
            self.file_lbl.setText("")
            self.attach_btn.setText(" 📎 Прикрепить скриншот")
            self.apply_theme(self.current_theme) # Restore style

    def update_char_count(self):
        text = self.msg_input.toPlainText()
        count = len(text)
        if count < 5:
            self.send_btn.setEnabled(False)
            self.send_btn.setToolTip("Минимум 5 символов")
        elif count > 2000:
            self.send_btn.setEnabled(False)
            self.send_btn.setToolTip("Максимум 2000 символов")
        else:
            self.send_btn.setEnabled(True)
            self.send_btn.setToolTip("")

    def get_technical_data(self):
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "python": sys.version.split()[0],
            "app_ver": "8.1.2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

    def send_feedback(self):
        # 1. Rate Limit
        now = time.time()
        if now - self.last_sent_time < 10:
            self.show_status(f"Подождите {int(10 - (now - self.last_sent_time))} сек.", False)
            return

        # 2. Validation
        name = self.name_input.text().strip()
        topic = self.topic_input.text().strip()
        text = self.msg_input.toPlainText().strip()
        
        if not name:
            self.name_input.setFocus()
            self.show_status("Пожалуйста, представьтесь", False)
            return
        if not topic:
            self.topic_input.setFocus()
            self.show_status("Укажите тему обращения", False)
            return
        if len(text) < 5:
            self.msg_input.setFocus()
            self.show_status("Текст сообщения слишком короткий", False)
            return

        # 3. Loading State
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Отправка...")
        self.loading_bar.setVisible(True)
        self.show_status("Соединение с сервером...", True, is_loading=True)

        # 4. Prepare Data
        data = {
            "topic": topic,
            "message": text,
            "name": name,
            "technical_data": json.dumps(self.get_technical_data())
        }
        
        token = "dummy_jwt_token"
        if self.auth_manager and hasattr(self.auth_manager, 'get_token'):
            token = self.auth_manager.get_token() or "dummy_jwt_token"

        # 5. Worker
        self.worker = FeedbackWorker(self.api_url, token, data, self.screenshot_path)
        self.worker.finished.connect(self.on_send_finished)
        self.worker.start()

    def on_send_finished(self, success, message, code):
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Отправить")
        self.loading_bar.setVisible(False)
        
        if success:
            # Add to history
            new_item = {
                "topic": self.topic_input.text(),
                "message": self.msg_input.toPlainText(),
                "name": self.name_input.text(),
                "date": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            self.history_data.append(new_item)
            self.save_history()
            self.add_history_item(new_item)

            self.last_sent_time = time.time()
            self.msg_input.clear()
            self.topic_input.clear()
            self.screenshot_path = None
            self.file_lbl.setText("")
            self.attach_btn.setText(" 📎 Прикрепить скриншот")
            
            # Show success in status
            self.show_status("Сообщение успешно отправлено!", True)
            
            # Show popup notification
            QMessageBox.information(self, "Успех", "Ваше сообщение успешно отправлено!\nМы рассмотрим его в ближайшее время.")
            
        else:
            self.show_status(message, False)

    def show_status(self, text, success, is_loading=False):
        self.status_lbl.setVisible(True)
        self.status_lbl.setText(text)
        
        # Fade In
        effect = QGraphicsOpacityEffect(self.status_lbl)
        self.status_lbl.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()
        self.status_anim = anim
        
        t = self.current_theme
        if is_loading:
            self.status_lbl.setStyleSheet(f"color: {t['accent']}; font-weight: bold;")
        elif success:
            self.status_lbl.setStyleSheet(f"color: {t['success']}; font-weight: bold;")
        else:
            self.status_lbl.setStyleSheet(f"color: {t['danger']}; font-weight: bold;")

    def apply_theme(self, t):
        self.current_theme = t
        self.setStyleSheet(f"background-color: transparent;")
        
        # Header
        self.title_lbl.setStyleSheet(f"color: {t['text_main']}; font-size: 26px; font-weight: bold;")
        self.subtitle_lbl.setStyleSheet(f"color: {t['text_secondary']}; font-size: 14px;")
        
        # Form Frame
        self.form_frame.setStyleSheet(f"""
            #FeedbackForm {{
                background-color: {t['bg_secondary']}80; 
                border: 1px solid {t['border']};
                border-radius: 16px;
            }}
            QLabel {{ color: {t['text_main']}; font-weight: 600; font-size: 14px; }}
        """)
        
        # Inputs
        input_style = f"""
            QLineEdit, QTextEdit {{
                border: 1px solid {t['border']};
                border-radius: 8px;
                background-color: {t['input_bg']};
                color: {t['text_main']};
                padding: 12px;
                font-size: 14px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {t['accent']};
                background-color: {t['input_bg']};
            }}
        """
        self.setStyleSheet(self.styleSheet() + input_style)
        
        # Attachment Button
        self.attach_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['bg_tertiary']};
                color: {t['text_main']};
                border: 1px dashed {t['border']};
                border-radius: 8px;
                padding: 10px;
                text-align: left;
            }}
            QPushButton:hover {{
                border: 1px dashed {t['accent']};
                color: {t['accent']};
            }}
        """)
        
        # History Box
        self.history_box.toggle_button.setStyleSheet(f"""
            QToolButton {{
                color: {t['accent']};
                font-size: 14px;
                border: none;
                background: transparent;
            }}
            QToolButton:hover {{
                text-decoration: underline;
            }}
        """)
        
        # Send Button
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['accent']};
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background-color: {t['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {t['accent_pressed']};
            }}
            QPushButton:disabled {{
                background-color: {t['bg_tertiary']};
                color: {t['text_secondary']};
            }}
        """)
        
        # Update history items
        for item in self.history_items:
            item.apply_theme(t)

    def load_history(self):
        self.history_data = []
        if self.data_manager:
            self.history_data = self.data_manager.get_global_data("feedback_history", [])
        
        # Sort by date desc
        for item in reversed(self.history_data):
            self.add_history_item(item)

    def save_history(self):
        if self.data_manager:
            self.data_manager.set_global_data("feedback_history", self.history_data)
            self.data_manager.save_data()

    def add_history_item(self, data):
        if not hasattr(self, 'current_theme'):
             self.current_theme = {
                'input_bg': '#ffffff', 'border': '#cccccc', 
                'text_main': '#000000', 'text_secondary': '#666666', 
                'accent': '#3498db', 'bg_secondary': '#f0f0f0', 'bg_tertiary': '#e0e0e0',
                'accent_hover': '#2980b9', 'accent_pressed': '#1f618d', 'success': '#2ecc71', 'danger': '#e74c3c'
             }

        item_widget = FeedbackHistoryItem(data, self.current_theme)
        self.history_list_layout.insertWidget(0, item_widget)
        self.history_items.append(item_widget)
