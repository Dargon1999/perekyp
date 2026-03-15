import sys
import os
import platform
import asyncio
import csv
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QListWidget, QProgressBar, QApplication, QMessageBox,
    QGridLayout, QFrame, QScrollArea, QDialog
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
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        login_layout.addWidget(lbl_title)
        login_layout.addWidget(self.input_code)
        login_layout.addWidget(self.btn_login)
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
                
        # 1. Active Profile Stats
        profile = self.data_manager.get_active_profile()
        if profile:
            group = QGroupBox(f"Активный профиль: {profile.get('name', 'N/A')}")
            grid = QGridLayout()
            
            balance = sum(t["amount"] for t in profile.get("transactions", []))
            tx_count = len(profile.get("transactions", []))
            
            grid.addWidget(QLabel("Баланс (расчетный):"), 0, 0)
            grid.addWidget(QLabel(f"{balance:.2f}"), 0, 1)
            grid.addWidget(QLabel("Всего транзакций:"), 1, 0)
            grid.addWidget(QLabel(str(tx_count)), 1, 1)
            
            group.setLayout(grid)
            self.content_layout.addWidget(group)
            
        # 2. Security Logs
        log_group = QGroupBox("Логи безопасности (последние 10)")
        log_layout = QVBoxLayout()
        log_list = QListWidget()
        
        try:
            if os.path.exists(self.security_manager.log_file):
                with open(self.security_manager.log_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader, None) # Skip header
                    rows = list(reader)
                    for row in rows[-10:]:
                        # Timestamp, IP, User-Agent, Event, Result, Details
                        if len(row) >= 6:
                            log_list.addItem(f"[{row[0]}] {row[3]} ({row[4]}): {row[5]}")
        except Exception as e:
            log_list.addItem(f"Ошибка чтения логов: {e}")
            
        log_layout.addWidget(log_list)
        log_group.setLayout(log_layout)
        self.content_layout.addWidget(log_group)
        
        self.content_layout.addStretch()

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
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #e74c3c;")
        
        auth_layout.addWidget(lbl_title)
        auth_layout.addWidget(self.input_code)
        auth_layout.addWidget(self.btn_submit)
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
