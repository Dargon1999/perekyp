import logging
import os
import json
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QStackedWidget, QFrame, QMessageBox, QListWidget, 
    QListWidgetItem, QComboBox, QCheckBox, QScrollArea, QGroupBox,
    QGridLayout, QButtonGroup, QRadioButton, QGraphicsOpacityEffect,
    QFileDialog, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QColor, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from gui.styles import StyleManager
from gui.security_manager import SecurityManager
from gui.update_manager import UpdateManager
from gui.widgets.feedback_widget import FeedbackWidget
from gui.widgets.toggle_switch import ToggleSwitch
from gui.widgets.auth_widgets import AdminAuthWidget, CodeAuthWidget
from gui.custom_dialogs import StyledDialogBase, AlertDialog, ConfirmationDialog, RestoreProfileDialog
from version import VERSION

EYE_OPEN_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 4.5C7 4.5 2.73 7.61 1 12C2.73 16.39 7 19.5 12 19.5C17 19.5 21.27 16.39 23 12C21.27 7.61 17 4.5 12 4.5ZM12 17C9.24 17 7 14.76 7 12C7 9.24 9.24 7 12 7C14.76 7 17 9.24 17 12C17 14.76 14.76 17 12 17ZM12 9C10.34 9 9 10.34 9 12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12C15 10.34 13.66 9 12 9Z" fill="white"/></svg>"""
EYE_CLOSED_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 7C14.76 7 17 9.24 17 12C17 12.88 16.77 13.71 16.38 14.44L17.84 15.9C18.57 14.76 19 13.43 19 12C19 9.24 16.76 7 14 7H12ZM12 4.5C17 4.5 21.27 7.61 23 12C22.18 14.08 20.78 15.86 19.03 17.2L20.55 18.72L19.28 20L4 4.73L5.27 3.45L7.29 5.47C8.71 4.86 10.31 4.5 12 4.5ZM10.5 8.68L15.32 13.5C15.22 13.5 15.11 13.5 15 13.5C13.66 13.5 12.5 12.55 12.18 11.27L9.5 8.59C9.79 8.62 10.13 8.68 10.5 8.68ZM2.83 6.94L4.81 8.92C3.25 10.22 2 11.89 1 12C2.73 16.39 7 19.5 12 19.5C13.54 19.5 15 19.14 16.35 18.49L18.47 20.61L2.83 6.94ZM12 17C10.13 17 8.5 15.93 7.66 14.33L10.38 17.05C10.89 17.03 11.43 17 12 17Z" fill="white"/></svg>"""

class SettingsLoginWorker(QThread):
    finished = pyqtSignal(bool, str, float)

    def __init__(self, security_manager, role, key_name, code):
        super().__init__()
        self.security_manager = security_manager
        self.role = role
        self.key_name = key_name
        self.code = code

    def run(self):
        # Simulate small delay for UX
        self.msleep(300)
        
        success = self.security_manager.verify_code(self.key_name, self.code)
        
        if success:
            self.security_manager.register_attempt(self.role, True)
            locked, duration = False, 0
        else:
            locked, duration = self.security_manager.register_attempt(self.role, False)
        
        msg = ""
        if not success:
            if locked:
                msg = f"Блокировка: {int(duration)} сек."
            else:
                msg = "Неверный код доступа"
        
        self.finished.emit(success, msg, duration)

class SettingsAuthWorker(QThread):
    finished = pyqtSignal(str, str, float) # role (admin/user/None), msg, duration

    def __init__(self, security_manager, code):
        super().__init__()
        self.security_manager = security_manager
        self.code = code

    def run(self):
        self.msleep(300)
        
        # 1. Check Admin
        if self.security_manager.verify_code("admin_code", self.code):
            self.security_manager.register_attempt("admin", True)
            self.finished.emit("admin", "Успешный вход (Администратор)", 0)
            return
            
        # 2. Check User
        if self.security_manager.verify_code("extra_code", self.code):
            self.security_manager.register_attempt("extra", True)
            self.finished.emit("user", "Успешный вход (Пользователь)", 0)
            return
            
        # 3. Failed
        # Register failure for admin to be safe
        locked, duration = self.security_manager.register_attempt("admin", False)
        msg = f"Блокировка: {int(duration)} сек." if locked else "Неверный код доступа"
        self.finished.emit(None, msg, duration)

class ClickableFrame(QFrame):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class ChangeCodeDialog(StyledDialogBase):
    def __init__(self, parent, title, security_manager, code_key):
        super().__init__(parent, title)
        self.security_manager = security_manager
        self.code_key = code_key
        
        t = StyleManager.get_theme(self._theme)
        
        # Current Code
        self.content_layout.addWidget(QLabel("Текущий код:"))
        self.current_code = QLineEdit()
        self.current_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.content_layout.addWidget(self.current_code)
        
        # New Code
        self.content_layout.addWidget(QLabel("Новый код:"))
        self.new_code = QLineEdit()
        self.new_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.content_layout.addWidget(self.new_code)
        
        # Confirm Code
        self.content_layout.addWidget(QLabel("Подтвердите код:"))
        self.confirm_code = QLineEdit()
        self.confirm_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.content_layout.addWidget(self.confirm_code)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = self.create_button("Сохранить", "primary", self.save_code)
        self.cancel_btn = self.create_button("Отмена", "secondary", self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        self.content_layout.addLayout(btn_layout)
        
    def save_code(self):
        current = self.current_code.text()
        new = self.new_code.text()
        confirm = self.confirm_code.text()
        
        # Verify current
        if not self.security_manager.verify_code(self.code_key, current):
            QMessageBox.warning(self, "Ошибка", "Неверный текущий код.")
            return
        
        # Validate new
        if new != confirm:
            QMessageBox.warning(self, "Ошибка", "Новые коды не совпадают.")
            return
        
        valid, msg = self.security_manager.validate_complexity(new)
        if not valid:
            QMessageBox.warning(self, "Ошибка", f"Код слишком простой:\n{msg}")
            return
        
        # Save
        self.security_manager.set_code(self.code_key, new)
        QMessageBox.information(self, "Успех", "Код успешно изменен.")
        self.accept()

class SettingsLoginDialog(StyledDialogBase):
    def __init__(self, parent, security_manager):
        super().__init__(parent, "Вход в настройки")
        self.security_manager = security_manager
        self.role = None
        
        # Input
        self.content_layout.addWidget(QLabel("Введите код доступа:"))
        self.code_input = QLineEdit()
        self.code_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.code_input.setPlaceholderText("Код администратора или пользователя")
        self.content_layout.addWidget(self.code_input)
        
        # Status
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self.content_layout.addWidget(self.status_lbl)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.login_btn = self.create_button("Войти", "primary", self.try_login)
        self.cancel_btn = self.create_button("Отмена", "secondary", self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.login_btn)
        self.content_layout.addLayout(btn_layout)
        
    def try_login(self):
        code = self.code_input.text()
        if not code:
            self.status_lbl.setText("Введите код")
            return
            
        self.login_btn.setEnabled(False)
        self.code_input.setEnabled(False)
        self.status_lbl.setText("Проверка...")
        self.status_lbl.setStyleSheet("color: #aaa;")
        
        self.worker = SettingsAuthWorker(self.security_manager, code)
        self.worker.finished.connect(self.on_check_finished)
        self.worker.start()
        
    def on_check_finished(self, role, msg, duration):
        if role:
            self.role = role
            self.accept()
        else:
            self.login_btn.setEnabled(True)
            self.code_input.setEnabled(True)
            self.code_input.clear()
            self.status_lbl.setText(msg)
            self.status_lbl.setStyleSheet("color: #e74c3c;")

class SettingsTab(QWidget):
    def __init__(self, data_manager, auth_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.auth_manager = auth_manager
        self.main_window = main_window
        self.security_manager = SecurityManager(self.data_manager)
        self.current_role = None  # admin or user
        self.update_info = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main Layout (Vertical for Top Nav)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- Top Navigation Bar ---
        self.nav_frame = QFrame()
        self.nav_frame.setObjectName("NavFrame")
        self.nav_frame.setFixedHeight(60)
        
        nav_layout = QHBoxLayout(self.nav_frame)
        nav_layout.setContentsMargins(10, 0, 10, 0)
        nav_layout.setSpacing(10)
        
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.idClicked.connect(self.on_nav_clicked)
        
        # Define Tabs
        tabs = [
            (0, "Основные", "gui/assets/icons/settings.svg"),
            (1, "Обновление", "gui/assets/icons/update.svg"),
            (2, "Вкладки", "gui/assets/icons/tabs.svg"),
            (3, "Дополнительно", "gui/assets/icons/advanced.svg"),
            (4, "Связь", "gui/assets/icons/feedback.svg")
        ]
        
        self.nav_buttons = {}
        
        for idx, text, icon_path in tabs:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(40)
            
            # Modern Tab Style
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    padding: 5px 15px;
                    color: #95a5a6;
                    font-weight: 600;
                    font-size: 14px;
                    background: transparent;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #ecf0f1;
                    background: rgba(255, 255, 255, 0.05);
                }
                QPushButton:checked {
                    background-color: #3498db;
                    color: white;
                }
            """)
            
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                
            self.nav_group.addButton(btn, idx)
            nav_layout.addWidget(btn)
            self.nav_buttons[idx] = btn
            
        nav_layout.addStretch()
        self.main_layout.addWidget(self.nav_frame)
        
        # --- Content Area ---
        self.content_stack = QStackedWidget()
        self.main_layout.addWidget(self.content_stack)
        
        # --- Pages ---
        self.create_general_page()      # Index 0
        self.create_update_page()       # Index 1
        self.create_tab_mgmt_page()     # Index 2
        self.create_advanced_page()     # Index 3
        self.create_contact_page()      # Index 4
        
        # Select first page
        self.nav_buttons[0].setChecked(True)
        self.content_stack.setCurrentIndex(0)
        
        self.apply_theme()

    def on_nav_clicked(self, index):
        self.content_stack.setCurrentIndex(index)
        self.update_nav_styles()

    def update_advanced_page_visibility(self):
        """Show/hide advanced features based on role."""
        pass # Now handled by individual auth widgets inside the tab



    def update_nav_styles(self):
        # Basic implementation to ensure button state is visually correct
        current_idx = self.content_stack.currentIndex()
        for idx, btn in self.nav_buttons.items():
            btn.setChecked(idx == current_idx)

    def apply_theme(self, theme=None):
        if not theme or isinstance(theme, str):
            theme_name = theme if isinstance(theme, str) else self.data_manager.get_setting("theme", "dark")
            theme = StyleManager.get_theme(theme_name)
            
        # Update FeedbackWidget
        if hasattr(self, 'feedback_widget'):
            self.feedback_widget.apply_theme(theme)

    # --- Page 0: General ---
    def create_general_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # License Section
        layout.addWidget(QLabel("Лицензия:"))
        
        license_layout = QHBoxLayout()
        self.license_input = QLineEdit()
        self.license_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Get real license key
        real_key = "********************"
        if self.auth_manager and self.auth_manager.current_creds:
            real_key = self.auth_manager.current_creds.get("key", real_key)
            
        self.license_input.setText(real_key)
        self.license_input.setReadOnly(True)
        self.license_input.setFixedHeight(40)
        license_layout.addWidget(self.license_input)
        
        # Show/Hide License Button
        self.toggle_license_btn = QPushButton()
        self.toggle_license_btn.setFixedSize(40, 40)
        self.toggle_license_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_license_btn.setCheckable(True)
        self._set_eye_icon(self.toggle_license_btn, EYE_OPEN_SVG)
        self.toggle_license_btn.clicked.connect(self.toggle_license_visibility)
        license_layout.addWidget(self.toggle_license_btn)
        
        layout.addLayout(license_layout)
        
        status_layout = QVBoxLayout()
        status_layout.setSpacing(5)
        self.status_lbl = QLabel("Статус: Активна")
        self.status_lbl.setStyleSheet("color: #2ecc71; font-weight: bold;")
        status_layout.addWidget(self.status_lbl)
        
        self.expiry_lbl = QLabel("Действует до: 18.12.2125 15:21")
        self.expiry_lbl.setStyleSheet("color: #7f8c8d;")
        status_layout.addWidget(self.expiry_lbl)
        layout.addLayout(status_layout)
        
        # Data Management
        layout.addWidget(QLabel("Управление данными:"))
        data_btns_layout = QHBoxLayout()
        data_btns_layout.setSpacing(10)
        
        self.export_btn = QPushButton("Экспорт профиля")
        self.export_btn.setFixedSize(150, 35)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_profile)
        
        self.import_btn = QPushButton("Импорт профиля")
        self.import_btn.setFixedSize(150, 35)
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self.import_profile)
        
        self.restore_btn = QPushButton("Восстановить")
        self.restore_btn.setFixedSize(150, 35)
        self.restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_btn.clicked.connect(self.restore_profile_wizard)
        
        data_btns_layout.addWidget(self.export_btn)
        data_btns_layout.addWidget(self.import_btn)
        data_btns_layout.addWidget(self.restore_btn)
        data_btns_layout.addStretch()
        layout.addLayout(data_btns_layout)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Theme
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Тема оформления:"))
        theme_layout.addStretch()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Темная (Dark)", "Светлая (Light)"])
        self.theme_combo.setFixedWidth(200)
        current_theme = self.data_manager.get_setting("theme", "dark")
        self.theme_combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)
        
        # --- Backup Section ---
        backup_group = QGroupBox("Резервное копирование")
        backup_layout = QVBoxLayout(backup_group)
        backup_layout.setSpacing(15)
        
        # Channel Selection
        backup_layout.addWidget(QLabel("Резервный канал (папка):"))
        channel_row = QHBoxLayout()
        
        self.backup_path_input = QLineEdit()
        self.backup_path_input.setReadOnly(True)
        self.backup_path_input.setPlaceholderText("Папка не выбрана")
        current_channel = self.data_manager.get_global_data("backup_channel", "")
        self.backup_path_input.setText(current_channel)
        
        self.btn_browse_backup = QPushButton("Обзор...")
        self.btn_browse_backup.clicked.connect(self.on_select_backup_channel)
        
        channel_row.addWidget(self.backup_path_input)
        channel_row.addWidget(self.btn_browse_backup)
        backup_layout.addLayout(channel_row)
        
        # Frequency
        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel("Периодичность:"))
        
        self.freq_combo = QComboBox()
        self.freq_options = [
            ("never", "Никогда"),
            ("1d", "Раз в день"),
            ("1w", "Раз в неделю"),
            ("2w", "Раз в 2 недели"),
            ("1m", "Раз в месяц")
        ]
        for key, text in self.freq_options:
            self.freq_combo.addItem(text, key)
            
        current_freq = self.data_manager.get_global_data("backup_frequency", "never")
        idx = next((i for i, (k, _) in enumerate(self.freq_options) if k == current_freq), 0)
        self.freq_combo.setCurrentIndex(idx)
        self.freq_combo.currentIndexChanged.connect(self.on_backup_freq_changed)
        
        freq_row.addWidget(self.freq_combo)
        freq_row.addStretch()
        backup_layout.addLayout(freq_row)
        
        # Manual Backup
        backup_action_row = QHBoxLayout()
        self.btn_backup_now = QPushButton("Создать резервную копию сейчас")
        self.btn_backup_now.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_backup_now.clicked.connect(self.on_backup_now)
        backup_action_row.addWidget(self.btn_backup_now)
        backup_action_row.addStretch()
        backup_layout.addLayout(backup_action_row)
        
        layout.addWidget(backup_group)
        
        # License Cost Logic
        price_group = QGroupBox("Автоматизация стоимости объявлений")
        price_group_layout = QVBoxLayout(price_group)
        
        # Toggle first
        auto_price_layout = QHBoxLayout()
        auto_price_layout.addWidget(QLabel("Предлагать добавление расхода при доходе:"))
        
        is_auto = self.data_manager.get_setting("listing_cost_enabled", True)
        
        self.auto_price_toggle = ToggleSwitch() 
        self.auto_price_toggle.setChecked(bool(is_auto))
        self.auto_price_toggle.setToolTip("Автоматически добавлять стоимость объявления в расход")
        self.auto_price_toggle.toggled.connect(self.on_auto_price_toggled)
        
        auto_price_layout.addWidget(self.auto_price_toggle)
        price_group_layout.addLayout(auto_price_layout)

        # Cost Input (Visible only if enabled)
        self.cost_container = QWidget()
        cost_layout = QHBoxLayout(self.cost_container)
        cost_layout.setContentsMargins(0, 0, 0, 0)
        cost_layout.addWidget(QLabel("Стоимость подачи объявления:"))
        
        current_cost = self.data_manager.get_setting("listing_cost", 0.0)
        self.price_input = QLineEdit(str(current_cost))
        self.price_input.setPlaceholderText("0.0")
        self.price_input.setFixedWidth(100)
        self.price_input.textChanged.connect(self.on_price_changed)
        cost_layout.addWidget(self.price_input)
        cost_layout.addStretch()
        
        price_group_layout.addWidget(self.cost_container)
        self.cost_container.setVisible(bool(is_auto))
        
        layout.addWidget(price_group)
        
        # Timer Settings
        layout.addWidget(QLabel("Настройки таймера:"))
        layout.addWidget(QLabel("Режим уведомлений о закрытии контрактов:"))
        
        self.notif_combo = QComboBox()
        
        self.notif_modes = [
            ("notify_keep", "Показывать уведомление (без удаления)"),
            ("silent_keep", "Отключить уведомления (без удаления)"),
            ("notify_and_delete", "Показывать уведомление и удалять")
        ]
        
        for _, mode_text in self.notif_modes:
            self.notif_combo.addItem(mode_text)
            
        current_mode = self.data_manager.get_setting("contract_notification_mode", "notify_keep")
        # Fallback for old boolean setting
        if current_mode not in [m[0] for m in self.notif_modes]:
            if self.data_manager.get_setting("auto_delete_contracts", False):
                current_mode = "notify_and_delete"
            else:
                current_mode = "notify_keep"
        
        # Set current index
        for i, (mode_key, _) in enumerate(self.notif_modes):
            if mode_key == current_mode:
                self.notif_combo.setCurrentIndex(i)
                break
                
        self.notif_combo.currentIndexChanged.connect(self.on_notif_combo_changed)
        layout.addWidget(self.notif_combo)
        
        help_lbl = QLabel("Выберите действие при истечении времени контракта.")
        help_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(help_lbl)

        layout.addStretch()
        
        # Version
        version_lbl = QLabel(f"Version: {VERSION}")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        version_lbl.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(version_lbl)
        
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0,0,0,0)
        page_layout.addWidget(scroll)
        self.content_stack.addWidget(page)

    def toggle_license_visibility(self, checked):
        if checked:
            # Refresh key from AuthManager in case it wasn't ready at init
            if self.auth_manager and self.auth_manager.current_creds:
                real_key = self.auth_manager.current_creds.get("key", "")
                if real_key:
                    self.license_input.setText(real_key)
            
            self.license_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._set_eye_icon(self.toggle_license_btn, EYE_CLOSED_SVG)
        else:
            self.license_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._set_eye_icon(self.toggle_license_btn, EYE_OPEN_SVG)

    def _set_eye_icon(self, btn, svg_data):
        renderer = QSvgRenderer(bytearray(svg_data, encoding='utf-8'))
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        btn.setIcon(QIcon(pixmap))
        btn.setText("") # Clear text if any

    def on_theme_changed(self, index):
        theme_name = "dark" if index == 0 else "light"
        self.data_manager.set_setting("theme", theme_name)
        
        if self.main_window:
            self.main_window.apply_styles()
            
        # Manually trigger apply_theme for local components that need it
        t = StyleManager.get_theme(theme_name)
        self.apply_theme(t)
            
        self.update_nav_styles()

    def on_price_changed(self, text):
        try:
            val = float(text)
            if val < 0:
                raise ValueError("Negative value")
            self.data_manager.set_setting("listing_cost", val)
            self.price_input.setStyleSheet("") # Reset style
        except ValueError:
            # Invalid input (not a number or negative)
            self.price_input.setStyleSheet("border: 1px solid red;")
            
    def on_auto_price_toggled(self, checked):
        """Handle auto-add price toggle."""
        self.data_manager.set_setting("listing_cost_enabled", checked)
        if hasattr(self, 'cost_container'):
            self.cost_container.setVisible(checked)
        
    def on_notif_combo_changed(self, index):
        if 0 <= index < len(self.notif_modes):
            mode_key = self.notif_modes[index][0]
            self.data_manager.set_setting("contract_notification_mode", mode_key)
            
            # Maintain backward compatibility
            if mode_key == "notify_and_delete":
                self.data_manager.set_setting("auto_delete_contracts", True)
            else:
                self.data_manager.set_setting("auto_delete_contracts", False)

    # --- Page 1: Update ---
    def create_update_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Центр обновлений")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #ecf0f1; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Update Card
        self.update_frame = QFrame()
        self.update_frame.setObjectName("UpdateFrame")
        self.update_frame.setStyleSheet("""
            #UpdateFrame {
                background-color: #2c3e50;
                border-radius: 12px;
                border: 1px solid #34495e;
            }
        """)
        update_layout = QVBoxLayout(self.update_frame)
        update_layout.setContentsMargins(30, 30, 30, 30)
        update_layout.setSpacing(20)
        
        # Status Icon & Text
        status_row = QHBoxLayout()
        status_row.setSpacing(20)
        
        self.status_icon_lbl = QLabel()
        self.status_icon_lbl.setFixedSize(64, 64)
        # Default icon (info/cloud)
        self.status_icon_lbl.setStyleSheet("""
            background-color: #34495e;
            border-radius: 32px;
            color: white;
            font-size: 32px;
            qproperty-alignment: AlignCenter;
        """)
        self.status_icon_lbl.setText("☁")
        
        status_text_layout = QVBoxLayout()
        self.update_title = QLabel("Проверка обновлений")
        self.update_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        
        self.update_label = QLabel("Нажмите кнопку ниже, чтобы проверить наличие новой версии.")
        self.update_label.setWordWrap(True)
        self.update_label.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        
        status_text_layout.addWidget(self.update_title)
        status_text_layout.addWidget(self.update_label)
        
        status_row.addWidget(self.status_icon_lbl)
        status_row.addLayout(status_text_layout)
        status_row.addStretch()
        
        update_layout.addLayout(status_row)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #34495e; height: 1px;")
        update_layout.addWidget(line)
        
        # Buttons Area
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(15)
        
        self.check_update_btn = QPushButton("Проверить сейчас")
        self.check_update_btn.setFixedSize(200, 45)
        self.check_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QPushButton:disabled {
                background-color: #34495e;
                color: #7f8c8d;
            }
        """)
        self.check_update_btn.clicked.connect(self.on_check_update)
        
        self.download_btn = QPushButton("Скачать и установить")
        self.download_btn.setEnabled(False) 
        self.download_btn.setVisible(False) # Hide initially
        self.download_btn.setFixedSize(220, 45)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #219150;
            }
        """)
        self.download_btn.clicked.connect(self.on_download_clicked)
        
        btns_layout.addWidget(self.check_update_btn)
        btns_layout.addWidget(self.download_btn)
        btns_layout.addStretch()
        
        update_layout.addLayout(btns_layout)
        
        layout.addWidget(self.update_frame)
        
        # Additional Info
        info_lbl = QLabel(f"Текущая версия: {VERSION}")
        info_lbl.setStyleSheet("color: #7f8c8d; margin-top: 10px;")
        layout.addWidget(info_lbl)
        
        layout.addStretch()
        self.content_stack.addWidget(page)

    def on_check_update(self):
        self.check_update_btn.setEnabled(False)
        self.check_update_btn.setText("Проверка...")
        self.update_title.setText("Поиск обновлений")
        self.update_label.setText("Подключение к серверу...")
        self.status_icon_lbl.setText("⏳")
        self.download_btn.setVisible(False)
        
        self.update_manager = UpdateManager(self.data_manager, VERSION, self.auth_manager)
        self.update_manager.check_completed.connect(self.on_update_check_finished)
        self.update_manager.update_error.connect(self.on_update_error)
        self.update_manager.check_for_updates_async(is_manual=True)

    def on_update_check_finished(self, result):
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("Проверить снова")
        
        success = result.get("success", False)
        message = result.get("message", "")
        update_found = result.get("update_found", False)
        server_ver = result.get("server_version", "?.?.?")
        
        if success:
            if update_found:
                self.update_info = result
                self.update_title.setText(f"Доступна версия {server_ver}")
                self.update_label.setText("Нажмите 'Скачать и установить' для обновления.")
                self.update_label.setStyleSheet("color: #2ecc71; font-size: 14px;")
                self.status_icon_lbl.setText("🚀")
                # Green
                self.status_icon_lbl.setStyleSheet("""
                    background-color: #2ecc71;
                    border-radius: 32px;
                    color: white;
                    font-size: 32px;
                    qproperty-alignment: AlignCenter;
                """)
                
                self.download_btn.setEnabled(True)
                self.download_btn.setVisible(True)
            else:
                self.update_info = None
                self.update_title.setText("Обновление не требуется")
                self.update_label.setText(message if message else "У вас установлена последняя версия.")
                self.update_label.setStyleSheet("color: #bdc3c7; font-size: 14px;")
                self.status_icon_lbl.setText("✅")
                # Green darker
                self.status_icon_lbl.setStyleSheet("""
                    background-color: #27ae60;
                    border-radius: 32px;
                    color: white;
                    font-size: 32px;
                    qproperty-alignment: AlignCenter;
                """)
                self.download_btn.setVisible(False)
        else:
            self.update_info = None
            self.update_title.setText("Ошибка")
            self.update_label.setText("Не удалось проверить обновления.")
            self.status_icon_lbl.setText("❌")
            # Red
            self.status_icon_lbl.setStyleSheet("""
                background-color: #c0392b;
                border-radius: 32px;
                color: white;
                font-size: 32px;
                qproperty-alignment: AlignCenter;
            """)
            self.download_btn.setVisible(False)

    def on_download_clicked(self):
        if self.update_info and self.main_window:
            self.main_window.start_update(self.update_info)

    def on_update_error(self, error_msg):
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("Повторить")
        self.update_title.setText("Ошибка")
        self.update_label.setText(f"Детали: {error_msg}")
        self.status_icon_lbl.setText("⚠️")
        # Orange
        self.status_icon_lbl.setStyleSheet("""
            background-color: #f39c12;
            border-radius: 32px;
            color: white;
            font-size: 32px;
            qproperty-alignment: AlignCenter;
        """)
        logging.error(f"Update error: {error_msg}")

    # --- Page 2: Tab Management ---
    def create_tab_mgmt_page(self):
        page = QWidget()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Отображение вкладок:"))
        header_layout.addStretch()
        self.hidden_tabs_count_lbl = QLabel("Скрыто: 0")
        self.hidden_tabs_count_lbl.setStyleSheet("color: #aaa; font-weight: bold; background: #333; padding: 5px 12px; border-radius: 12px;")
        header_layout.addWidget(self.hidden_tabs_count_lbl)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        
        # Grid Layout for Cards
        grid = QGridLayout(content)
        grid.setSpacing(15)
        
        # Definitions: (key, name, icon_key)
        self.tab_definitions = [
            ("car_rental", "Аренда авто", "car_rental"),
            ("clothes", "Покупка / Продажа", "tshirt"),
            ("mining", "Добыча", "hammer"),
            ("farm_bp", "Фарм BP", "leaf"),
            ("memo", "Блокнот", "sticky-note"),
            ("helper", "Помощник", "magic"),
            ("cooking", "Кулинария", "utensils"),
            ("analytics", "Аналитика", "chart-bar"),
            ("capital_planning", "Капитал", "coins"),
            ("timers", "Таймер", "clock")
        ]
        
        self.tab_cards = {} 
        
        for i, (key, name, icon_key) in enumerate(self.tab_definitions):
            frame = ClickableFrame()
            frame.setObjectName("TabCard")
            frame.setCursor(Qt.CursorShape.PointingHandCursor)
            frame.setFixedHeight(80)
            
            frame_layout = QHBoxLayout(frame)
            frame_layout.setContentsMargins(15, 0, 15, 0)
            frame_layout.setSpacing(15)
            
            # Icon
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(32, 32)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Resolve Icon
            icon_source = "?"
            if self.main_window and hasattr(self.main_window, 'icon_map'):
                icon_source = self.main_window.icon_map.get(icon_key, "?")
            
            # Check if it's a file path or emoji
            if os.path.exists(str(icon_source)) and (str(icon_source).endswith('.svg') or str(icon_source).endswith('.png')):
                # Load Image
                if str(icon_source).endswith('.svg'):
                    renderer = QSvgRenderer(icon_source)
                    pixmap = QPixmap(32, 32)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    renderer.render(painter)
                    painter.end()
                    icon_lbl.setPixmap(pixmap)
                else:
                    icon_lbl.setPixmap(QIcon(icon_source).pixmap(32, 32))
            else:
                # Emoji or Text
                icon_lbl.setText(str(icon_source))
                icon_lbl.setStyleSheet("font-size: 24px;")
                
            frame_layout.addWidget(icon_lbl)
            
            # Text Info
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            
            lbl_name = QLabel(name)
            lbl_name.setObjectName("TabName")
            lbl_name.setStyleSheet("font-weight: bold; font-size: 14px;")
            text_layout.addWidget(lbl_name)
            
            lbl_hint = QLabel("Нажмите, чтобы скрыть/показать")
            lbl_hint.setStyleSheet("font-size: 10px; color: #7f8c8d;")
            text_layout.addWidget(lbl_hint)
            
            frame_layout.addLayout(text_layout)
            frame_layout.addStretch()
            
            # Visual Indicator
            status_lbl = QLabel()
            status_lbl.setObjectName("StatusIcon")
            frame_layout.addWidget(status_lbl)

            # Click handler
            frame.clicked.connect(lambda ch=False, k=key: self.toggle_tab_visibility(k))
            
            self.tab_cards[key] = {
                "frame": frame,
                "status_lbl": status_lbl,
                "hint_lbl": lbl_hint,
                "name_lbl": lbl_name
            }
            
            row = i // 2
            col = i % 2
            grid.addWidget(frame, row, col)
            
        scroll.setWidget(content)
        
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 20, 20, 20)
        page_layout.setSpacing(20)
        page_layout.addLayout(header_layout)
        page_layout.addWidget(scroll)
        self.content_stack.addWidget(page)
        
        self.update_tab_cards()

    def toggle_tab_visibility(self, key):
        hidden_tabs = self.data_manager.get_setting("hidden_tabs", [])
        if key in hidden_tabs:
            hidden_tabs.remove(key)
        else:
            hidden_tabs.append(key)
        self.data_manager.set_setting("hidden_tabs", hidden_tabs)
        self.data_manager.save_data()
        self.update_tab_cards()
        if self.main_window:
            self.main_window.update_tabs_visibility()

    def update_tab_cards(self):
        hidden_tabs = self.data_manager.get_setting("hidden_tabs", [])
        self.hidden_tabs_count_lbl.setText(f"Скрыто: {len(hidden_tabs)}")
        
        for key, widgets in self.tab_cards.items():
            is_hidden = key in hidden_tabs
            
            if is_hidden:
                widgets["status_lbl"].setText("❌")
                widgets["frame"].setStyleSheet("#TabCard { background-color: rgba(231, 76, 60, 0.1); border: 1px solid #e74c3c; border-radius: 8px; }")
                widgets["hint_lbl"].setText("Скрыто")
            else:
                widgets["status_lbl"].setText("✅")
                widgets["frame"].setStyleSheet("#TabCard { background-color: rgba(46, 204, 113, 0.1); border: 1px solid #2ecc71; border-radius: 8px; }")
                widgets["hint_lbl"].setText("Активно")

    # --- Page 3: Advanced ---
    def create_advanced_page(self):
        page = QWidget()
        
        # Main Layout
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel("Расширенные настройки")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #ecf0f1; margin-bottom: 15px;")
        layout.addWidget(header)
        
        # Tab Widget for Sub-tabs
        self.advanced_tabs = QTabWidget()
        self.advanced_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #34495e;
                border-radius: 8px;
                background: #2c3e50;
                top: -1px; 
            }
            QTabBar::tab {
                background: #34495e;
                color: #bdc3c7;
                padding: 10px 25px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #2c3e50;
                color: white;
                border-bottom: 2px solid #3498db;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #3d566e;
                color: white;
            }
        """)
        
        # 1. Admin Code Sub-tab
        self.admin_auth_widget = AdminAuthWidget(self.security_manager, self.data_manager)
        self.advanced_tabs.addTab(self.admin_auth_widget, "Код администратора")
        
        # 2. Code Sub-tab
        self.code_auth_widget = CodeAuthWidget(self.security_manager)
        self.advanced_tabs.addTab(self.code_auth_widget, "Код пользователя")
        
        layout.addWidget(self.advanced_tabs)
        self.content_stack.addWidget(page)

    def open_change_admin_code_dialog(self):
        # Deprecated or moved to dashboard if needed
        dlg = ChangeCodeDialog(self, "Смена кода Администратора", self.security_manager, "admin_code")
        dlg.exec()

    def open_change_user_code_dialog(self):
        # Deprecated or moved to dashboard if needed
        dlg = ChangeCodeDialog(self, "Смена кода Пользователя", self.security_manager, "extra_code")
        dlg.exec()

    def on_select_backup_channel(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для резервных копий")
        if folder:
            self.backup_path_input.setText(folder)
            self.data_manager.set_global_data("backup_channel", folder)
            QMessageBox.information(self, "Успех", "Резервный канал установлен.")

    def on_backup_freq_changed(self, index):
        key = self.freq_options[index][0]
        self.data_manager.set_global_data("backup_frequency", key)

    def on_backup_now(self):
        channel = self.data_manager.get_global_data("backup_channel", "")
        try:
            self.data_manager.create_backup(extra_channel=channel)
            QMessageBox.information(self, "Успех", "Резервная копия успешно создана.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать копию:\n{str(e)}")

    def reset_app_settings(self):
        reply = QMessageBox.question(
            self, "Сброс настроек", 
            "Вы уверены? Это сбросит тему, скрытые вкладки и другие настройки интерфейса.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.data_manager.set_setting("theme", "dark")
            self.data_manager.set_setting("hidden_tabs", [])
            QMessageBox.information(self, "Сброс", "Настройки сброшены. Перезапустите приложение.")

    # --- Page 4: Contact ---
    def create_contact_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.feedback_widget = FeedbackWidget(self.data_manager, self.auth_manager, self.main_window)
        layout.addWidget(self.feedback_widget)
        
        self.content_stack.addWidget(page)

    # --- Export / Import Logic ---
    def export_profile(self):
        profile = self.data_manager.get_active_profile()
        if not profile:
            QMessageBox.warning(self, "Ошибка", "Нет активного профиля для экспорта.")
            return

        # Sanitize filename
        safe_name = "".join([c for c in profile.get('name', 'unnamed') if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт профиля", 
            f"profile_{safe_name}.json", 
            "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            # Check permissions
            if not os.access(os.path.dirname(file_path), os.W_OK):
                raise PermissionError("Нет прав на запись в выбранную папку.")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Успех", "Профиль успешно экспортирован.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")

    def import_profile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт профиля", "", "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError("Файл не найден.")
                
            if not os.access(file_path, os.R_OK):
                raise PermissionError("Нет прав на чтение файла.")

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validation
            required_keys = ["id", "name"]
            if not isinstance(data, dict) or not all(key in data for key in required_keys):
                raise ValueError("Некорректный формат файла профиля. Отсутствуют обязательные поля (id, name).")

            # Check for duplicate ID
            profiles = self.data_manager.get_all_profiles()
            existing = next((p for p in profiles if p["id"] == data["id"]), None)

            if existing:
                reply = QMessageBox.question(
                    self, "Дубликат профиля",
                    f"Профиль '{existing['name']}' с таким ID уже существует.\nПерезаписать его?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Update existing
                    for i, p in enumerate(profiles):
                        if p["id"] == data["id"]:
                            profiles[i] = data
                            break
                    QMessageBox.information(self, "Успех", f"Профиль '{data['name']}' успешно обновлен.")
                else:
                    # Create copy
                    data["id"] = str(uuid.uuid4())
                    data["name"] = f"{data['name']} (Копия)"
                    profiles.append(data)
                    QMessageBox.information(self, "Успех", f"Профиль импортирован как '{data['name']}'")
            else:
                profiles.append(data)
                QMessageBox.information(self, "Успех", f"Профиль '{data['name']}' успешно импортирован.")

            self.data_manager.save_data()
            
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Ошибка", "Файл поврежден или не является корректным JSON.")
        except ValueError as ve:
            QMessageBox.critical(self, "Ошибка", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать профиль:\n{str(e)}")

    def restore_profile_wizard(self):
        """Open the profile restore wizard."""
        try:
            dialog = RestoreProfileDialog(self, self.data_manager)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть мастер восстановления: {e}")

