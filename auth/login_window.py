from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFrame, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QByteArray, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
import os
from auth.auth_manager import AuthManager
from gui.custom_dialogs import AlertDialog, ConfirmationDialog, CleanupProgressDialog
from gui.widgets.eyes_widget import EyesWidget
from gui.widgets.utility_widgets import InternalMemWorker, InternalTempWorker
from gui.animations import AnimationManager
from gui.styles import StyleManager
from utils import resource_path
import ctypes
import sys
import subprocess

LOGIN_SVG = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M11 7L9.6 8.4L12.2 11H2V13H12.2L9.6 15.6L11 17L16 12L11 7ZM20 19H12V21H20C21.1 21 22 20.1 22 19V5C22 3.9 21.1 3 20 3H12V5H20V19Z" fill="white"/>
</svg>
"""

def create_svg_icon(svg_content, size=24, color="white"):
    # Replace color if needed (simple string replacement)
    if color != "white":
        svg_content = svg_content.replace("white", color)
        
    renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

class DeactivateWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, auth_manager, login, password, key):
        super().__init__()
        self.auth_manager = auth_manager
        self.login = login
        self.password = password
        self.key = key

    def run(self):
        try:
            success, message = self.auth_manager.deactivate_key(self.login, self.password, self.key)
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, str(e))

class LoginWorker(QThread):
    finished = pyqtSignal(bool, str, object) # success, message, expires_at

    def __init__(self, auth_manager, login, password, key):
        super().__init__()
        self.auth_manager = auth_manager
        self.login = login
        self.password = password
        self.key = key

    def run(self):
        try:
            success, message, expires_at = self.auth_manager.validate_key(self.login, self.password, self.key)
            self.finished.emit(success, message, expires_at)
        except Exception as e:
            self.finished.emit(False, str(e), None)

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация - MoneyTracker")
        
        # Ensure icon is set for Taskbar/Alt-Tab
        icon_path = resource_path("icon_v2.ico")
        if not os.path.exists(icon_path):
            icon_path = resource_path("icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        
        # Additional icon setup for potentially standalone behavior
        self.setProperty("icon_path", icon_path)
        
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.auth_manager = AuthManager()
        
        self.setup_ui()
        self.load_saved_creds()
        
        # Animate Window Appearance
        AnimationManager.fade_in(self.container)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F7:
            self.run_f7_ram_clean()
        elif event.key() == Qt.Key.Key_F8:
            self.run_f8_temp_clean()
        else:
            super().keyPressEvent(event)

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def run_f7_ram_clean(self):
        if not self.is_admin():
            dlg = AlertDialog(self, "Ошибка доступа", "Для очистки RAM требуются права администратора.\nПожалуйста, запустите приложение от имени администратора.")
            dlg.exec()
            return

        dlg = ConfirmationDialog(self, "Очистка RAM", "Вы действительно хотите запустить встроенную оптимизацию оперативной памяти?")
        if dlg.exec():
            # Internal memory optimizer launch (replacing external call)
            from gui.widgets.utility_widgets import InternalMemWorker
            
            self.cleanup_dlg = CleanupProgressDialog(self)
            self.cleanup_dlg.show()
            self.cleanup_dlg.setWindowTitle("Оптимизация RAM")
            
            self.mem_worker = InternalMemWorker()
            self.mem_worker.progress.connect(self.cleanup_dlg.set_progress)
            self.mem_worker.log.connect(self.cleanup_dlg.append_log)
            self.mem_worker.finished_data.connect(self.on_mem_cleanup_finished)
            
            self.mem_worker.start()

    def on_mem_cleanup_finished(self, data):
        status = data.get("status")
        if status == "success":
            summary = "Оптимизация RAM успешно завершена!"
        else:
            summary = f"Оптимизация завершена с ошибкой:\n{data.get('msg')}"
        
        self.cleanup_dlg.on_finished(summary)

    def run_f8_temp_clean(self):
        dlg = ConfirmationDialog(self, "Очистка системы", "Вы действительно хотите запустить очистку временных файлов?\n\nБудет выполнено:\n- Очистка %TEMP%\n- Очистка системного кэша\n- Очистка корзины")
        if not dlg.exec():
            return

        # Backup critical data before cleanup (example: config.json and data.json)
        self.backup_critical_data()

        self.cleanup_dlg = CleanupProgressDialog(self)
        self.cleanup_dlg.show()
        
        self.temp_worker = InternalTempWorker()
        self.temp_worker.progress.connect(self.cleanup_dlg.set_progress)
        self.temp_worker.log.connect(self.cleanup_dlg.append_log)
        self.temp_worker.finished_data.connect(self.on_temp_cleanup_finished)
        
        # Connect cancellation
        self.cleanup_dlg.btn_cancel.clicked.connect(self.temp_worker.cancel)
        
        self.temp_worker.start()

    def backup_critical_data(self):
        import shutil
        import datetime
        backup_dir = os.path.join(os.getcwd(), "backups", "cleanup_pre")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for f in ["config.json", "data.json"]:
            if os.path.exists(f):
                shutil.copy2(f, os.path.join(backup_dir, f"{f}_{timestamp}.bak"))

    def on_temp_cleanup_finished(self, data):
        status = data.get("status")
        if status == "success":
            freed = data.get("freed_mb", 0)
            summary = f"Очистка успешно завершена!\nОсвобождено: {freed:.2f} МБ"
        elif status == "cancelled":
            freed = data.get("freed_mb", 0)
            summary = f"Операция прервана пользователем.\nУспели очистить: {freed:.2f} МБ"
        else:
            summary = f"Очистка завершена с ошибкой:\n{data.get('msg')}"
        
        self.cleanup_dlg.on_finished(summary)

    def setup_ui(self):
        # Get theme colors
        t = StyleManager.get_theme("dark") # Login always dark for now

        # Main container
        self.container = QFrame(self)
        self.container.setGeometry(10, 10, 380, 500)
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {t['bg_secondary']};
                border-radius: 16px;
                border: 1px solid {t['border']};
            }}
        """)
        
        layout = QVBoxLayout(self.container)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 40, 30, 40)
        
        # Eyes Animation
        eyes_container = QWidget()
        eyes_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        eyes_container.setStyleSheet("background-color: transparent;")
        eyes_layout = QHBoxLayout(eyes_container)
        eyes_layout.setContentsMargins(0, 0, 0, 0)
        eyes_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eyes = EyesWidget(eye_size=25, pupil_size=10, distance=10)
        eyes_layout.addWidget(self.eyes)
        layout.addWidget(eyes_container)
        
        # Title
        title = QLabel("Вход в систему")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("Header")
        layout.addWidget(title)
        
        subtitle = QLabel("Введите данные лицензии")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("Label")
        layout.addWidget(subtitle)
        
        # Inputs
        self.login_input = self.create_input("Логин")
        self.password_input = self.create_input("Пароль", is_password=True)
        self.key_input = self.create_input("Ключ доступа")
        
        layout.addWidget(self.login_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.key_input)
        
        layout.addStretch()
        
        # Buttons
        self.login_btn = QPushButton("Войти")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setFixedHeight(45)
        self.login_btn.setIcon(create_svg_icon(LOGIN_SVG, 20))
        self.login_btn.setIconSize(QSize(20, 20))
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['accent']};
                color: white;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                border: none;
                padding-left: 10px;
                padding-right: 10px;
            }}
            QPushButton:hover {{
                background-color: {t['accent']}E6; /* 90% opacity */
            }}
            QPushButton:pressed {{
                background-color: {t['accent']}CC; /* 80% opacity */
            }}
            QPushButton:disabled {{
                background-color: {t['text_secondary']};
            }}
        """)
        self.login_btn.clicked.connect(self.attempt_login)
        layout.addWidget(self.login_btn)
        
        exit_btn = QPushButton("Выход")
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['text_secondary']};
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                border: 1px solid transparent;
            }}
            QPushButton:hover {{
                color: {t['danger']};
                background-color: {t['danger']}1A;
            }}
        """)
        exit_btn.clicked.connect(self.reject)
        layout.addWidget(exit_btn)
        
    def create_input(self, placeholder, is_password=False):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        if is_password:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setFixedHeight(45)
        return inp
        
    def load_saved_creds(self):
        session = self.auth_manager.load_session()
        if session:
            self.login_input.setText(session.get("login", ""))
            self.password_input.setText(session.get("password", ""))
            self.key_input.setText(session.get("key", ""))
            
    def attempt_login(self):
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()
        key = self.key_input.text().strip()
        
        if not all([login, password, key]):
            dlg = AlertDialog(self, "Ошибка", "Заполните все поля")
            dlg.exec()
            return
            
        self.login_btn.setText("Проверка...")
        self.login_btn.setEnabled(False)
        self.login_input.setEnabled(False)
        self.password_input.setEnabled(False)
        self.key_input.setEnabled(False)
        
        # Start worker
        self.worker = LoginWorker(self.auth_manager, login, password, key)
        self.worker.finished.connect(self.on_login_finished)
        self.worker.start()

        # Watchdog Timer (15s timeout)
        self.watchdog = QTimer(self)
        self.watchdog.setSingleShot(True)
        self.watchdog.timeout.connect(self.on_login_timeout)
        self.watchdog.start(15000)

    def on_login_timeout(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.on_login_finished(False, "Превышено время ожидания ответа от сервера (Timeout)", None)

    def on_login_finished(self, success, message, expires_at):
        # Stop watchdog and loading animation
        if hasattr(self, 'watchdog') and self.watchdog.isActive():
            self.watchdog.stop()
        if hasattr(self, 'loading_timer') and self.loading_timer.isActive():
            self.loading_timer.stop()

        self.login_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.key_input.setEnabled(True)
        
        if success:
            self.accept()
        else:
            self.login_btn.setText("Войти")
            self.login_btn.setEnabled(True)
            
            if message == "ERR_HWID_MISMATCH":
                from gui.custom_dialogs import ConfirmationDialog
                dlg = ConfirmationDialog(
                    self, 
                    "Ключ занят", 
                    "Этот ключ уже активирован на другом ПК.\n\n"
                    "Хотите сбросить привязку и активировать ключ на этом компьютере?\n"
                    "(Потребуется ввести верный логин и пароль)"
                )
                if dlg.exec():
                    self.attempt_deactivation()
            else:
                dlg = AlertDialog(self, "Ошибка доступа", message)
                dlg.exec()

    def attempt_deactivation(self):
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()
        key = self.key_input.text().strip()
        
        self.login_btn.setText("Сброс...")
        self.login_btn.setEnabled(False)
        
        self.deact_worker = DeactivateWorker(self.auth_manager, login, password, key)
        self.deact_worker.finished.connect(self.on_deactivation_finished)
        self.deact_worker.start()

    def on_deactivation_finished(self, success, message):
        self.login_btn.setText("Войти")
        self.login_btn.setEnabled(True)
        
        dlg = AlertDialog(self, "Результат", message)
        dlg.exec()
        
        if success:
            # Try login again automatically
            self.attempt_login()
