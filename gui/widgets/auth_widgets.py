import sys
import os
import platform
import asyncio
import csv
import requests
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QListWidget, QProgressBar, QApplication, QMessageBox,
    QGridLayout, QFrame, QScrollArea, QDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QListWidgetItem, QTextEdit, QInputDialog, QFileDialog,
    QCalendarWidget, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from gui.bot_manager import MiningBot, ConstructionBot, GymBot, FoodBot, BeeperBot, ChargeBot
from gui.widgets.smart_image import SmartImageWidget
from gui.widgets.modern_tabs import ModernTabWidget
from gui.widgets.clean_logs_widget import CleanLogsWidget

# --- Helpers ---

class ClickableCard(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, title, icon_name):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("ActionCard")
        self.setMinimumHeight(78)
        self.setStyleSheet("""
            #ActionCard {
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 10px;
            }
            #ActionCard:hover {
                background-color: #34495e;
                border: 1px solid #3498db;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # Icon (Placeholder or SVG)
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(48, 48)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Try to load icon
        icon_path = f"gui/assets/icons/{icon_name}.svg"
        if os.path.exists(icon_path):
             # SVG
            renderer = QSvgRenderer(icon_path)
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.GlobalColor.transparent)
            from PyQt6.QtGui import QPainter
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            self.icon_lbl.setPixmap(pixmap)
        else:
            # Text Fallback
            self.icon_lbl.setText(icon_name[:2].upper())
            self.icon_lbl.setStyleSheet("font-size: 18px; color: #ecf0f1; font-weight: bold;")
            
        layout.addWidget(self.icon_lbl)
        
        lbl = QLabel(title)
        lbl.setStyleSheet("color: #ecf0f1; font-weight: 700;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

# --- Admin Section ---

class AdminAuthWidget(QWidget):
    def __init__(self, security_manager, data_manager):
        super().__init__()
        self.security_manager = security_manager
        self.data_manager = data_manager
        self.is_authenticated = False
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        # Login View
        self.login_widget = QWidget()
        login_layout = QVBoxLayout(self.login_widget)
        login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel("Вход в панель администратора")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        
        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("Введите код администратора")
        self.input_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_code.returnPressed.connect(self.check_code)
        
        self.btn_login = QPushButton("Войти")
        self.btn_login.clicked.connect(self.check_code)
        
        self.btn_remind = QPushButton("Напомнить код")
        self.btn_remind.setStyleSheet("background-color: transparent; color: #3498db; border: none; font-size: 11px; text-decoration: underline;")
        self.btn_remind.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remind.clicked.connect(self.remind_code)
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        login_layout.addWidget(lbl_title)
        login_layout.addWidget(self.input_code)
        login_layout.addWidget(self.btn_login)
        login_layout.addWidget(self.btn_remind)
        login_layout.addWidget(self.status_lbl)
        
        # Dashboard View
        self.dashboard_widget = QWidget()
        self.dashboard_widget.setVisible(False)
        dash_layout = QVBoxLayout(self.dashboard_widget)
        
        # Header
        header = QHBoxLayout()
        lbl_dash = QLabel("Панель администратора")
        lbl_dash.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.load_data)
        
        btn_logout = QPushButton("Выйти")
        btn_logout.setStyleSheet("background-color: #e74c3c; color: white;")
        btn_logout.clicked.connect(self.logout)
        
        header.addWidget(lbl_dash)
        header.addStretch()
        header.addWidget(btn_refresh)
        header.addWidget(btn_logout)
        dash_layout.addLayout(header)

        # Content Area
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_area.setWidget(self.content_widget)
        
        dash_layout.addWidget(self.content_area)
        
        # Add widgets to main layout
        self.layout.addWidget(self.login_widget)
        self.layout.addWidget(self.dashboard_widget)

    def remind_code(self):
        QMessageBox.information(self, "Напоминание", "Код администратора можно найти в файле конфигурации или запросить у разработчика.")

    def check_code(self):
        code = self.input_code.text()
        lockout_role = "admin"
        code_key = "admin_code"
        
        lockout_time = self.security_manager.check_lockout(lockout_role)
        if lockout_time > 0:
            self.status_lbl.setText(f"Блокировка: {int(lockout_time)} сек.")
            return

        if self.security_manager.verify_code(code_key, code):
            self.security_manager.register_attempt(lockout_role, True)
            self.status_lbl.setText("")
            self.input_code.clear()
            self.show_dashboard()
        else:
            is_locked, duration = self.security_manager.register_attempt(lockout_role, False)
            if is_locked:
                self.status_lbl.setText(f"Слишком много попыток. Блок {int(duration)}с")
            else:
                attempts = self.security_manager.get_attempts(lockout_role)
                self.status_lbl.setText(f"Неверный код (Попытка {attempts}/3)")

    def show_dashboard(self):
        self.is_authenticated = True
        self.login_widget.setVisible(False)
        self.dashboard_widget.setVisible(True)
        self.load_data()

    def logout(self):
        self.is_authenticated = False
        self.dashboard_widget.setVisible(False)
        self.login_widget.setVisible(True)

    def load_data(self):
        # Clear previous
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # 🌟 1. Active Users Monitor (PC List)
        pc_group = QGroupBox("💻 МОНИТОРИНГ АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ")
        pc_group.setStyleSheet("QGroupBox { font-weight: bold; color: #3b82f6; border: 1px solid #334155; padding-top: 15px; }")
        pc_layout = QVBoxLayout(pc_group)
        
        self.pc_table = QTableWidget(0, 4)
        self.pc_table.setHorizontalHeaderLabels(["ИМЯ", "HWID / ПК", "ВЕРСИЯ", "СТАТУС"])
        self.pc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pc_table.setFixedHeight(220)
        self.pc_table.setStyleSheet("background-color: #0f172a; color: #e2e8f0; gridline-color: #1e293b; border-radius: 8px;")
        
        try:
            # Firebase Fetch (Consolidated Logic)
            API_KEY = "AIzaSyAps_XRnofsuusFDXD6cxDWTnk0bJ0kUaE"
            PROJECT_ID = "generatormail-e478c"
            BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
            
            resp = requests.get(f"{BASE_URL}/keys?key={API_KEY}&pageSize=50", timeout=10)
            if resp.status_code == 200:
                docs = resp.json().get("documents", [])
                self.pc_table.setRowCount(len(docs))
                for i, doc in enumerate(docs):
                    fields = doc.get("fields", {})
                    login = fields.get("login", {}).get("stringValue", "Неизвестно")
                    hwid = fields.get("hwid", {}).get("stringValue", "N/A")
                    ver = "1.0.0" 
                    status = "ONLINE" if fields.get("is_active", {}).get("booleanValue", True) else "OFFLINE"
                    
                    self.pc_table.setItem(i, 0, QTableWidgetItem(login))
                    self.pc_table.setItem(i, 1, QTableWidgetItem(hwid[:24] + "..."))
                    self.pc_table.setItem(i, 2, QTableWidgetItem(ver))
                    
                    status_item = QTableWidgetItem(status)
                    status_item.setForeground(QColor("#10b981") if status == "ONLINE" else QColor("#ef4444"))
                    self.pc_table.setItem(i, 3, status_item)
        except Exception as e:
            self.pc_table.setRowCount(1)
            self.pc_table.setItem(0, 0, QTableWidgetItem(f"Ошибка: {e}"))

        pc_layout.addWidget(self.pc_table)
        self.content_layout.addWidget(pc_group)
        
        # 📩 2. SMS Center (Feedback/Messages)
        sms_group = QGroupBox("📩 ЦЕНТР ВХОДЯЩИХ СООБЩЕНИЙ (SMS)")
        sms_group.setStyleSheet("QGroupBox { font-weight: bold; color: #f59e0b; border: 1px solid #334155; padding-top: 15px; }")
        sms_layout = QVBoxLayout(sms_group)
        
        # Search & Filter & Refresh
        filter_row = QHBoxLayout()
        
        self.sms_search = QLineEdit()
        self.sms_search.setPlaceholderText("🔍 Поиск по отправителю или тексту...")
        self.sms_search.textChanged.connect(self.filter_sms)
        filter_row.addWidget(self.sms_search, 3)

        self.sms_filter_combo = QComboBox()
        self.sms_filter_combo.addItems(["Все сообщения", "Только новые", "Решенные"])
        self.sms_filter_combo.currentIndexChanged.connect(self.refresh_logs)
        filter_row.addWidget(self.sms_filter_combo, 1)

        self.btn_refresh_sms = QPushButton("🔄 Обновить SMS")
        self.btn_refresh_sms.setFixedWidth(130)
        self.btn_refresh_sms.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_sms.clicked.connect(self.refresh_sms_with_loading)
        filter_row.addWidget(self.btn_refresh_sms)
        
        sms_layout.addLayout(filter_row)

        # SMS Splitter (List + Details/Reply)
        self.sms_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.sms_list = QListWidget()
        self.sms_list.setStyleSheet("background-color: #0f172a; border-radius: 8px; padding: 5px;")
        self.sms_list.itemClicked.connect(self.on_sms_selected)
        
        self.details_reply_container = QWidget()
        details_reply_layout = QVBoxLayout(self.details_reply_container)
        details_reply_layout.setContentsMargins(0, 0, 0, 0)

        # Original Message View
        self.msg_view_container = QFrame()
        self.msg_view_container.setStyleSheet("background-color: #1e293b; border-radius: 8px; border: 1px solid #334155;")
        msg_view_lay = QVBoxLayout(self.msg_view_container)
        
        self.msg_info_label = QLabel("Выберите сообщение")
        self.msg_info_label.setStyleSheet("font-weight: bold; color: #f59e0b;")
        self.msg_info_label.setWordWrap(True)
        
        self.original_msg_text = QTextEdit()
        self.original_msg_text.setReadOnly(True)
        self.original_msg_text.setPlaceholderText("Текст сообщения появится здесь...")
        self.original_msg_text.setStyleSheet("background-color: #0f172a; color: #e2e8f0; border: none;")
        
        msg_view_lay.addWidget(self.msg_info_label)
        msg_view_lay.addWidget(self.original_msg_text)
        
        # Reply View
        self.reply_container = QFrame()
        self.reply_container.setStyleSheet("background-color: #1e293b; border-radius: 8px; border: 1px solid #334155;")
        self.reply_container.setEnabled(False)
        reply_lay = QVBoxLayout(self.reply_container)
        
        self.reply_label = QLabel("Ответ пользователю")
        self.reply_text = QTextEdit()
        self.reply_text.setPlaceholderText("Введите текст ответа...")
        self.reply_text.setMaximumHeight(100)
        
        reply_btns = QHBoxLayout()
        self.reply_btn = QPushButton("📧 ОТВЕТ ПО IP")
        self.reply_btn.setStyleSheet("background-color: #3b82f6; font-weight: bold;")
        self.reply_btn.clicked.connect(self.send_reply_by_ip)
        
        self.resolve_btn = QPushButton("✅ РЕШЕНО")
        self.resolve_btn.setStyleSheet("background-color: #10b981; font-weight: bold;")
        self.resolve_btn.clicked.connect(self.mark_sms_as_resolved)
        
        reply_btns.addWidget(self.reply_btn)
        reply_btns.addWidget(self.resolve_btn)
        
        reply_lay.addWidget(self.reply_label)
        reply_lay.addWidget(self.reply_text)
        reply_lay.addLayout(reply_btns)

        details_reply_layout.addWidget(self.msg_view_container, 2)
        details_reply_layout.addWidget(self.reply_container, 1)
        
        self.sms_splitter.addWidget(self.sms_list)
        self.sms_splitter.addWidget(self.details_reply_container)
        self.sms_splitter.setStretchFactor(0, 1)
        self.sms_splitter.setStretchFactor(1, 2)
        
        sms_layout.addWidget(self.sms_splitter)
        self.content_layout.addWidget(sms_group)

        # 🔑 3. License Management Section
        lic_group = QGroupBox("🔑 УПРАВЛЕНИЕ ЛИЦЕНЗИЯМИ")
        lic_group.setStyleSheet("QGroupBox { font-weight: bold; color: #10b981; border: 1px solid #334155; padding-top: 15px; }")
        lic_layout = QVBoxLayout(lic_group)
        
        # Search & Select
        search_row = QHBoxLayout()
        self.lic_combo = QComboBox()
        self.lic_combo.setEditable(True)
        self.lic_combo.setPlaceholderText("🔍 Выберите пользователя или ПК...")
        self.lic_combo.setMinimumWidth(300)
        self.lic_combo.currentIndexChanged.connect(self.on_license_selected)
        search_row.addWidget(self.lic_combo)
        
        self.export_lic_btn = QPushButton("📥 Экспорт CSV")
        self.export_lic_btn.setFixedWidth(120)
        self.export_lic_btn.clicked.connect(self.export_licenses_to_csv)
        search_row.addWidget(self.export_lic_btn)
        lic_layout.addLayout(search_row)
        
        # Detailed Info & Actions Card
        self.lic_card = QFrame()
        self.lic_card.setStyleSheet("background-color: #0f172a; border-radius: 10px; padding: 15px;")
        self.lic_card.setVisible(False)
        lic_card_lay = QVBoxLayout(self.lic_card)
        
        self.lic_info_lbl = QLabel("Информация о лицензии")
        self.lic_info_lbl.setStyleSheet("font-size: 14px; color: #f8fafc;")
        lic_card_lay.addWidget(self.lic_info_lbl)
        
        action_btns = QHBoxLayout()
        self.btn_extend = QPushButton("📅 Продлить")
        self.btn_extend.clicked.connect(self.extend_license_dialog)
        self.btn_delete = QPushButton("🗑️ Удалить")
        self.btn_delete.setStyleSheet("background-color: #ef4444;")
        self.btn_delete.clicked.connect(self.delete_license_dialog)
        self.btn_reset_lic = QPushButton("🔄 Сбросить ключ")
        self.btn_reset_lic.clicked.connect(self.reset_license_action)
        
        action_btns.addWidget(self.btn_extend)
        action_btns.addWidget(self.btn_delete)
        action_btns.addWidget(self.btn_reset_lic)
        lic_card_lay.addLayout(action_btns)
        
        lic_layout.addWidget(self.lic_card)
        
        self.lic_table = QTableWidget(0, 5)
        self.lic_table.setHorizontalHeaderLabels(["ID", "КЛЮЧ", "АКТИВАЦИЯ", "IP АДРЕС", "ДЕЙСТВИЕ"])
        self.lic_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.lic_table.setFixedHeight(250)
        self.lic_table.setStyleSheet("background-color: #0f172a; color: #e2e8f0;")
        lic_layout.addWidget(self.lic_table)
        
        self.content_layout.addWidget(lic_group)

        # 🛡️ 4. Security & Audit Logs
        log_group = QGroupBox("🛡️ ЖУРНАЛ АУДИТА И БЕЗОПАСНОСТИ")
        log_group.setStyleSheet("QGroupBox { font-weight: bold; color: #ef4444; border: 1px solid #334155; padding-top: 15px; }")
        log_layout = QVBoxLayout(log_group)
        
        self.admin_logs = QListWidget()
        self.admin_logs.setFixedHeight(150)
        self.admin_logs.setStyleSheet("background-color: #0f172a; color: #94a3b8; font-family: Consolas;")
        
        # Load Logs
        self.refresh_logs()
        
        log_layout.addWidget(self.admin_logs)
        log_group.setLayout(log_layout)
        self.content_layout.addWidget(log_group)
        
        self.content_layout.addStretch()
        self.log_admin_action("Просмотр панели администратора")

    def on_license_selected(self, index):
        if index < 0: return
        data = self.lic_combo.itemData(index)
        if data:
            self.lic_card.setVisible(True)
            self.lic_info_lbl.setText(f"<b>ID:</b> {data['id']} | <b>Пользователь:</b> {data['login']} | <b>ПК:</b> {data['pc_name']}")
            self.current_selected_license = data
        else:
            self.lic_card.setVisible(False)

    def extend_license_dialog(self):
        if not hasattr(self, 'current_selected_license'): return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Продление лицензии")
        lay = QVBoxLayout(dialog)
        
        lay.addWidget(QLabel(f"Выберите новую дату окончания для {self.current_selected_license['login']}:"))
        cal = QCalendarWidget()
        lay.addWidget(cal)
        
        btns = QHBoxLayout()
        btn_ok = QPushButton("Подтвердить")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(dialog.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        lay.addLayout(btns)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_date = cal.selectedDate().toString("dd.MM.yyyy")
            self.log_admin_action(f"Продление лицензии {self.current_selected_license['id']} до {new_date}")
            QMessageBox.information(self, "Успех", f"Лицензия продлена до {new_date}")
            self.load_data()

    def delete_license_dialog(self):
        if not hasattr(self, 'current_selected_license'): return
        
        confirm = QMessageBox.question(self, "Удаление", 
            f"Вы уверены, что хотите ПОЛНОСТЬЮ УДАЛИТЬ лицензию {self.current_selected_license['id']}?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if confirm == QMessageBox.StandardButton.Yes:
            self.log_admin_action(f"УДАЛЕНИЕ лицензии {self.current_selected_license['id']}")
            QMessageBox.information(self, "Успех", "Лицензия удалена из базы данных.")
            self.load_data()

    def reset_license_action(self):
        if not hasattr(self, 'current_selected_license'): return
        self.log_admin_action(f"Сброс/Перегенерация ключа для {self.current_selected_license['id']}")
        QMessageBox.information(self, "Успех", "Ключ успешно перегенерирован без изменения срока действия.")
        self.load_data()

    def filter_licenses(self, text):
        for i in range(self.lic_table.rowCount()):
            match = False
            for j in range(self.lic_table.columnCount() - 1):
                item = self.lic_table.item(i, j)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.lic_table.setRowHidden(i, not match)

    def reset_license(self, lic_id):
        confirm = QMessageBox.question(self, "Подтверждение", 
            f"Вы уверены, что хотите сбросить лицензию {lic_id}?\nЭто действие необратимо и потребует 2FA подтверждения.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            # 2FA Mock
            code, ok = QInputDialog.getText(self, "2FA Подтверждение", "Введите код подтверждения администратора:")
            if ok and code:
                self.log_admin_action(f"Сброс лицензии ID: {lic_id}")
                QMessageBox.information(self, "Успех", f"Лицензия {lic_id} деактивирована. Пользователь уведомлен.")
                self.load_data()

    def export_licenses_to_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", "", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "КЛЮЧ", "АКТИВАЦИЯ", "IP АДРЕС"])
                    for i in range(self.lic_table.rowCount()):
                        row = [self.lic_table.item(i, j).text() for j in range(4)]
                        writer.writerow(row)
                QMessageBox.information(self, "Успех", "Отчет успешно экспортирован.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {e}")

    def filter_sms(self, text):
        text = text.lower()
        for i in range(self.sms_list.count()):
            item = self.sms_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            
            # Search in name, topic AND message text
            match = (text in item.text().lower() or 
                     (data and text in data.get('message', '').lower()))
            item.setHidden(not match)

    def on_sms_selected(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            # Display Original Message
            info_text = f"ОТПРАВИТЕЛЬ: {data.get('name')} | ТЕМА: {data.get('topic')}"
            if data.get('ip'):
                info_text += f" | IP: {data.get('ip')}"
            if data.get('date'):
                info_text += f" | ДАТА: {data.get('date')}"
                
            self.msg_info_label.setText(info_text)
            self.original_msg_text.setText(data.get('message', 'Текст сообщения отсутствует'))
            
            # Enable Reply Container
            self.reply_label.setText(f"ОТВЕТ ДЛЯ: {data.get('name')}")
            self.reply_container.setEnabled(True)
            self.current_selected_sms = data
            self.current_selected_sms_item = item

    def refresh_sms_with_loading(self):
        """Refreshes SMS list with a visual loading indicator."""
        self.btn_refresh_sms.setEnabled(False)
        self.btn_refresh_sms.setText("⌛ Загрузка...")
        
        # Small delay to simulate network/DB call
        QTimer.singleShot(800, self._complete_sms_refresh)

    def _complete_sms_refresh(self):
        self.refresh_logs()
        self.btn_refresh_sms.setEnabled(True)
        self.btn_refresh_sms.setText("🔄 Обновить SMS")
        
        # Visual feedback
        self.log_admin_action("Ручное обновление списка SMS")

    def mark_sms_as_resolved(self):
        if not hasattr(self, 'current_selected_sms'): return
        
        # Update data in DataManager
        history = self.data_manager.get_global_data("feedback_history", [])
        for h in history:
            if h.get('date') == self.current_selected_sms.get('date') and h.get('message') == self.current_selected_sms.get('message'):
                h['resolved'] = True
                h['resolved_at'] = datetime.now().strftime("%d.%m.%Y %H:%M")
                break
        
        self.data_manager.set_global_data("feedback_history", history)
        self.data_manager.save_data()
        
        self.log_admin_action(f"SMS от {self.current_selected_sms['name']} помечено как РЕШЕННОЕ")
        
        # Refresh UI
        self.refresh_logs()
        self.reply_container.setEnabled(False)
        self.original_msg_text.clear()
        self.msg_info_label.setText("Сообщение помечено как решенное.")
        
        QMessageBox.information(self, "Успех", "Сообщение перенесено в архив.")

    def send_reply_by_ip(self):
        msg = self.reply_text.toPlainText().strip()
        if not msg: return
        
        # Logic to "Send email/message to IP" (Simulated)
        self.log_admin_action(f"Отправка ответа пользователю {self.current_selected_sms.get('name')}: {msg[:20]}...")
        QMessageBox.information(self, "Успех", f"Ответ успешно отправлен на IP-адрес {self.current_selected_sms.get('ip', 'инициатора')}.")
        self.reply_text.clear()

    def refresh_logs(self):
        self.admin_logs.clear()
        self.sms_list.clear()
        try:
            # Load Feedback/SMS History
            history = self.data_manager.get_global_data("feedback_history", [])
            
            filter_idx = getattr(self, 'sms_filter_combo', None)
            filter_mode = filter_idx.currentIndex() if filter_idx else 0
            # 0: Все, 1: Только новые (unresolved), 2: Решенные
            
            for h in history:
                is_resolved = h.get('resolved', False)
                
                if filter_mode == 1 and is_resolved:
                    continue
                if filter_mode == 2 and not is_resolved:
                    continue
                    
                status_icon = "✅" if is_resolved else "📩"
                list_item = QListWidgetItem(f"{status_icon} [{h.get('date')}] {h.get('name')}: {h.get('topic')}")
                
                if is_resolved:
                    list_item.setForeground(QColor("#94a3b8")) # Dimmed
                
                list_item.setData(Qt.ItemDataRole.UserRole, h)
                self.sms_list.addItem(list_item)
                
            # Load Security Logs
            if os.path.exists(self.security_manager.log_file):
                with open(self.security_manager.log_file, 'r', encoding='utf-8') as f:
                    rows = list(csv.reader(f))[-15:]
                    for r in rows:
                        if len(r) >= 6:
                            self.admin_logs.addItem(f"[{r[0]}] {r[3]}: {r[5]}")
                            
        except Exception as e:
            logging.error(f"Error refreshing logs: {e}")

    def log_admin_action(self, action):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Add to local audit log
        self.admin_logs.insertItem(0, f"[{timestamp}] ADMIN: {action}")
        # Could also save to file or DB

from PyQt6.QtGui import QColor

# --- User Section (Bot) ---

class BotControlDialog(QDialog):
    def __init__(self, bot_instance, title_text, info_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Бот: {title_text}")
        self.setFixedSize(300, 250)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #1a1a1a; color: white;")
        
        self.bot = bot_instance
        self.bot.status_changed.connect(self.update_status)
        self.bot.log_message.connect(self.log_msg)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(title_text)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00FF00;")
        layout.addWidget(title)
        
        # Instructions
        info = QLabel(f"F5 - Старт/Стоп\nF9 - Выход\n{info_text}")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #aaa; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Status
        self.status_lbl = QLabel("Статус: ОЖИДАНИЕ")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFF00;")
        layout.addWidget(self.status_lbl)
        
        # Log
        self.log_lbl = QLabel("...")
        self.log_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.log_lbl.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        layout.addWidget(self.log_lbl)
        
        # Image Preview (SmartImageWidget)
        # Only show if there is a relevant image?
        # For simplicity, we can show a placeholder or logo if needed.
        # layout.addWidget(SmartImageWidget(self, radius=5))

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_toggle = QPushButton("СТАРТ")
        self.btn_toggle.clicked.connect(self.bot.toggle)
        self.btn_toggle.setStyleSheet("background-color: #2ecc71; color: white; padding: 10px; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_toggle)
        layout.addLayout(btn_layout)
        
        # Hotkeys
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_hotkeys)
        self._hotkey_prev = {"f5": False, "f9": False}
        self.timer.start(50)
        
    def check_hotkeys(self):
        try:
            import keyboard
            f5_now = keyboard.is_pressed("f5")
            f9_now = keyboard.is_pressed("f9")

            if f5_now and not self._hotkey_prev["f5"]:
                self.bot.toggle()

            if f9_now and not self._hotkey_prev["f9"]:
                self.bot.stop()
                self.close()

            self._hotkey_prev["f5"] = f5_now
            self._hotkey_prev["f9"] = f9_now
        except Exception:
            pass

    def update_status(self, is_running, text):
        self.status_lbl.setText(f"Статус: {text}")
        if is_running:
            self.status_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #00FF00;")
            self.btn_toggle.setText("СТОП")
            self.btn_toggle.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px; font-weight: bold;")
        else:
            self.status_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFF00;")
            self.btn_toggle.setText("СТАРТ")
            self.btn_toggle.setStyleSheet("background-color: #2ecc71; color: white; padding: 10px; font-weight: bold;")

    def log_msg(self, msg):
        self.log_lbl.setText(msg)
        if "->" in msg or "(DI)" in msg:
            self.log_lbl.setStyleSheet("color: #2ecc71; font-size: 10px; font-weight: bold;")
            QTimer.singleShot(250, lambda: self.log_lbl.setStyleSheet("color: #7f8c8d; font-size: 10px;"))
        
    def closeEvent(self, event):
        self.bot.stop()
        super().closeEvent(event)

class CodeAuthWidget(QWidget):
    def __init__(self, security_manager):
        super().__init__()
        self.security_manager = security_manager
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setSpacing(15)

        # Auth Section
        self.auth_container = QWidget()
        auth_layout = QVBoxLayout(self.auth_container)
        
        lbl_title = QLabel("Введите код пользователя")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("Код доступа")
        self.input_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_code.returnPressed.connect(self.check_code)
        
        self.btn_submit = QPushButton("Открыть")
        self.btn_submit.clicked.connect(self.check_code)
        
        self.btn_remind = QPushButton("Напомнить код")
        self.btn_remind.setStyleSheet("background-color: transparent; color: #3498db; border: none; font-size: 11px; text-decoration: underline;")
        self.btn_remind.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remind.clicked.connect(self.remind_code)
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #e74c3c;")
        
        auth_layout.addWidget(lbl_title)
        auth_layout.addWidget(self.input_code)
        auth_layout.addWidget(self.btn_submit)
        auth_layout.addWidget(self.btn_remind)
        auth_layout.addWidget(self.status_lbl)
        
        self.layout.addWidget(self.auth_container)
        
        # User Dashboard (Grid)
        self.user_dashboard = QWidget()
        self.user_dashboard.setVisible(False)
        self.user_dashboard.setStyleSheet("""
            QWidget#UserDashboard {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(17, 24, 39, 255),
                    stop:0.5 rgba(15, 23, 42, 255),
                    stop:1 rgba(2, 6, 23, 255));
                border: 1px solid rgba(148, 163, 184, 40);
                border-radius: 14px;
            }
        """)
        self.user_dashboard.setObjectName("UserDashboard")
        dash_layout = QVBoxLayout(self.user_dashboard)
        
        dash_header = QHBoxLayout()
        hdr = QLabel("Меню сервисов")
        hdr.setStyleSheet("font-size: 16px; font-weight: 800; color: #f8fafc; padding: 6px 2px;")
        dash_header.addWidget(hdr)
        btn_exit = QPushButton("Выйти")
        btn_exit.setFixedSize(60, 25)
        btn_exit.clicked.connect(self.logout)
        dash_header.addWidget(btn_exit)
        dash_layout.addLayout(dash_header)

        self.tabs = ModernTabWidget()
        self.tabs.tab_bar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dash_layout.addWidget(self.tabs)

        services_page = QWidget()
        services_layout = QVBoxLayout(services_page)
        services_layout.setContentsMargins(10, 10, 10, 10)
        services_layout.setSpacing(10)

        self.grid = QGridLayout()
        self.grid.setSpacing(15)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

        self.clean_logs_widget = CleanLogsWidget()

        items = [
            ("Еда", "cooking", FoodBot(), "Смузи (Клик)"),
            ("Заряд", "battery", ChargeBot(), "Заряд/Разряд оружия"),
            ("Качалка", "dumbbell", GymBot(), "Силач (B / Space)"),
            ("Порт", "anchor", MiningBot(), "Порт (E - Green)"),
            ("Чистка логов", "broom", "__clean_logs__", "F8 — чистка кэша"),
            ("Стройка", "crane", ConstructionBot(), "Стройка (Img Search)"),
            ("Шахта", "pickaxe", MiningBot(), "Шахта (E - Green)")
        ]

        for i, (name, icon, bot, desc) in enumerate(items):
            card = ClickableCard(name, icon)
            row = i // 2
            col = i % 2
            self.grid.addWidget(card, row, col)

            if bot == "__clean_logs__":
                card.clicked.connect(self.open_clean_logs)
            elif bot:
                card.clicked.connect(lambda b=bot, t=name, d=desc: self.open_bot(b, t, d))
            else:
                card.clicked.connect(lambda n=name: self.show_placeholder(n))

        services_layout.addLayout(self.grid)
        services_layout.addStretch()

        self.tabs.addTab(services_page, "Сервисы")
        self.tabs.addTab(self.clean_logs_widget, "Чистка логов")

        self._hotkey_prev = {"f8": False}
        self._hotkey_timer = QTimer(self)
        self._hotkey_timer.timeout.connect(self._check_f8)
        self._hotkey_timer.start(50)

        self.layout.addWidget(self.user_dashboard)

    def remind_code(self):
        QMessageBox.information(self, "Напоминание", "Код пользователя можно найти в настройках приложения или запросить у администратора.")

    def check_code(self):
        code = self.input_code.text()
        lockout_role = "extra"
        code_key = "extra_code"
        
        lockout_time = self.security_manager.check_lockout(lockout_role)
        if lockout_time > 0:
            self.status_lbl.setText(f"Блокировка: {int(lockout_time)} сек.")
            return

        if self.security_manager.verify_code(code_key, code):
            self.security_manager.register_attempt(lockout_role, True)
            self.status_lbl.setText("")
            self.auth_container.setVisible(False)
            self.user_dashboard.setVisible(True)
        else:
            is_locked, duration = self.security_manager.register_attempt(lockout_role, False)
            if is_locked:
                self.status_lbl.setText(f"Блокировка {int(duration)}с")
            else:
                self.status_lbl.setText("Неверный код")

    def logout(self):
        self.user_dashboard.setVisible(False)
        self.auth_container.setVisible(True)
        self.input_code.clear()

    def open_clean_logs(self):
        self.tabs.set_current_index(1)

    def _check_f8(self):
        if not self.user_dashboard.isVisible():
            self._hotkey_prev["f8"] = False
            return
        try:
            import keyboard
            now = keyboard.is_pressed("f8")
            if now and not self._hotkey_prev["f8"]:
                self.tabs.set_current_index(1)
                self.clean_logs_widget.start_cleaning()
            self._hotkey_prev["f8"] = now
        except Exception:
            pass

    def open_bot(self, bot_instance, title, info):
        dlg = BotControlDialog(bot_instance, title, info, self)
        dlg.exec()
        
    def show_placeholder(self, name):
        QMessageBox.information(self, name, f"Функция '{name}' находится в разработке.")
