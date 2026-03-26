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
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QTimer
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
        
        # Connect signals
        self.data_manager.data_changed.connect(self.update_storage_path_info)
        
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
            (4, "Связь", "gui/assets/icons/feedback.svg"),
            (5, "Информация", "gui/assets/icons/info.svg")
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
        self.create_info_page()         # Index 5
        
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
        
        # --- App Data Path Section ---
        path_group = QGroupBox("Путь к данным приложения")
        path_layout = QVBoxLayout(path_group)
        path_layout.setSpacing(10)
        
        path_info_lbl = QLabel("Все данные и настройки сохраняются в следующей папке:")
        path_info_lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        path_layout.addWidget(path_info_lbl)
        
        path_row = QHBoxLayout()
        self.storage_path_input = QLineEdit()
        self.storage_path_input.setReadOnly(True)
        self.storage_path_input.setFixedHeight(35)
        self.storage_path_input.setCursor(Qt.CursorShape.IBeamCursor)
        self.storage_path_input.setToolTip("Нажмите, чтобы выделить путь")
        path_row.addWidget(self.storage_path_input)
        
        self.copy_path_btn = QPushButton("Копировать")
        self.copy_path_btn.setFixedSize(100, 35)
        self.copy_path_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_path_btn.clicked.connect(self.copy_storage_path)
        path_row.addWidget(self.copy_path_btn)
        
        self.open_path_btn = QPushButton("Открыть")
        self.open_path_btn.setFixedSize(100, 35)
        self.open_path_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_path_btn.clicked.connect(self.open_storage_path)
        path_row.addWidget(self.open_path_btn)
        
        path_layout.addLayout(path_row)
        
        self.path_status_lbl = QLabel("")
        self.path_status_lbl.setStyleSheet("font-size: 11px;")
        path_layout.addWidget(self.path_status_lbl)
        
        layout.addWidget(path_group)
        
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
        self.theme_combo.addItems(["Темная (Dark)", "Светлая (Light)", "Тёмно-синяя (Dark Blue)"])
        self.theme_combo.setFixedWidth(200)
        current_theme = self.data_manager.get_setting("theme", "dark")
        if current_theme == "dark": self.theme_combo.setCurrentIndex(0)
        elif current_theme == "light": self.theme_combo.setCurrentIndex(1)
        elif current_theme == "dark_blue": self.theme_combo.setCurrentIndex(2)
        
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)
        
        # --- Interactive Color Palette ---
        palette_group = QGroupBox("Интерактивная цветовая палитра (Акцент)")
        palette_layout = QVBoxLayout(palette_group)
        
        palette_scroll = QScrollArea()
        palette_scroll.setWidgetResizable(True)
        palette_scroll.setFixedHeight(80)
        palette_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        palette_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        palette_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        palette_content = QWidget()
        palette_hbox = QHBoxLayout(palette_content)
        palette_hbox.setContentsMargins(5, 5, 5, 5)
        palette_hbox.setSpacing(10)
        
        # Predefined colors for palette
        colors = [
            "#3498db", "#2ecc71", "#e74c3c", "#f1c40f", "#9b59b6", 
            "#1abc9c", "#e67e22", "#34495e", "#f39c12", "#d35400",
            "#c0392b", "#8e44ad", "#2980b9", "#27ae60", "#16a085"
        ]
        
        self.color_btns = []
        for color_hex in colors:
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {color_hex}; border-radius: 20px; border: 2px solid transparent;")
            btn.clicked.connect(lambda checked, c=color_hex: self.on_palette_color_selected(c))
            palette_hbox.addWidget(btn)
            self.color_btns.append(btn)
            
        palette_hbox.addStretch()
        palette_scroll.setWidget(palette_content)
        palette_layout.addWidget(palette_scroll)
        
        # Current color preview and custom hex input
        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("Выбранный акцент:"))
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(24, 24)
        self.color_preview.setStyleSheet(f"background-color: {self.data_manager.get_setting('accent_color', '#3498db')}; border-radius: 12px;")
        preview_row.addWidget(self.color_preview)
        
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("#HEX")
        self.hex_input.setFixedWidth(80)
        self.hex_input.setText(self.data_manager.get_setting("accent_color", "#3498db"))
        self.hex_input.textChanged.connect(self.on_palette_color_selected)
        preview_row.addWidget(self.hex_input)
        preview_row.addStretch()
        palette_layout.addLayout(preview_row)
        
        layout.addWidget(palette_group)
        
        # --- Header Customization Section ---
        header_group = QGroupBox("Персонализация заголовка")
        header_group_layout = QVBoxLayout(header_group)
        header_group_layout.setSpacing(10)
        
        # GTA 5 RP Color
        gta_color_layout = QHBoxLayout()
        gta_color_layout.addWidget(QLabel("Цвет 'GTA 5 RP':"))
        gta_color_layout.addStretch()
        self.gta_color_input = QLineEdit()
        self.gta_color_input.setFixedWidth(100)
        self.gta_color_input.setPlaceholderText("#ffffff")
        current_gta_color = self.data_manager.get_setting("header_gta_color", "#ffffff")
        self.gta_color_input.setText(current_gta_color)
        self.gta_color_input.textChanged.connect(self.on_header_customization_changed)
        gta_color_layout.addWidget(self.gta_color_input)
        header_group_layout.addLayout(gta_color_layout)
        
        # DARGON Color
        dargon_color_layout = QHBoxLayout()
        dargon_color_layout.addWidget(QLabel("Цвет 'Dargon':"))
        dargon_color_layout.addStretch()
        self.dargon_color_input = QLineEdit()
        self.dargon_color_input.setFixedWidth(100)
        self.dargon_color_input.setPlaceholderText("#3b82f6")
        current_dargon_color = self.data_manager.get_setting("header_dargon_color", "#3b82f6")
        self.dargon_color_input.setText(current_dargon_color)
        self.dargon_color_input.textChanged.connect(self.on_header_customization_changed)
        dargon_color_layout.addWidget(self.dargon_color_input)
        header_group_layout.addLayout(dargon_color_layout)
        
        # Show/Hide DARGON
        show_dargon_layout = QHBoxLayout()
        show_dargon_layout.addWidget(QLabel("Показывать логотип 'Dargon':"))
        show_dargon_layout.addStretch()
        self.show_dargon_toggle = ToggleSwitch()
        current_show_dargon = self.data_manager.get_setting("header_show_dargon", True)
        self.show_dargon_toggle.setChecked(current_show_dargon)
        self.show_dargon_toggle.toggled.connect(self.on_header_customization_changed)
        show_dargon_layout.addWidget(self.show_dargon_toggle)
        header_group_layout.addLayout(show_dargon_layout)
        
        layout.addWidget(header_group)
        
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
        
        # Manual Balance Edit Logic
        balance_group = QGroupBox("Управление балансом")
        balance_group_layout = QVBoxLayout(balance_group)
        
        manual_edit_layout = QHBoxLayout()
        manual_edit_layout.addWidget(QLabel("Разрешить ручное редактирование баланса:"))
        
        is_manual_edit = self.data_manager.get_setting("allowManualBalanceEdit", False)
        
        self.manual_edit_toggle = ToggleSwitch()
        self.manual_edit_toggle.setChecked(bool(is_manual_edit))
        self.manual_edit_toggle.setToolTip("Разрешить редактирование баланса по двойному клику во всех разделах")
        self.manual_edit_toggle.setAccessibleName("Разрешить ручное редактирование баланса")
        self.manual_edit_toggle.toggled.connect(self.on_manual_edit_toggled)
        
        manual_edit_layout.addWidget(self.manual_edit_toggle)
        manual_edit_layout.addStretch()
        balance_group_layout.addLayout(manual_edit_layout)

        # Cost of Appearance Visibility (Task 2)
        coa_layout = QHBoxLayout()
        coa_layout.addWidget(QLabel("Отображать стоимость появления в списке покупок:"))
        
        is_coa = self.data_manager.get_setting("showCostOfAppearance", False)
        
        self.coa_toggle = ToggleSwitch()
        self.coa_toggle.setChecked(bool(is_coa))
        self.coa_toggle.setToolTip("Показывать столбец 'Стоимость появления' в разделе 'Покупка/Продажа'")
        self.coa_toggle.setAccessibleName("Отображать стоимость появления")
        self.coa_toggle.toggled.connect(self.on_coa_toggled)
        
        coa_layout.addWidget(self.coa_toggle)
        coa_layout.addStretch()
        balance_group_layout.addLayout(coa_layout)

        # Show Buy Price in Inventory (Task 4)
        sbp_layout = QHBoxLayout()
        sbp_layout.addWidget(QLabel("Отображать цену покупки в списке склада:"))
        
        is_sbp = self.data_manager.get_setting("showBuyPriceInInventory", True)
        
        self.sbp_toggle = ToggleSwitch()
        self.sbp_toggle.setChecked(bool(is_sbp))
        self.sbp_toggle.setToolTip("Показывать цену покупки под названием товара во вкладке «Покупка/Продажа»")
        self.sbp_toggle.setAccessibleName("Отображать цену покупки")
        self.sbp_toggle.toggled.connect(self.on_sbp_toggled)
        
        sbp_layout.addWidget(self.sbp_toggle)
        sbp_layout.addStretch()
        balance_group_layout.addLayout(sbp_layout)
        
        layout.addWidget(balance_group)

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
        layout.addWidget(QLabel("Стартовая вкладка:"))
        self.startup_tab_combo = QComboBox()
        
        # Mapping for startup tabs
        self.tab_options = [
            ("car_rental", "Аренда авто"),
            ("clothes", "Покупка / Продажа"),
            ("mining", "Добыча"),
            ("farm_bp", "Фарм BP"),
            ("memo", "Блокнот"),
            ("helper", "Помощник"),
            ("cooking", "Кулинария"),
            ("analytics", "Аналитика"),
            ("capital_planning", "Капитал"),
            ("timers", "Таймер"),
            ("fishing", "Рыбалка"),
            ("settings", "Настройки")
        ]
        
        for _, opt_text in self.tab_options:
            self.startup_tab_combo.addItem(opt_text)
            
        current_startup = self.data_manager.get_setting("startup_tab", "car_rental")
        for i, (opt_key, _) in enumerate(self.tab_options):
            if opt_key == current_startup:
                self.startup_tab_combo.setCurrentIndex(i)
                break
                
        self.startup_tab_combo.currentIndexChanged.connect(self.on_startup_tab_changed)
        layout.addWidget(self.startup_tab_combo)
        
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
        
        self.update_storage_path_info()
        
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
            # Refresh key from AuthManager
            real_key = ""
            if self.auth_manager:
                # Try to get from current creds
                if self.auth_manager.current_creds:
                    real_key = self.auth_manager.current_creds.get("key", "")
                
                # If still empty, try to load from session file directly
                if not real_key:
                    session = self.auth_manager.load_session()
                    if session:
                        real_key = session.get("key", "")
            
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

    def update_storage_path_info(self):
        """Update storage path display and validate it."""
        try:
            path = self.data_manager.get_data_dir()
            self.storage_path_input.setText(path)
            
            if os.path.exists(path):
                if os.access(path, os.W_OK):
                    self.path_status_lbl.setText("✅ Путь доступен для записи")
                    self.path_status_lbl.setStyleSheet("color: #2ecc71; font-size: 11px;")
                else:
                    self.path_status_lbl.setText("⚠️ Путь доступен только для чтения")
                    self.path_status_lbl.setStyleSheet("color: #f1c40f; font-size: 11px;")
            else:
                self.path_status_lbl.setText("❌ Папка не найдена")
                self.path_status_lbl.setStyleSheet("color: #e74c3c; font-size: 11px;")
        except Exception as e:
            self.path_status_lbl.setText(f"❌ Ошибка проверки пути: {str(e)}")
            self.path_status_lbl.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def copy_storage_path(self):
        """Copy storage path to clipboard."""
        path = self.storage_path_input.text()
        if path:
            QApplication.clipboard().setText(path)
            old_text = self.copy_path_btn.text()
            self.copy_path_btn.setText("Скопировано!")
            self.copy_path_btn.setEnabled(False)
            QTimer.singleShot(2000, lambda: self._reset_copy_btn(old_text))

    def _reset_copy_btn(self, text):
        self.copy_path_btn.setText(text)
        self.copy_path_btn.setEnabled(True)

    def open_storage_path(self):
        """Open storage path in file explorer."""
        path = self.storage_path_input.text()
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось открыть папку. Путь не существует.")

    def on_coa_toggled(self, checked):
        self.data_manager.set_setting("showCostOfAppearance", checked)
        self.data_manager.save_data()
        
        # Notify other components immediately
        self.data_manager.data_changed.emit()

    def on_sbp_toggled(self, checked):
        self.data_manager.set_setting("showBuyPriceInInventory", checked)
        self.data_manager.save_data()
        
        # Notify other components immediately
        self.data_manager.data_changed.emit()

    def on_theme_changed(self, index):
        if index == 0: theme_name = "dark"
        elif index == 1: theme_name = "light"
        else: theme_name = "dark_blue"
        
        self.data_manager.set_setting("theme", theme_name)
        
        if self.main_window:
            self.main_window.apply_styles()
            
        # Manually trigger apply_theme for local components that need it
        t = StyleManager.get_theme(theme_name)
        self.apply_theme(t)
            
        self.update_nav_styles()

    def on_palette_color_selected(self, color_hex):
        """Update accent color and apply theme."""
        if not color_hex.startswith("#"):
            color_hex = "#" + color_hex
            
        if len(color_hex) != 7:
            return # Invalid hex
            
        self.data_manager.set_setting("accent_color", color_hex)
        self.data_manager.save_data()
        
        # Update UI preview
        self.color_preview.setStyleSheet(f"background-color: {color_hex}; border-radius: 12px;")
        if self.hex_input.text().lower() != color_hex.lower():
            self.hex_input.setText(color_hex)
            
        # Apply styles globally
        if self.main_window:
            self.main_window.apply_styles()
            
        # Update current tab UI
        current_theme_name = self.data_manager.get_setting("theme", "dark")
        t = StyleManager.get_theme(current_theme_name)
        self.apply_theme(t)

    def on_header_customization_changed(self):
        """Update header colors and visibility."""
        gta_color = self.gta_color_input.text()
        dargon_color = self.dargon_color_input.text()
        show_dargon = self.show_dargon_toggle.isChecked()
        
        # Basic hex validation
        if not gta_color.startswith("#"): gta_color = "#" + gta_color
        if not dargon_color.startswith("#"): dargon_color = "#" + dargon_color
        
        self.data_manager.set_setting("header_gta_color", gta_color)
        self.data_manager.set_setting("header_dargon_color", dargon_color)
        self.data_manager.set_setting("header_show_dargon", show_dargon)
        self.data_manager.save_data()
        
        # Refresh title bar if possible
        if self.main_window and hasattr(self.main_window, 'title_bar'):
            current_theme = self.data_manager.get_setting("theme", "dark")
            self.main_window.title_bar.set_theme(current_theme)

    def on_manual_edit_toggled(self, checked):
        self.data_manager.set_setting("allowManualBalanceEdit", checked)
        self.data_manager.save_data()
        
        # Notify other components immediately
        self.data_manager.data_changed.emit()

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
        
    def on_startup_tab_changed(self, index):
        if 0 <= index < len(self.tab_options):
            mode_key = self.tab_options[index][0]
            self.data_manager.set_setting("startup_tab", mode_key)
            self.data_manager.save_data()

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
            ("timers", "Таймер", "clock"),
            ("fishing", "Рыбалка", "fish")
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

    # --- Page 5: Information ---
    def create_info_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content = QWidget()
        content.setObjectName("InfoContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)
        
        # 🌟 1. Dynamic Modern Header
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_card.setStyleSheet("""
            #HeaderCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e293b, stop:1 #0f172a);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(30, 30, 30, 30)
        
        logo_lbl = QLabel("🐉")
        logo_lbl.setStyleSheet("font-size: 64px;")
        header_layout.addWidget(logo_lbl)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(5)
        app_title = QLabel("GTA 5 RP Dargon")
        app_title.setStyleSheet("font-size: 32px; font-weight: 900; color: #f59e0b; letter-spacing: 1px;")
        title_box.addWidget(app_title)
        
        version_badge = QLabel("STABLE RELEASE")
        version_badge.setStyleSheet("""
            background-color: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
            font-size: 12px;
            font-weight: 800;
            padding: 4px 12px;
            border-radius: 10px;
            border: 1px solid rgba(59, 130, 246, 0.3);
        """)
        version_badge.setFixedWidth(130)
        title_box.addWidget(version_badge)
        
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        # Quick Navigation Tool
        nav_group = QFrame()
        nav_group.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 12px; padding: 10px;")
        nav_lay = QHBoxLayout(nav_group)
        
        for icon, target in [("📊", "Учёт"), ("🎣", "Рыбалка"), ("⏳", "Фарм"), ("🛡️", "Защита")]:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"Перейти к разделу {target}")
            btn.setStyleSheet("QPushButton { background: transparent; font-size: 20px; border-radius: 8px; } QPushButton:hover { background: rgba(255,255,255,0.1); }")
            nav_lay.addWidget(btn)
        header_layout.addWidget(nav_group)
        
        content_layout.addWidget(header_card)

        # 🗺️ 2. Grid-based Module Explorer (Responsive Mock)
        modules_title = QLabel("🗺️ ИЕРАРХИЯ МОДУЛЕЙ СИСТЕМЫ")
        modules_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #3b82f6; margin-left: 5px;")
        content_layout.addWidget(modules_title)
        
        explorer_layout = QGridLayout()
        explorer_layout.setSpacing(20)
        
        modules = [
            ("📊 Финансовый Учёт", "Аналитика доходов и расходов, графики окупаемости бизнеса, экспорт в CSV.", "#3b82f6"),
            ("🎣 Система Рыбалки", "Автоматические таймеры клёва, база цен на улов, расчет износа снаряжения.", "#10b981"),
            ("⛏️ Модуль Добычи", "Оптимизация маршрутов (Шахта/Порт), трекер ресурсов, калькулятор веса.", "#f59e0b"),
            ("⏳ Фарм Battle Pass", "Интеллектуальный трекер заданий, контроль времени онлайна, уведомления.", "#ef4444"),
            ("🛡️ Центр Защиты", "Привязка по HWID, шифрование локальных данных, облачная синхронизация.", "#8b5cf6"),
            ("⚙️ Мастер Настройки", "Персонализация интерфейса, выбор цветовых схем, управление путями.", "#64748b")
        ]
        
        for i, (m_title, m_desc, m_color) in enumerate(modules):
            m_card = QFrame()
            m_card.setStyleSheet(f"""
                QFrame {{
                    background-color: #1e293b;
                    border-radius: 16px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    padding: 20px;
                }}
                QFrame:hover {{
                    border: 1px solid {m_color};
                    background-color: #24334d;
                }}
            """)
            m_lay = QVBoxLayout(m_card)
            m_lay.setSpacing(10)
            
            t_lbl = QLabel(m_title)
            t_lbl.setStyleSheet(f"font-weight: 800; color: #f1f5f9; font-size: 16px;")
            m_lay.addWidget(t_lbl)
            
            d_lbl = QLabel(m_desc)
            d_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 140%;")
            d_lbl.setWordWrap(True)
            m_lay.addWidget(d_lbl)
            
            # Action Footer
            footer = QHBoxLayout()
            copy_btn = QPushButton("Копировать")
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setStyleSheet(f"color: {m_color}; font-weight: 700; border: none; background: transparent;")
            copy_btn.clicked.connect(lambda checked, text=m_desc: QApplication.clipboard().setText(text))
            footer.addStretch()
            footer.addWidget(copy_btn)
            m_lay.addLayout(footer)
            
            explorer_layout.addWidget(m_card, i // 2, i % 2)
            
        content_layout.addLayout(explorer_layout)

        # 📖 3. Interactive Help & Navigation
        help_card = QFrame()
        help_card.setStyleSheet("background: #0f172a; border-radius: 16px; padding: 20px;")
        help_lay = QHBoxLayout(help_card)
        
        msg_lbl = QLabel("Нужна помощь в освоении системы?")
        msg_lbl.setStyleSheet("font-weight: 700; color: #f8fafc; font-size: 15px;")
        help_lay.addWidget(msg_lbl)
        help_lay.addStretch()
        
        faq_btn = QPushButton("Открыть FAQ")
        faq_btn.setFixedSize(140, 40)
        faq_btn.setStyleSheet("background: #3b82f6; color: white; font-weight: 800; border-radius: 10px;")
        faq_btn.clicked.connect(self.show_faq)
        help_lay.addWidget(faq_btn)
        
        content_layout.addWidget(help_card)
        
        # Footer
        footer_lbl = QLabel(f"MoneyTracker Modern UI • 2026 • Build 1.0.0")
        footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_lbl.setStyleSheet("color: #475569; font-size: 11px; margin-top: 10px;")
        content_layout.addWidget(footer_lbl)
        
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self.content_stack.addWidget(page)

    def show_changelog(self):
        msg = f"""<b>История обновлений {VERSION}:</b><br><br>
        • 🚀 Полностью обновлен интерфейс настроек связи<br>
        • 🛠️ Исправлена видимость стрелок в темной теме (Фарм БП)<br>
        • 🛡️ Расширена панель администратора (Мониторинг ПК, SMS Центр)<br>
        • 📖 Улучшен раздел информации и документации<br>
        • 🔗 Добавлена интеграция с Discord Webhook для отчетов<br>
        • 📂 Добавлено отображение абсолютных путей сохранения"""
        QMessageBox.information(self, "Чейнджлог", msg)

    def show_faq(self):
        faq = """<b>FAQ - Часто задаваемые вопросы:</b><br><br>
        <b>Q: Как изменить тему оформления?</b><br>
        A: Перейдите в Настройки -> Основные -> Тема оформления.<br><br>
        <b>Q: Где хранятся мои данные?</b><br>
        A: Путь к данным указан во вкладке 'Основные' в блоке 'Путь к данным'.<br><br>
        <b>Q: Как сбросить HWID?</b><br>
        A: Обратитесь в поддержку через вкладку 'Связь'.<br><br>
        <b>Q: Бот не нажимает клавиши, что делать?</b><br>
        A: Запустите программу от имени администратора."""
        QMessageBox.information(self, "FAQ", faq)

    def _add_info_section(self, parent_layout, title, items):
        section_frame = QFrame()
        section_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        section_layout = QVBoxLayout(section_frame)
        section_layout.setSpacing(12)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #3498db; margin-bottom: 10px;")
        section_layout.addWidget(title_lbl)
        
        for name, desc in items:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(15)
            
            name_lbl = QLabel(f"• {name}")
            name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #f1c40f; min-width: 150px;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
            
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet("font-size: 13px; color: #bdc3c7;")
            desc_lbl.setWordWrap(True)
            
            item_layout.addWidget(name_lbl)
            item_layout.addWidget(desc_lbl, stretch=1)
            section_layout.addLayout(item_layout)
        
        parent_layout.addWidget(section_frame)

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

