from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
    QFrame, QLineEdit, QApplication, QGraphicsDropShadowEffect, 
    QComboBox, QDateEdit, QFileDialog, QButtonGroup, QScrollArea, QSizeGrip,
    QWidget, QCompleter, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, QTime, QTimer, QSize, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QIcon, QPixmap, QAction, QKeySequence
import traceback

from gui.styles import StyleManager
from gui.custom_dialogs import StyledDialogBase, ResizeMixin
from gui.title_bar import CustomTitleBar
from datetime import datetime

class TransactionDialog(QDialog, ResizeMixin):
    def __init__(self, parent=None, data_manager=None, category="legacy", transaction=None):
        super().__init__(parent)
        self.setup_resizing()
        self.transaction = transaction
        self.data_manager = data_manager if data_manager else (parent.data_manager if parent else None)
        self.category = category
        self.current_image_path = None
        
        # Determine theme colors
        self.theme = StyledDialogBase._theme
        t = StyleManager.get_theme(self.theme)
        
        self.bg_color = t['bg_secondary']
        self.border_color = t['border']
        self.input_bg = t['input_bg']
        self.input_border = t['border']
        self.text_color = t['text_main']
        self.placeholder_color = t['text_secondary']
        self.shadow_color = QColor(0, 0, 0, 100) if self.theme == "dark" else QColor(0, 0, 0, 30)
        self.accent_color = t['accent']
        self.danger_color = t['danger']
        self.success_color = t['success']
        
        # Frameless setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Restore standard size
        self.resize(500, 650)
        self.setMinimumWidth(450)
        self.setMinimumHeight(550)
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10) # Margin for shadow
        
        # Container Frame (The actual window background)
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {self.bg_color};
                border-radius: 10px;
                border: 1px solid {self.border_color};
            }}
        """)
        
        # Shadow Effect
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
        self.title_bar.title_label.setText(f"{'Редактировать' if transaction else 'Добавить'} операцию")
        self.title_bar.set_theme(self.theme)
        # Hide profile controls in dialog
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
        
        # 2. Content Area (Scrollable)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 15, 20, 15) # Reduced margins
        self.content_layout.setSpacing(12) # Reduced spacing
        
        self.scroll_area.setWidget(self.content_widget)
        self.container_layout.addWidget(self.scroll_area)
        
        self.setup_ui()
        
        if transaction:
            self.load_transaction_data()
        else:
            self.apply_listing_cost()

    def showEvent(self, event):
        self.animate_open()
        super().showEvent(event)

    def animate_open(self):
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def setup_ui(self):
        try:
            # -- Image Preview --
            if self.category == "clothes":
                self.image_label = QLabel("Ctrl+V для вставки\nЛКМ для выбора файла")
                self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.image_label.setStyleSheet(f"border: 2px dashed {self.input_border}; border-radius: 10px; color: {self.placeholder_color}; background-color: {self.input_bg};")
                self.image_label.setFixedHeight(120) # Reduced from 150
                self.image_label.setScaledContents(False) # Disable auto-stretch to keep aspect ratio
                self.image_label.mousePressEvent = self.select_image
                self.content_layout.addWidget(self.image_label)
                
                # Shortcut for Paste
                self.paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
                self.paste_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                self.paste_shortcut.activated.connect(self.paste_image)
            else:
                self.image_label = None
                self.paste_shortcut = None
            
            # -- Transaction Type (Toggle Buttons) --
            type_layout = QHBoxLayout()
            type_layout.setSpacing(10)
            
            self.btn_income = QPushButton("Доход (+)")
            self.btn_income.setCheckable(True)
            self.btn_income.setChecked(True)
            self.btn_income.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_income.setFixedHeight(40) # Reduced from 45
            
            self.btn_expense = QPushButton("Расход (-)")
            self.btn_expense.setCheckable(True)
            self.btn_expense.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_expense.setFixedHeight(40) # Reduced from 45
            
            # Exclusive check
            self.type_group = QButtonGroup(self)
            self.type_group.addButton(self.btn_income)
            self.type_group.addButton(self.btn_expense)
            
            # Connect signals to update styles
            self.type_group.buttonClicked.connect(self.update_type_styles)
            
            type_layout.addWidget(self.btn_income)
            type_layout.addWidget(self.btn_expense)
            self.content_layout.addLayout(type_layout)
            
            # -- Date Field --
            date_container = self.create_input_container("Дата")
            self.date_edit = QDateEdit()
            self.date_edit.setCalendarPopup(True)
            self.date_edit.setDate(QDate.currentDate())
            self.date_edit.setDisplayFormat("dd.MM.yyyy")
            self.date_edit.setFixedHeight(40)
            date_container.layout().addWidget(self.date_edit)
            self.content_layout.addWidget(date_container)

            # -- Item Name Field --
            item_container = self.create_input_container("Название товара/авто")
            self.item_name_input = QComboBox()
            self.item_name_input.setEditable(True)
            self.item_name_input.setFixedHeight(40)
            self.item_name_input.setPlaceholderText("Например: Sultan")
            
            if self.data_manager:
                items = self.data_manager.get_unique_item_names(self.category)
                self.item_name_input.addItems(items)
                completer = QCompleter(items)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                self.item_name_input.setCompleter(completer)
                
            item_container.layout().addWidget(self.item_name_input)
            self.content_layout.addWidget(item_container)
            
            # -- Amount Field --
            amount_container = self.create_input_container("Сумма ($)")
            amount_layout = QHBoxLayout()
            amount_layout.setContentsMargins(0, 0, 0, 0)
            amount_layout.setSpacing(10)

            self.amount_input = QLineEdit()
            self.amount_input.setPlaceholderText("0")
            self.amount_input.setFixedHeight(40)
            
            amount_layout.addWidget(self.amount_input)
            
            amount_container.layout().addLayout(amount_layout)
            self.content_layout.addWidget(amount_container)

            # -- Ad Cost Field (Conditional for Car Rental Income) --
            self.ad_cost_container = self.create_input_container("Стоимость объявления")
            self.ad_cost_input = QLineEdit()
            self.ad_cost_input.setPlaceholderText("0")
            self.ad_cost_input.setFixedHeight(40)
            self.ad_cost_container.layout().addWidget(self.ad_cost_input)
            self.content_layout.addWidget(self.ad_cost_container)
            self.ad_cost_container.hide() # Hide by default
            
            # -- Comment Field --
            comment_container = self.create_input_container("Примечание")
            self.comment_input = QLineEdit()
            self.comment_input.setPlaceholderText("Например: Продажа с тюнингом")
            self.comment_input.setFixedHeight(45) # Increased height
            self.comment_input.setStyleSheet("padding: 5px; font-size: 14px;")
            comment_container.layout().addWidget(self.comment_input)
            self.content_layout.addWidget(comment_container)
            
            self.content_layout.addStretch()
            
            # -- Action Buttons --
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(15)
            
            self.save_btn = QPushButton("Сохранить")
            self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.save_btn.setFixedHeight(45) # Reduced from 50
            self.save_btn.clicked.connect(self.accept)
            
            self.cancel_btn = QPushButton("Отмена")
            self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.cancel_btn.setFixedHeight(45) # Reduced from 50
            self.cancel_btn.clicked.connect(self.reject)
            
            btn_layout.addWidget(self.save_btn)
            btn_layout.addWidget(self.cancel_btn)
            self.content_layout.addLayout(btn_layout)
            
            # Initial Style Update
            self.update_type_styles()
            self.apply_styles()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка интерфейса", f"Ошибка при создании интерфейса:\n{str(e)}\n{traceback.format_exc()}")

    def create_input_container(self, label_text):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4) # Reduced from 8
        
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {self.placeholder_color}; font-size: 14px; font-weight: 500;")
        layout.addWidget(label)
        
        return widget

    def apply_listing_cost(self):
        if self.data_manager:
            enabled = self.data_manager.get_setting("listing_cost_enabled", True)
            if not enabled:
                return
            
            cost = self.data_manager.get_setting("listing_cost", 0.0)
            if cost > 0:
                # Check if UI was initialized successfully
                if not hasattr(self, 'ad_cost_input'):
                    return

                # Do NOT switch to Expense or set Main Amount.
                # Instead, set the Ad Cost field and ensure Income mode is active.
                self.btn_income.setChecked(True)
                self.ad_cost_input.setText(str(cost))
                
                # Optional: Clear main amount or set to 0 if preferred, but usually user enters it.
                # self.amount_input.setText("0") # Leaving it empty/default is better for UX.
                
                if not self.comment_input.text():
                    self.comment_input.setText("") # Don't auto-fill "Ad Cost" note on main income
                
                self.update_type_styles()

    def apply_styles(self):
        # Common Input Styles
        input_style = f"""
            border: 1px solid {self.input_border};
            border-radius: 8px;
            background-color: {self.input_bg};
            color: {self.text_color};
            padding-left: 10px;
            font-size: 15px;
            selection-background-color: #3498db;
        """
        
        self.date_edit.setStyleSheet(input_style + f"""
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 0px;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QDateEdit::down-arrow {{
                image: none;
                border-left: 2px solid {self.placeholder_color};
                border-bottom: 2px solid {self.placeholder_color};
                width: 8px;
                height: 8px;
                transform: rotate(-45deg);
                margin-right: 10px;
                margin-top: 2px;
            }}
        """)
        
        self.item_name_input.setStyleSheet(input_style + """
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
        """)
        
        self.amount_input.setStyleSheet(input_style)
        self.ad_cost_input.setStyleSheet(input_style)
        self.comment_input.setStyleSheet(input_style)
        
        # Button Styles
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.success_color};
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid {self.success_color};
            }}
            QPushButton:hover {{
                background-color: {self.success_color}1A;
            }}
            QPushButton:pressed {{
                background-color: {self.success_color}33;
            }}
        """)
        
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.text_color};
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid {self.input_border};
            }}
            QPushButton:hover {{
                background-color: {self.border_color};
            }}
        """)

    def update_type_styles(self, btn=None):
        if not self.btn_income.isChecked() and not self.btn_expense.isChecked():
            return
            
        is_income = self.btn_income.isChecked()
        
        # Reset fields state
        self.amount_input.setReadOnly(False)
        self.ad_cost_input.setReadOnly(False)

        # Toggle Ad Cost visibility if enabled in settings and type is Income
        if self.data_manager and is_income:
             is_auto = self.data_manager.get_setting("listing_cost_enabled", True)
             
             if is_auto:
                 self.ad_cost_container.show()
             else:
                 self.ad_cost_container.hide()
        else:
             self.ad_cost_container.hide()

        # Update button styles
        if is_income:
            self.btn_income.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.success_color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 16px;
                }}
            """)
            self.btn_expense.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.text_color};
                    border: 2px solid {self.input_border};
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    border-color: {self.danger_color};
                    color: {self.danger_color};
                }}
            """)
            self.save_btn.setText("Добавить доход")
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.success_color};
                    color: white;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {self.success_color}D9;
                }}
            """)
        else:
            self.btn_expense.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.danger_color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 16px;
                }}
            """)
            self.btn_income.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.text_color};
                    border: 2px solid {self.input_border};
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    border-color: {self.success_color};
                    color: {self.success_color};
                }}
            """)
            self.save_btn.setText("Добавить расход")
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.danger_color};
                    color: white;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {self.danger_color}D9;
                }}
            """)

    def load_transaction_data(self):
        amount = self.transaction["amount"]
        if amount < 0:
            self.btn_expense.setChecked(True)
            self.amount_input.setText(str(abs(amount)))
        else:
            self.btn_income.setChecked(True)
            self.amount_input.setText(str(amount))
            
        self.comment_input.setText(self.transaction.get("comment", ""))
        self.item_name_input.setCurrentText(self.transaction.get("item_name", ""))
        
        if self.transaction.get("image_path"):
            self.set_preview_image(self.transaction["image_path"])
        
        try:
            date_obj = datetime.strptime(self.transaction["date"], "%d.%m.%Y")
        except ValueError:
            try:
                date_obj = datetime.strptime(self.transaction["date"], "%Y-%m-%d")
            except ValueError:
                date_obj = datetime.now()

        self.date_edit.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
        
        self.update_type_styles()

    def select_image(self, event):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            # Save it immediately using DataManager if possible, or just preview
            if self.data_manager:
                saved_path = self.data_manager.save_image(file_path)
                self.set_preview_image(saved_path)

    def paste_image(self):
        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()
        if not pixmap.isNull() and self.data_manager:
            saved_path = self.data_manager.save_pixmap_image(pixmap)
            self.set_preview_image(saved_path)

    def keyPressEvent(self, event):
        if self.paste_shortcut and event.matches(QKeySequence.StandardKey.Paste):
            self.paste_image()
        super().keyPressEvent(event)

    def set_preview_image(self, path):
        if not path: return
        self.current_image_path = path
        
        if not self.image_label: return
        
        resolved_path = self.data_manager.resolve_image_path(path) if self.data_manager else path
        pixmap = QPixmap(resolved_path)
        if not pixmap.isNull():
            # Scale pixmap to fit label while keeping aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setText("")

    def get_data(self):
        # Validation
        amount_text = self.amount_input.text().strip().replace(" ", "").replace(",", ".")
        try:
            amount = float(amount_text)
            if amount < 0: raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректную положительную сумму.")
            return None

        if self.btn_expense.isChecked():
            amount = -amount

        # Note validation
        comment = self.comment_input.text().strip()
        if len(comment) > 500:
             QMessageBox.warning(self, "Ошибка", "Примечание не может превышать 500 символов.")
             return None

        # Ad Cost Validation (if visible)
        ad_cost = 0.0
        if self.ad_cost_container.isVisible():
            ad_cost_text = self.ad_cost_input.text().strip().replace(" ", "").replace(",", ".")
            try:
                ad_cost = float(ad_cost_text)
                if ad_cost < 0: raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректную стоимость объявления.")
                return None

        return {
            "amount": amount,
            "comment": comment,
            "date": self.date_edit.date().toString("dd.MM.yyyy"),
            "item_name": self.item_name_input.currentText().strip(),
            "image_path": self.current_image_path,
            "ad_cost": ad_cost # Return ad cost for processing
        }

    def accept(self):
        data = self.get_data()
        if not data: return # Validation failed

        if self.data_manager:
            if self.transaction:
                # Update existing
                self.data_manager.update_transaction(
                    self.category,
                    self.transaction["id"],
                    data["amount"],
                    data["comment"],
                    data["date"],
                    data["item_name"],
                    data["image_path"],
                    ad_cost=data.get("ad_cost", 0.0)
                )
            else:
                # Add new
                self.data_manager.add_transaction(
                    self.category,
                    data["amount"],
                    data["comment"],
                    data["date"],
                    data["item_name"],
                    data["image_path"],
                    ad_cost=data.get("ad_cost", 0.0)
                )
        
        QDialog.accept(self)

    # -- Dragging Logic for Frameless Window (Optional, if clicking outside title bar) --
    # The CustomTitleBar handles dragging, but usually users expect to drag from empty space too.
    # We'll leave it to TitleBar for now to keep it standard.
