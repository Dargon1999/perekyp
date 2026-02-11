from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, 
    QLabel, QLineEdit, QMessageBox, QWidget, QFrame, QGraphicsDropShadowEffect,
    QInputDialog
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor
from gui.title_bar import CustomTitleBar
from gui.custom_dialogs import AlertDialog, ConfirmationDialog, StyledDialogBase

from gui.styles import StyleManager

class AddProfileDialog(QDialog):
    def __init__(self, parent=None, edit_mode=False, current_name="", current_capital=0.0):
        super().__init__(parent)
        self.edit_mode = edit_mode
        
        # Determine theme colors from StyleManager
        self.theme = StyledDialogBase._theme
        t = StyleManager.get_theme(self.theme)
        
        self.bg_color = t['bg_secondary']
        self.border_color = t['border']
        self.input_bg = t['input_bg']
        self.input_border = t['border']
        self.text_color = t['text_main']
        self.label_color = t['text_secondary']
        self.shadow_color = QColor(0, 0, 0, 100) if self.theme == "dark" else QColor(0, 0, 0, 30)
        self.input_focus = t['accent']
        self.accent = t['accent']
        self.success = t['success']
        self.danger = t['danger']
        
        # Frameless Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 350)
        
        # Main Layout with Shadow
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Container
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {self.bg_color};
                border-radius: 10px;
                border: 1px solid {self.border_color};
            }}
        """)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(self.shadow_color)
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)
        
        self.layout.addWidget(self.container)
        
        # Container Layout
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        # Title Bar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.title_label.setText("Редактировать профиль" if edit_mode else "Создать профиль")
        self.title_bar.set_theme(self.theme)
        self.title_bar.profile_btn.hide()
        self.title_bar.active_profile_label.hide()
        self.title_bar.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        self.container_layout.addWidget(self.title_bar)
        
        # Content
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        self.container_layout.addWidget(self.content_widget)
        
        self.setup_ui(current_name, current_capital)

    def setup_ui(self, name, capital):
        # Name
        name_container = self.create_input_container("Название профиля")
        self.name_input = QLineEdit(name)
        self.style_input(self.name_input)
        name_container.layout().addWidget(self.name_input)
        self.content_layout.addWidget(name_container)
        
        # Capital
        capital_container = self.create_input_container("Стартовый капитал ($)")
        self.capital_input = QLineEdit(str(capital) if capital else "")
        self.capital_input.setPlaceholderText("0")
        self.style_input(self.capital_input)
        capital_container.layout().addWidget(self.capital_input)
        self.content_layout.addWidget(capital_container)
        
        self.content_layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        save_btn = QPushButton("Сохранить" if self.edit_mode else "Создать")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.success};
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 15px;
                border: 1px solid {self.success};
            }}
            QPushButton:hover {{
                background-color: {self.success}1A;
            }}
        """)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.danger};
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 15px;
                border: 1px solid {self.danger};
            }}
            QPushButton:hover {{
                background-color: {self.danger}1A;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        self.content_layout.addLayout(btn_layout)

    def create_input_container(self, label_text):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {self.label_color}; font-size: 14px; font-weight: 500;")
        layout.addWidget(label)
        
        return widget

    def style_input(self, widget):
        widget.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {self.input_border};
                border-radius: 8px;
                background-color: {self.input_bg};
                color: {self.text_color};
                padding-left: 10px;
                font-size: 15px;
                selection-background-color: {self.input_focus};
            }}
            QLineEdit:focus {{ border: 1px solid {self.input_focus}; }}
        """)

    def get_data(self):
        try:
            capital = float(self.capital_input.text())
        except ValueError:
            capital = 0.0
        return self.name_input.text(), capital

class ProfileDialog(QDialog):
    def __init__(self, parent, data_manager):
        super().__init__(parent)
        self.data_manager = data_manager
        
        # Determine theme colors from StyleManager
        self.theme = StyledDialogBase._theme
        t = StyleManager.get_theme(self.theme)
        
        self.bg_color = t['bg_secondary']
        self.border_color = t['border']
        self.list_bg = t['bg_secondary'] # Changed from input_bg to match dialog background
        self.list_border = t['border']
        self.list_item_border = t['border']
        self.text_color = t['text_main']
        self.hover_color = t['bg_tertiary']
        self.selected_bg = t['accent']
        self.selected_text = "white"
        self.shadow_color = QColor(0, 0, 0, 100) if self.theme == "dark" else QColor(0, 0, 0, 30)
        self.success = t['success']
        self.danger = t['danger']
        self.warning = t['warning']
        self.info = t['accent']

        # Frameless Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(500, 600)
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Container
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {self.bg_color};
                border-radius: 10px;
                border: 1px solid {self.border_color};
            }}
        """)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(self.shadow_color)
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)
        
        self.layout.addWidget(self.container)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        # Title Bar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.title_label.setText("Управление профилями")
        self.title_bar.set_theme(self.theme)
        self.title_bar.profile_btn.hide()
        self.title_bar.active_profile_label.hide()
        self.title_bar.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        self.container_layout.addWidget(self.title_bar)
        
        # Content
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        self.container_layout.addWidget(self.content_widget)
        
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # List
        self.list_widget = QListWidget()
        self.list_widget.setWordWrap(True)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: 1px solid {self.list_border};
                border-radius: 8px;
                color: {self.text_color};
                font-size: 15px;
                outline: none;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {self.list_item_border};
                margin-bottom: 2px;
            }}
            QListWidget::item:selected {{
                background-color: {self.selected_bg};
                color: {self.selected_text};
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {self.hover_color};
                color: {self.text_color}
            }}
            QListWidget::item:hover:selected {{
                color: {self.selected_text};
                background-color: {self.selected_bg};
            }}
        """)
        self.list_widget.itemDoubleClicked.connect(self.select_profile)
        self.content_layout.addWidget(self.list_widget, 1) # Stretch factor 1 to expand

        # Buttons Grid
        btn_grid = QVBoxLayout()
        btn_grid.setSpacing(10)
        
        # Top Row: New & Select
        row1 = QHBoxLayout()
        
        self.add_btn = self.create_button("+ Новый профиль", self.success)
        self.add_btn.clicked.connect(self.add_profile)
        
        self.select_btn = self.create_button("✓ Выбрать", self.info)
        self.select_btn.clicked.connect(self.select_profile)
        
        row1.addWidget(self.add_btn)
        row1.addWidget(self.select_btn)
        
        # Bottom Row: Edit & Delete
        row2 = QHBoxLayout()
        
        self.edit_btn = self.create_button("✎ Изменить", self.warning)
        self.edit_btn.clicked.connect(self.edit_profile)
        
        self.delete_btn = self.create_button("✕ Удалить", self.danger)
        self.delete_btn.clicked.connect(self.delete_profile)
        
        row2.addWidget(self.edit_btn)
        row2.addWidget(self.delete_btn)
        
        btn_grid.addLayout(row1)
        btn_grid.addLayout(row2)
        
        self.content_layout.addLayout(btn_grid)

    def create_button(self, text, color):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid {color};
            }}
            QPushButton:hover {{
                background-color: {color}1A;
                color: white;
            }}
        """)
        return btn

    def refresh_list(self):
        self.list_widget.clear()
        profiles = self.data_manager.get_all_profiles()
        active_profile = self.data_manager.get_active_profile()
        
        for p in profiles:
            name = p["name"]
            if p["id"] == active_profile["id"]:
                name = f"⭐ {name} (Активный)"
            else:
                name = f"   {name}"
            
            self.list_widget.addItem(name)
            item = self.list_widget.item(self.list_widget.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, p["id"])

    def add_profile(self):
        dialog = AddProfileDialog(self)
        if dialog.exec():
            name, capital = dialog.get_data()
            if name:
                self.data_manager.create_profile(name, capital)
                self.refresh_list()

    def edit_profile(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            return
            
        profile_id = self.list_widget.item(current_row).data(Qt.ItemDataRole.UserRole)
        profile = next((p for p in self.data_manager.get_all_profiles() if p["id"] == profile_id), None)
        
        if not profile:
            return

        # Use our new stylish dialog for editing too
        dialog = AddProfileDialog(self, edit_mode=True, current_name=profile["name"], current_capital=profile["starting_amount"])
        if dialog.exec():
            new_name, new_capital = dialog.get_data()
            if new_name:
                self.data_manager.update_profile(profile_id, new_name, new_capital)
                self.refresh_list()

    def delete_profile(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            return
            
        profile_id = self.list_widget.item(current_row).data(Qt.ItemDataRole.UserRole)
        
        if len(self.data_manager.get_all_profiles()) <= 1:
            AlertDialog(
                self, 
                "Ошибка", 
                "Нельзя удалить единственный профиль.", 
                "warning"
            ).exec()
            return

        dialog = ConfirmationDialog(
            self, 
            "Удаление профиля", 
            "Вы уверены? Все данные профиля будут удалены безвозвратно."
        )
        
        if dialog.exec():
            self.data_manager.delete_profile(profile_id)
            self.refresh_list()

    def select_profile(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            return
            
        profile_id = self.list_widget.item(current_row).data(Qt.ItemDataRole.UserRole)
        self.data_manager.set_active_profile(profile_id)
        self.accept()
