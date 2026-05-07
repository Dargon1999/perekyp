from PyQt5 import QtWidgets, QtCore
from widgets.common import CommonLogger, ScriptController, SettingsManager, auto_detect_region, CommonUI
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
from widgets.mem_reduct_widget import MemReductWidget
from widgets.admin_panel import AdminPanel

class SettingsPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    TARGET_SLIDER_HEIGHT = 50 

    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        title = QtWidgets.QLabel("⚙️ Настройки")
        title.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            margin-top: 5px;
            background: none;
        """)
        layout.addWidget(title)
        
        settings_group, settings_layout = CommonUI.create_settings_group("⚠️ Для применения настроек нужно перезайти!")

        hover_off_on, self.switch_hover = CommonUI.create_switch_header("Звук наведения на модули", "🔊")
        volume_hover_layout, self.volume_hover, self.volume_hover_get = CommonUI.create_slider_row("Громкость звука наведения:", 0, 100, 35, step=1, suffix="")
        
        self.volume_hover_container = QtWidgets.QWidget()
        self.volume_hover_container.setLayout(volume_hover_layout)
        
        is_hover_on = self.switch_hover.isChecked() if hasattr(self.switch_hover, 'isChecked') else True
        self.volume_hover_container.setMaximumHeight(self.TARGET_SLIDER_HEIGHT if is_hover_on else 0)
        self.volume_hover_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed) 

        click_off_on, self.switch_click = CommonUI.create_switch_header("Звук клика по модулям", "🔔") 
        volume_click_layout, self.volume_click, self.volume_click_get = CommonUI.create_slider_row("Громкость клика:", 0, 100, 45, step=1, suffix="")

        self.volume_click_container = QtWidgets.QWidget()
        self.volume_click_container.setLayout(volume_click_layout)

        is_click_on = self.switch_click.isChecked() if hasattr(self.switch_click, 'isChecked') else True
        self.volume_click_container.setMaximumHeight(self.TARGET_SLIDER_HEIGHT if is_click_on else 0)
        self.volume_click_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed) 

        settings_layout.addLayout(hover_off_on)
        settings_layout.addWidget(self.volume_hover_container)

        settings_layout.addLayout(click_off_on)
        settings_layout.addWidget(self.volume_click_container)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # --- Дополнительно ---
        extra_title = QtWidgets.QLabel("➕ Дополнительно")
        extra_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin-top: 15px;")
        layout.addWidget(extra_title)

        self.mem_reduct = MemReductWidget()
        layout.addWidget(self.mem_reduct)

        # --- Админ панель ---
        self.admin_code_input = QtWidgets.QLineEdit()
        self.admin_code_input.setPlaceholderText("Введите код администратора...")
        self.admin_code_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.admin_code_input.setStyleSheet("background: #222; color: white; border: 1px solid #444; border-radius: 4px; padding: 5px;")
        self.admin_code_input.textChanged.connect(self._check_admin_code)
        layout.addWidget(self.admin_code_input)

        self.admin_panel = AdminPanel()
        self.admin_panel.setVisible(False)
        layout.addWidget(self.admin_panel)

        layout.addStretch()

        self.switch_hover.clicked.connect(lambda checked: self.animate_container(checked, self.volume_hover_container, 'hover'))
        self.switch_hover.clicked.connect(self.handle_toggle)
        self.switch_click.clicked.connect(lambda checked: self.animate_container(checked, self.volume_click_container, 'click'))
        self.switch_click.clicked.connect(self.handle_toggle)
        self.volume_hover.valueChanged.connect(self.handle_toggle_slider)
        self.volume_click.valueChanged.connect(self.handle_toggle_slider)

    def handle_toggle(self):
        self._save_settings()

    def _load_settings(self):
        hover_state = self.settings.get("settings", "switch_hover", True)
        click_state = self.settings.get("settings", "switch_click", True)
        volume_hover = self.settings.get("settings", "volume_hover", 35)
        volume_click = self.settings.get("settings", "volume_click", 45)

        self.volume_hover.setValue(int(volume_hover))
        self.volume_click.setValue(int(volume_click))
        self.switch_hover.setChecked(hover_state)
        self.switch_click.setChecked(click_state)

    def handle_toggle_slider(self):
        self.settings.save_group("settings", {
            "volume_hover": self.volume_hover_get(),
            "volume_click": self.volume_click_get(),
        })

    def _save_settings(self):
        self.settings.save_group("settings", {
            "switch_hover": self.switch_hover.isChecked(),
            "switch_click": self.switch_click.isChecked(),
        })

    def _check_admin_code(self, text):
        # В реальном приложении код должен быть захеширован или проверяться на сервере
        if text == "ADMIN777": # Пример кода
            self.admin_panel.setVisible(True)
            self.admin_code_input.setStyleSheet("background: #004400; color: white; border: 1px solid #00FF00;")
            CommonLogger.log("[Admin] Панель администратора разблокирована")
        else:
            self.admin_panel.setVisible(False)
            self.admin_code_input.setStyleSheet("background: #222; color: white; border: 1px solid #444;")

    def animate_container(self, checked, container: QtWidgets.QWidget, name: str):
        anim_attr_name = f'animation_{name}'

        if hasattr(self, anim_attr_name) and getattr(self, anim_attr_name).state() == QPropertyAnimation.Running:
            getattr(self, anim_attr_name).stop()

        animation = QPropertyAnimation(container, b"maximumHeight")
        setattr(self, anim_attr_name, animation)
        
        animation.setDuration(300) 
        animation.setEasingCurve(QEasingCurve.InOutQuad)

        if checked:
            animation.setStartValue(0)
            animation.setEndValue(self.TARGET_SLIDER_HEIGHT)
            container.setMinimumHeight(0) 
        else:
            animation.setStartValue(container.height())
            animation.setEndValue(0)
            
        animation.start()