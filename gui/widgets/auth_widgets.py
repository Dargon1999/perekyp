import sys
import os
import platform
import asyncio
import random
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QListWidget, QProgressBar, QApplication, QMessageBox,
    QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction

class ServerDataWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            # Simulate network delay
            self.sleep(2)
            
            # Mock data response
            data = {
                "online_users": [f"User_{random.randint(1000, 9999)}" for _ in range(random.randint(5, 15))],
                "server_info": {
                    "ip": "192.168.1.100",
                    "port": "25565",
                    "players": f"{random.randint(10, 100)}/500",
                    "uptime": "48h 12m"
                },
                "system_info": {
                    "version": "9.0.1",
                    "last_update": "2024-05-20"
                }
            }
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

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
        self.input_code.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        self.input_code.returnPressed.connect(self.check_code)
        
        self.btn_login = QPushButton("Войти")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
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
        
        btn_logout = QPushButton("Выйти")
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        btn_logout.clicked.connect(self.logout)
        
        header.addWidget(lbl_dash)
        header.addStretch()
        header.addWidget(btn_logout)
        dash_layout.addLayout(header)

        # Content Area (Loader + Data)
        self.loader = QProgressBar()
        self.loader.setRange(0, 0) # Infinite loading
        self.loader.setVisible(False)
        dash_layout.addWidget(self.loader)
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        dash_layout.addWidget(self.content_area)
        
        # Add widgets to main layout
        self.layout.addWidget(self.login_widget)
        self.layout.addWidget(self.dashboard_widget)

    def check_code(self):
        code = self.input_code.text()
        lockout_role = "admin"
        code_key = "admin_code"
        
        # Check lockout
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
        # Clear sensitive data from UI
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load_data(self):
        self.loader.setVisible(True)
        self.content_area.setVisible(False)
        
        self.worker = ServerDataWorker()
        self.worker.finished.connect(self.on_data_loaded)
        self.worker.error.connect(self.on_data_error)
        self.worker.start()

    def on_data_loaded(self, data):
        self.loader.setVisible(False)
        self.content_area.setVisible(True)
        self.populate_dashboard(data)

    def on_data_error(self, error_msg):
        self.loader.setVisible(False)
        lbl = QLabel(f"Ошибка загрузки данных: {error_msg}")
        lbl.setStyleSheet("color: red;")
        self.content_layout.addWidget(lbl)

    def populate_dashboard(self, data):
        # Clear previous
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 1. Server Info & System Info (Grid)
        info_group = QGroupBox("Информация о сервере и системе")
        grid = QGridLayout()
        
        # Server
        grid.addWidget(QLabel("IP Адрес:"), 0, 0)
        grid.addWidget(QLabel(data["server_info"]["ip"]), 0, 1)
        grid.addWidget(QLabel("Порт:"), 1, 0)
        grid.addWidget(QLabel(data["server_info"]["port"]), 1, 1)
        grid.addWidget(QLabel("Игроки:"), 2, 0)
        grid.addWidget(QLabel(data["server_info"]["players"]), 2, 1)
        grid.addWidget(QLabel("Uptime:"), 3, 0)
        grid.addWidget(QLabel(data["server_info"]["uptime"]), 3, 1)
        
        # System
        grid.addWidget(QLabel("Версия ПО:"), 0, 2)
        grid.addWidget(QLabel(data["system_info"]["version"]), 0, 3)
        grid.addWidget(QLabel("Обновлено:"), 1, 2)
        grid.addWidget(QLabel(data["system_info"]["last_update"]), 1, 3)
        
        info_group.setLayout(grid)
        self.content_layout.addWidget(info_group)

        # 2. File Paths (Copyable)
        paths_group = QGroupBox("Пути к файлам")
        paths_layout = QVBoxLayout()
        
        paths = {
            "Config": os.path.abspath("config.json"), # Dummy paths
            "Logs": os.path.abspath("logs/app.log"),
            "Database": os.path.abspath("data/db.sqlite")
        }
        
        for name, path in paths.items():
            row = QHBoxLayout()
            lbl = QLabel(f"{name}: {path}")
            lbl.setStyleSheet("font-family: monospace; color: #555;")
            btn_copy = QPushButton("Копировать")
            btn_copy.setFixedWidth(80)
            btn_copy.clicked.connect(lambda checked, p=path: QApplication.clipboard().setText(p))
            
            row.addWidget(lbl)
            row.addWidget(btn_copy)
            paths_layout.addLayout(row)
            
        paths_group.setLayout(paths_layout)
        self.content_layout.addWidget(paths_group)

        # 3. Online Users
        users_group = QGroupBox("Пользователи онлайн")
        users_layout = QVBoxLayout()
        user_list = QListWidget()
        user_list.addItems(data["online_users"])
        user_list.setFixedHeight(150)
        users_layout.addWidget(user_list)
        users_group.setLayout(users_layout)
        self.content_layout.addWidget(users_group)


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
        
        lbl_title = QLabel("Введите секретный код")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("Код доступа")
        self.input_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_code.returnPressed.connect(self.check_code)
        
        self.btn_submit = QPushButton("Активировать")
        self.btn_submit.clicked.connect(self.check_code)
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #e74c3c;")
        
        auth_layout.addWidget(lbl_title)
        auth_layout.addWidget(self.input_code)
        auth_layout.addWidget(self.btn_submit)
        auth_layout.addWidget(self.status_lbl)
        
        self.layout.addWidget(self.auth_container)
        
        # Hidden Content (Initially Hidden)
        self.hidden_content = QGroupBox("Скрытые функции")
        self.hidden_content.setVisible(False)
        hidden_layout = QVBoxLayout()
        hidden_layout.addWidget(QLabel("Доступ разрешен! Секретный режим активирован."))
        # Add some dummy hidden features
        hidden_layout.addWidget(QPushButton("Сброс экономики (Тест)"))
        hidden_layout.addWidget(QPushButton("Режим бога (Тест)"))
        self.hidden_content.setLayout(hidden_layout)
        
        self.layout.addWidget(self.hidden_content)

    def check_code(self):
        code = self.input_code.text()
        lockout_role = "extra"
        code_key = "extra_code"
        
        # Check lockout
        lockout_time = self.security_manager.check_lockout(lockout_role)
        if lockout_time > 0:
            self.status_lbl.setText(f"Блокировка: {int(lockout_time)} сек.")
            return

        if self.security_manager.verify_code(code_key, code):
            self.security_manager.register_attempt(lockout_role, True)
            self.status_lbl.setText("Успех!")
            self.status_lbl.setStyleSheet("color: #27ae60;")
            self.hidden_content.setVisible(True)
            self.auth_container.setVisible(False)
        else:
            is_locked, duration = self.security_manager.register_attempt(lockout_role, False)
            if is_locked:
                self.status_lbl.setText(f"Блокировка {int(duration)}с")
            else:
                self.status_lbl.setText("Неверный код")
