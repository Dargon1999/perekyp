from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, 
    QCheckBox, QFileDialog, QProgressBar, QMessageBox, QComboBox, QFrame, QGraphicsOpacityEffect,
    QScrollArea, QSizePolicy, QGridLayout, QToolButton, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect
from PyQt6.QtGui import QColor, QIcon, QMovie, QPixmap, QDragEnterEvent, QDropEvent
import requests
import json
import os
import platform
import time
import sys
import logging
from datetime import datetime, timezone
from PIL import Image
import io

# Worker for Async SMS Sending with Detailed Status
class SMSWorker(QThread):
    finished = pyqtSignal(bool, str, dict) # success, error_msg, response_data
    status_update = pyqtSignal(str, str) # step_name, status_text

    def __init__(self, phone, message):
        super().__init__()
        self.phone = phone
        self.message = message

    def run(self):
        try:
            self.status_update.emit("Инициализация", "Подготовка данных...")
            time.sleep(1) # Simulate
            
            self.status_update.emit("Соединение", "Подключение к шлюзу...")
            time.sleep(1.5)
            
            # Simulated Webhook call (using the provided Discord webhook as a mock SMS gateway)
            webhook_url = "https://discord.com/api/webhooks/1467522942718972087/hM8IIiKwxUlXeio0IgIDo6iesRq_iwF2Og35w0jM7igTafQ_4OIroCSb4IjGnKxMLwo2"
            
            payload = {
                "embeds": [{
                    "title": "📱 Исходящее SMS",
                    "fields": [
                        {"name": "Номер", "value": self.phone, "inline": True},
                        {"name": "Сообщение", "value": self.message, "inline": False}
                    ],
                    "color": 3447003,
                    "footer": {"text": f"MoneyTracker SMS Gateway • {datetime.now().strftime('%H:%M:%S')}"}
                }]
            }
            
            self.status_update.emit("Отправка", "Передача сообщения...")
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code < 300:
                self.status_update.emit("Доставка", "Доставлено абоненту ✅")
                self.finished.emit(True, "", {"code": response.status_code, "op": "OK"})
            else:
                self.status_update.emit("Ошибка", f"Ошибка шлюза: {response.status_code}")
                self.finished.emit(False, f"Ошибка API: {response.status_code}", {})
                
        except Exception as e:
            self.status_update.emit("Сбой", "Ошибка сети")
            self.finished.emit(False, str(e), {})

class SMSPreviewDialog(QDialog):
    def __init__(self, phone, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предпросмотр сообщения")
        self.setFixedWidth(350)
        self.setStyleSheet("background-color: #1e293b; color: white; border-radius: 10px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Проверьте данные перед отправкой:")
        title.setStyleSheet("font-weight: bold; color: #3b82f6;")
        layout.addWidget(title)
        
        info_box = QFrame()
        info_box.setStyleSheet("background-color: #0f172a; padding: 15px; border-radius: 8px;")
        info_lay = QVBoxLayout(info_box)
        
        phone_lbl = QLabel(f"<b>Кому:</b> {phone}")
        msg_lbl = QLabel(f"<b>Текст:</b><br>{message}")
        msg_lbl.setWordWrap(True)
        
        info_lay.addWidget(phone_lbl)
        info_lay.addWidget(msg_lbl)
        layout.addWidget(info_box)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Отправить")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

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
        
        # Initial Animation
        self.setWindowOpacity(0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 🌟 Header Section
        self.header_card = QFrame()
        self.header_card.setObjectName("HeaderCard")
        self.header_card.setStyleSheet("""
            #HeaderCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1c2c, stop:1 #4a192c);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        header_layout = QHBoxLayout(self.header_card)
        header_layout.setContentsMargins(25, 25, 25, 25)
        
        icon_lbl = QLabel("📬")
        icon_lbl.setStyleSheet("font-size: 45px;")
        header_layout.addWidget(icon_lbl)
        
        title_box = QVBoxLayout()
        self.title_lbl = QLabel("Связь и SMS")
        self.title_lbl.setStyleSheet("font-size: 24px; font-weight: 800; color: #ffffff;")
        title_box.addWidget(self.title_lbl)
        
        self.subtitle_lbl = QLabel("Отправляйте сообщения напрямую через наш SMS-шлюз")
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #cbd5e1;")
        title_box.addWidget(self.subtitle_lbl)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        # Connection Status Indicator
        status_box = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #10b981; font-size: 20px; margin-right: 5px;")
        self.status_text = QLabel("Шлюз активен")
        self.status_text.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px;")
        
        status_box.addWidget(self.status_dot)
        status_box.addWidget(self.status_text)
        header_layout.addLayout(status_box)
        
        self.main_layout.addWidget(self.header_card)

        # 📱 SMS Form Section
        self.sms_card = QFrame()
        self.sms_card.setObjectName("SMSCard")
        self.sms_card.setStyleSheet("""
            #SMSCard {
                background-color: #1e293b;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        sms_layout = QVBoxLayout(self.sms_card)
        sms_layout.setSpacing(15)

        # Source and Type Selection
        type_source_layout = QHBoxLayout()
        
        # 1. Ticket Type (Required)
        type_source_layout.addWidget(QLabel("<b>Тип обращения:</b>"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Выберите тип...", "Вопрос", "Баг", "Предложение по улучшению"])
        self.type_combo.setMinimumWidth(180)
        type_source_layout.addWidget(self.type_combo)
        
        type_source_layout.addSpacing(20)
        
        # 2. Source (Optional)
        type_source_layout.addWidget(QLabel("<b>Источник:</b>"))
        self.source_combo = QComboBox()
        self.source_combo.setEditable(True)
        self.source_combo.addItems(["", "Discord", "SMS", "E-mail", "Форум"])
        self.source_combo.setPlaceholderText("Напр. Discord")
        self.source_combo.setToolTip("Необязательно. Примеры: Discord, SMS, E-mail, Форум")
        self.source_combo.setFixedWidth(120)
        type_source_layout.addWidget(self.source_combo)
        
        type_source_layout.addStretch()
        
        self.avatar_lbl = QLabel("👤")
        self.avatar_lbl.setFixedSize(32, 32)
        self.avatar_lbl.setStyleSheet("background-color: #334155; border-radius: 16px; font-size: 18px;")
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_source_layout.addWidget(self.avatar_lbl)
        
        sms_layout.addLayout(type_source_layout)

        # Input Rows
        form_grid = QGridLayout()
        form_grid.setSpacing(15)

        # 3. Sender Field (Auto-detected or List/Manual)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("� От кого (Имя / Контакт)")
        self.phone_input.setMinimumHeight(45)
        
        # Auto-detect sender
        self.detect_sender()

        self.sms_msg_input = QTextEdit()
        self.sms_msg_input.setPlaceholderText("💬 Введите текст сообщения...")
        self.sms_msg_input.setMinimumHeight(100)
        self.sms_msg_input.setAccessibleName("Ввод текста сообщения")

        form_grid.addWidget(QLabel("<b>От кого:</b>"), 0, 0)
        form_grid.addWidget(self.phone_input, 0, 1)
        form_grid.addWidget(QLabel("<b>Текст:</b>"), 1, 0, Qt.AlignmentFlag.AlignTop)
        form_grid.addWidget(self.sms_msg_input, 1, 1)
        
        sms_layout.addLayout(form_grid)
        
        # Image Attachment Area (Drag and Drop)
        self.attach_area = QFrame()
        self.attach_area.setAcceptDrops(True)
        self.attach_area.setMinimumHeight(60)
        self.attach_area.setStyleSheet("""
            QFrame {
                border: 2px dashed #334155;
                border-radius: 10px;
                background-color: #0f172a;
            }
            QFrame:hover {
                border-color: #3b82f6;
            }
        """)
        attach_lay = QHBoxLayout(self.attach_area)
        self.attach_lbl = QLabel("Перетащите фото сюда или нажмите для выбора (JPG/PNG/GIF, до 2МБ)")
        self.attach_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        self.attach_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        attach_lay.addWidget(self.attach_lbl)
        
        # Overload drag/drop for attach_area
        self.attach_area.dragEnterEvent = self.on_drag_enter
        self.attach_area.dropEvent = self.on_drop
        self.attach_area.mousePressEvent = lambda e: self.browse_attachment()
        
        sms_layout.addWidget(self.attach_area)
        
        # Preview for attached image
        self.img_preview = QLabel()
        self.img_preview.setFixedHeight(100)
        self.img_preview.setVisible(False)
        self.img_preview.setStyleSheet("border-radius: 8px; border: 1px solid #334155;")
        sms_layout.addWidget(self.img_preview)

        # Status Block
        self.sms_status_box = QFrame()
        self.sms_status_box.setStyleSheet("background-color: #0f172a; border-radius: 10px; padding: 10px;")
        self.sms_status_box.setVisible(False)
        status_lay = QVBoxLayout(self.sms_status_box)
        
        self.status_steps = QLabel("Ожидание отправки...")
        self.status_steps.setStyleSheet("color: #94a3b8; font-family: Consolas; font-size: 12px;")
        status_lay.addWidget(self.status_steps)
        sms_layout.addWidget(self.sms_status_box)

        # Actions Row
        self.send_sms_btn = QPushButton("🚀 ОТПРАВИТЬ SMS")
        self.send_sms_btn.setMinimumHeight(55)
        self.send_sms_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_sms_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                font-size: 16px;
                font-weight: 800;
                border-radius: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6); }
            QPushButton:disabled { background: #1e293b; color: #475569; }
        """)
        self.send_sms_btn.clicked.connect(self.prepare_sms)
        sms_layout.addWidget(self.send_sms_btn)
        
        self.main_layout.addWidget(self.sms_card)
        self.main_layout.addStretch()

    def detect_sender(self):
        """Auto-detect sender based on authorized user."""
        if self.auth_manager:
            session = self.auth_manager.load_session()
            if session and session.get("login"):
                self.phone_input.setText(session.get("login"))
                self.phone_input.setReadOnly(True)
                self.phone_input.setToolTip("Отправитель определен автоматически")
                return
        
        # If not detected, maybe show a dropdown or just allow manual entry
        # For now, manual entry is fine as per requirements
        self.phone_input.setReadOnly(False)
        self.phone_input.setPlaceholderText("Введите ваше имя или контакт")

    def prepare_sms(self):
        sender = self.phone_input.text().strip()
        msg = self.sms_msg_input.toPlainText().strip()
        ticket_type = self.type_combo.currentText()
        
        if self.type_combo.currentIndex() == 0:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите тип обращения")
            return
        if not sender:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, укажите отправителя")
            return
        if not msg:
            QMessageBox.warning(self, "Ошибка", "Введите текст сообщения")
            return
            
        preview = SMSPreviewDialog(sender, f"[{ticket_type}] {msg}", self)
        if preview.exec() == QDialog.DialogCode.Accepted:
            self.start_sms_sending(sender, msg, ticket_type)

    def start_sms_sending(self, sender, msg, ticket_type):
        self.send_sms_btn.setEnabled(False)
        self.sms_status_box.setVisible(True)
        self.status_steps.setText(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск процесса...")
        
        # Prepare data for worker
        source = self.source_combo.currentText() or "Не указан"
        full_msg = f"Тип: {ticket_type}\nИсточник: {source}\n\n{msg}"
        
        self.worker = SMSWorker(sender, full_msg)
        self.worker.status_update.connect(self.on_sms_status)
        self.worker.finished.connect(self.on_sms_finished)
        self.worker.start()

    def on_drag_enter(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.attach_area.setStyleSheet("border: 2px dashed #3b82f6; background-color: #1e293b; border-radius: 10px;")

    def on_drop(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.process_attachment(file_path)
        self.attach_area.setStyleSheet("border: 2px dashed #334155; background-color: #0f172a; border-radius: 10px;")

    def browse_attachment(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", "Images (*.jpg *.png *.gif)")
        if file_path:
            self.process_attachment(file_path)

    def process_attachment(self, path):
        # 1. Check extension
        ext = os.path.splitext(path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            QMessageBox.warning(self, "Ошибка", "Поддерживаются только JPG, PNG и GIF")
            return
            
        # 2. Check size and compress if needed
        size = os.path.getsize(path)
        if size > 2 * 1024 * 1024: # 2MB
            # Compression logic (mock or simple PIL)
            try:
                img = Image.open(path)
                img.thumbnail((1280, 720)) # Resize
                # Save to temp or byte array
                self.screenshot_path = "temp_compressed.jpg"
                img.save(self.screenshot_path, "JPEG", quality=80)
                self.attach_lbl.setText(f"Файл сжат: {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось сжать файл: {e}")
                return
        else:
            self.screenshot_path = path
            self.attach_lbl.setText(f"Прикреплено: {os.path.basename(path)}")

        # 3. Show preview
        pixmap = QPixmap(self.screenshot_path)
        self.img_preview.setPixmap(pixmap.scaled(self.img_preview.width(), self.img_preview.height(), Qt.AspectRatioMode.KeepAspectRatio))
        self.img_preview.setVisible(True)

    def on_sms_status(self, step, text):
        current = self.status_steps.text()
        new_line = f"\n[{datetime.now().strftime('%H:%M:%S')}] {step}: {text}"
        self.status_steps.setText(current + new_line)

    def on_sms_finished(self, success, err, data):
        self.send_sms_btn.setEnabled(True)
        if success:
            # Add to history
            h_item = {
                "name": self.phone_input.text(),
                "topic": self.type_combo.currentText(),
                "message": self.sms_msg_input.toPlainText(),
                "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "ip": "Local",
                "resolved": False
            }
            
            history = self.data_manager.get_global_data("feedback_history", [])
            history.append(h_item)
            self.data_manager.set_global_data("feedback_history", history)
            self.data_manager.save_data()

            QMessageBox.information(self, "Успех", "SMS сообщение успешно доставлено!")
            self.phone_input.clear()
            self.sms_msg_input.clear()
            self.sms_status_box.setVisible(False)
            self.detect_sender() # Restore sender if auto-detected
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось отправить SMS:\n{err}")

    def apply_theme(self, t): pass
    def load_history(self): pass
    def save_history(self): pass
    def add_history_item(self, data): pass
    def update_char_count(self): pass
    def show_status(self, text, success, is_loading=False): pass
    def resizeEvent(self, event): super().resizeEvent(event)
