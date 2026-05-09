from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QFileDialog, QScrollArea, QGridLayout, 
    QFrame, QMessageBox, QTabWidget, QStackedWidget, QMenu, QListWidget, QListWidgetItem,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize, QByteArray, QBuffer, QIODevice, pyqtSignal, QTimer, QFileInfo
from PyQt6.QtGui import QPixmap, QImage, QIcon, QKeySequence, QShortcut, QImageReader
from PyQt6.QtWidgets import QApplication, QLabel
import logging
import os

class ImageDropLabel(QLabel):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    paste_requested = pyqtSignal()
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            # Check if at least one URL is a local image file
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile().lower()
                    if file_path.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    # We found a file, emit paste_requested-like signal or handle it directly
                    # Since we can't emit a signal with arguments to paste_image easily without changing it,
                    # we'll add a signal or call a method on parent if possible, 
                    # but simpler is to emit a custom signal carrying the path.
                    
                    # For now, let's assume the parent connects to a new signal or we modify this class
                    # to handle the drop logic itself?
                    # Better: Emit a signal that the parent listens to, OR generic paste_requested
                    # But paste_requested takes no args.
                    
                    # Let's add a new signal
                    self.image_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    paste_requested = pyqtSignal()
    image_dropped = pyqtSignal(str)
        
    def mousePressEvent(self, event):
        self.setFocus()
        self.clicked.emit()
        super().mousePressEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
        
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste) or (event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V):
            self.paste_requested.emit()
        else:
            super().keyPressEvent(event)

from gui.custom_dialogs import ConfirmationDialog, InputDialog, AlertDialog
from gui.styles import StyleManager

class ClothesTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        self.current_theme = "dark" # Default
        
        self.layout = QHBoxLayout(self)
        
        # Left Panel (Input)
        self.setup_left_panel()
        
        # Right Panel (Inventory/Sold)
        self.setup_right_panel()
        
        self.refresh_data()

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        t = StyleManager.get_theme(theme_name)
        
        self.left_panel.setStyleSheet(f"background-color: {t['bg_secondary']}; border-radius: 10px; border: 1px solid {t['border']};")
        
        input_style = f"""
            border: 1px solid {t['border']};
            border-radius: 8px;
            background-color: {t['input_bg']};
            color: {t['text_main']};
            padding-left: 10px;
            font-size: 15px;
            selection-background-color: {t['accent']};
        """
        
        self.name_input.setStyleSheet(input_style)
        self.price_input.setStyleSheet(input_style)
        self.note_input.setStyleSheet(input_style + "padding-top: 10px;")
        
        # Image label
        self.image_label.setStyleSheet(f"border: 2px dashed {t['border']}; border-radius: 10px; color: {t['text_secondary']}; background-color: {t['input_bg']};")

        # Stats Labels
        self.stat_income.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {t['text_secondary']};")
        self.stat_sold.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {t['text_secondary']};")
        
        # Switcher Buttons
        btn_style = f"""
            QPushButton {{
                background-color: transparent; 
                border: 1px solid {t['border']}; 
                padding: 8px 15px; 
                border-radius: 5px;
                color: {t['text_secondary']};
                font-weight: bold;
            }}
            QPushButton:checked {{
                color: {t['accent']};
                border: 1px solid {t['accent']};
            }}
            QPushButton:hover {{
                color: {t['text_main']};
                border-color: {t['text_main']};
            }}
        """
        self.view_inventory_btn.setStyleSheet(btn_style)
        self.view_sold_btn.setStyleSheet(btn_style)
        self.export_excel_btn.setStyleSheet(btn_style)
        
        # Save Button
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['success']};
                border: 1px solid {t['success']};
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t['success']}1A;
            }}
            QPushButton:pressed {{
                background-color: {t['success']}33;
            }}
        """)
        
        self.refresh_data()

    def setup_left_panel(self):
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(400)
        self.left_panel.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333;")
        
        layout = QVBoxLayout(self.left_panel)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Image Preview
        self.image_label = ImageDropLabel("Ctrl+V для вставки\nДвойной клик для выбора файла")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 2px dashed #555; border-radius: 10px; color: #777; background-color: #252525;")
        self.image_label.setFixedSize(360, 300)
        self.image_label.setScaledContents(False) # Keep aspect ratio
        
        # Connect signals
        self.image_label.clicked.connect(lambda: self.image_label.setFocus())
        self.image_label.double_clicked.connect(self.select_image)
        self.image_label.paste_requested.connect(self.paste_image)
        self.image_label.image_dropped.connect(self.handle_dropped_image)
        
        self.current_image_path = None
        
        # Input Style
        input_style = """
            border: 1px solid #333;
            border-radius: 8px;
            background-color: #252525;
            color: white;
            padding-left: 10px;
            font-size: 15px;
            selection-background-color: #3498db;
        """
        
        # Form Fields
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название товара")
        self.name_input.setStyleSheet(input_style)
        self.name_input.setFixedHeight(40)
        
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Цена покупки ($)")
        self.price_input.setStyleSheet(input_style)
        self.price_input.setFixedHeight(40)
        
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Примечание...")
        self.note_input.setStyleSheet(input_style + "padding-top: 10px;")
        self.note_input.setMaximumHeight(100)
        
        # Save Button
        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(50)
        # Style will be applied by apply_theme
        self.save_btn.clicked.connect(self.save_item)
        
        layout.addWidget(self.image_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.price_input)
        layout.addWidget(self.note_input)
        layout.addWidget(self.save_btn)
        layout.addStretch()
        
        self.layout.addWidget(self.left_panel)

        # Shortcut for Paste - MUST be context application or widget with focus
        self.paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        self.paste_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.paste_shortcut.activated.connect(self.paste_image)
        
    def keyPressEvent(self, event):
        # Fallback for paste if shortcut doesn't trigger
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_image()
        super().keyPressEvent(event)

    def setup_right_panel(self):
        self.right_panel = QWidget()
        layout = QVBoxLayout(self.right_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (Stats + Switcher)
        header_layout = QHBoxLayout()
        
        # Stats
        self.stat_income = QLabel("Покупки: $0")
        self.stat_sold = QLabel("Продажи: $0")
        self.stat_profit = QLabel("Доход: $0")
        
        for lbl in [self.stat_income, self.stat_sold, self.stat_profit]:
            lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaa;")
            header_layout.addWidget(lbl)
            
        header_layout.addStretch()
        
        # Switcher Buttons
        self.view_inventory_btn = QPushButton("📦 Склад")
        self.view_sold_btn = QPushButton("⁝ Продано") # Using unicode for dots
        
        for btn in [self.view_inventory_btn, self.view_sold_btn]:
            btn.setCheckable(True)
            # Style applied in apply_theme
            
        self.view_inventory_btn.setChecked(True)
        self.view_inventory_btn.clicked.connect(lambda: self.switch_view(0))
        self.view_sold_btn.clicked.connect(lambda: self.switch_view(1))
        
        self.export_excel_btn = QPushButton("📊 Excel")
        self.export_excel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_excel_btn.setToolTip("Экспорт в Excel")
        self.export_excel_btn.clicked.connect(self.export_data)
        
        header_layout.addWidget(self.view_inventory_btn)
        header_layout.addWidget(self.view_sold_btn)
        header_layout.addWidget(self.export_excel_btn)
        
        layout.addLayout(header_layout)
        
        # Content Stack
        self.stack = QStackedWidget()
        
        # Page 1: Inventory List
        self.inventory_scroll = QScrollArea()
        self.inventory_scroll.setWidgetResizable(True)
        self.inventory_scroll.setStyleSheet("background-color: transparent; border: none;")
        self.inventory_container = QWidget()
        self.inventory_layout = QVBoxLayout(self.inventory_container)
        self.inventory_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.inventory_scroll.setWidget(self.inventory_container)
        self.stack.addWidget(self.inventory_scroll)
        
        # Page 2: Sold Grid (Responsive)
        self.sold_scroll = QScrollArea()
        self.sold_scroll.setWidgetResizable(True)
        self.sold_scroll.setStyleSheet("background-color: transparent; border: none;")
        
        self.sold_container = QWidget()
        self.sold_grid = QGridLayout(self.sold_container)
        self.sold_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.sold_grid.setSpacing(10)
        self.sold_grid.setContentsMargins(10, 10, 10, 10)
        
        self.sold_scroll.setWidget(self.sold_container)
        self.stack.addWidget(self.sold_scroll)
        
        layout.addWidget(self.stack)
        
        self.layout.addWidget(self.right_panel)

    def switch_view(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.view_inventory_btn.setChecked(True)
            self.view_sold_btn.setChecked(False)
        else:
            self.view_inventory_btn.setChecked(False)
            self.view_sold_btn.setChecked(True)
        self.refresh_data()

    def validate_image_file(self, file_path):
        """Validates image file before loading."""
        if not os.path.exists(file_path):
            return False, "Файл не найден."
        
        info = QFileInfo(file_path)
        if not info.exists(): # Double check
            return False, "Файл не существует."
            
        if not info.isFile():
            return False, "Это не файл."
            
        if info.size() == 0:
            return False, "Файл пуст (0 байт)."
            
        if not os.access(file_path, os.R_OK):
            return False, "Нет прав на чтение файла."
            
        reader = QImageReader(file_path)
        if not reader.canRead():
            return False, f"Неподдерживаемый формат или поврежденный файл.\n({reader.errorString()})"
            
        return True, ""

    def select_image(self, event):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if file_path:
            valid, error = self.validate_image_file(file_path)
            if not valid:
                QMessageBox.warning(self, "Ошибка", f"Не удалось открыть файл:\n{error}")
                return

            # Convert to Base64 immediately for portability
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                base64_str = self.data_manager.save_pixmap_image(pixmap) # Now returns Base64
                self.set_preview_image(base64_str)
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить выбранное изображение (QPixmap isNull).")

    def handle_dropped_image(self, file_path):
        """Handle image dropped onto the label."""
        if not file_path:
            return
            
        valid, error = self.validate_image_file(file_path)
        if not valid:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить перетащенное изображение:\n{error}")
            return
            
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            base64_str = self.data_manager.save_pixmap_image(pixmap)
            self.set_preview_image(base64_str)
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить перетащенное изображение.\nВозможно, формат не поддерживается.")

    def paste_image(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        saved_path = None
        error_msg = None
        
        # Check for Pixmap (Direct image copy)
        if mime_data.hasImage():
            pixmap = clipboard.pixmap()
            if not pixmap.isNull():
                saved_path = self.data_manager.save_pixmap_image(pixmap)
            else:
                error_msg = "Не удалось прочитать изображение из буфера обмена."

        # Check for URLs (File copy)
        elif mime_data.hasUrls():
            found_image = False
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    # Check extensions
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        found_image = True
                        if os.path.exists(file_path):
                            pixmap = QPixmap(file_path)
                            if not pixmap.isNull():
                                saved_path = self.data_manager.save_pixmap_image(pixmap)
                            else:
                                error_msg = "Файл поврежден или имеет неверный формат."
                        else:
                            error_msg = "Файл не найден или нет прав доступа."
                        break # Only take the first one
            
            if not found_image and not error_msg:
                 error_msg = "В буфере обмена нет поддерживаемых изображений."
        else:
             # If we are here, it might be text or something else.
             # We should only show error if the user explicitly triggered this action 
             # and expects an image.
             error_msg = "Буфер обмена не содержит изображения."
        
        if saved_path:
            self.set_preview_image(saved_path)
            self.show_paste_success()
        elif error_msg:
             # Show error only if we are sure it was a paste attempt for image
             # Since this is triggered by Ctrl+V, we should be careful not to annoy 
             # if user pasted text into a field (though QShortcut usually swallows it).
             
             # If a text field has focus, we might want to ignore this error 
             # unless the clipboard has NO text.
             
             widget = QApplication.focusWidget()
             if isinstance(widget, (QLineEdit, QTextEdit)) and mime_data.hasText():
                 return # Let the text widget handle it
                 
             QMessageBox.warning(self, "Ошибка вставки", error_msg)
            
    def show_paste_success(self):
        # Visual feedback: Flash green border
        current_style = self.image_label.styleSheet()
        self.image_label.setStyleSheet("border: 3px solid #2ecc71; border-radius: 10px; background-color: rgba(46, 204, 113, 0.1);")
        
        # Restore style after 500ms
        QTimer.singleShot(500, lambda: self.apply_theme(self.current_theme))

    def set_preview_image(self, path):
        self.current_image_path = path
        pixmap = self.data_manager.load_pixmap(path)
        if not pixmap.isNull():
             # Scale pixmap to fit label while keeping aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setText("")
        else:
             self.image_label.setText("Ошибка загрузки фото")

    def save_item(self):
        name = self.name_input.text()
        price = self.price_input.text()
        note = self.note_input.toPlainText()
        
        if not name or not price:
            AlertDialog(self, "Ошибка", "Заполните название и цену", "ОК").exec()
            return
            
        try:
            float(price)
        except ValueError:
            AlertDialog(self, "Ошибка", "Цена должна быть числом", "ОК").exec()
            return
            
        self.data_manager.add_clothes_item(name, price, note, self.current_image_path)
        
        # Reset form
        self.name_input.clear()
        self.price_input.clear()
        self.note_input.clear()
        self.image_label.clear()
        self.image_label.setText("Вставьте фото (Ctrl+V)\nили кликните")
        self.current_image_path = None
        
        self.refresh_data()

    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            
            success = self.data_manager.export_to_excel("clothes", file_path)
            if success:
                QMessageBox.information(self, "Успех", f"Данные успешно экспортированы в\n{file_path}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать данные")

    def refresh_data(self):
        try:
            # Update Stats
            stats = self.data_manager.get_category_stats("clothes")
            if stats:
                # Note: Stats returns total income/expenses. 
                # User wants "Buy Amount" (Expenses), "Sell Amount" (Income)
                # My get_category_stats for clothes returns:
                # income = sum(sell_price)
                # expenses = sum(buy_price of ALL items)
                self.stat_income.setText(f"Покупки: ${stats['expenses']:,.0f}")
                self.stat_sold.setText(f"Продажи: ${stats['income']:,.0f}")
                
                profit = stats['pure_profit']
                color = "#2ecc71" if profit >= 0 else "#e74c3c"
                self.stat_profit.setText(f"Доход: ${profit:,.0f}")
                self.stat_profit.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")

            # Update Inventory List
            self.clear_layout(self.inventory_layout)
            inventory = self.data_manager.get_clothes_inventory()
            
            for item in inventory:
                try:
                    card = self.create_inventory_card(item)
                    self.inventory_layout.addWidget(card)
                except Exception as e:
                    logging.error(f"Error adding inventory card: {e}")
                
            # Update Sold Grid
            self.clear_layout(self.sold_grid)
            sold_items = self.data_manager.get_clothes_sold()
            
            row, col = 0, 0
            for item in sold_items:
                try:
                    card = self.create_sold_card(item)
                    self.sold_grid.addWidget(card, row, col)
                    col += 1
                    if col > 2: # 3 columns
                        col = 0
                        row += 1
                except Exception as e:
                     logging.error(f"Error adding sold card: {e}")

        except Exception as e:
            logging.error(f"Critical error in refresh_data: {e}", exc_info=True)

    def create_inventory_card(self, item):
        try:
            t = StyleManager.get_theme(self.current_theme)
            
            card_bg = t["bg_secondary"]
            card_border = f"1px solid {t['border']}"
            img_bg = t["bg_tertiary"]
            text_color = t["text_main"]
            note_color = t["text_secondary"]

            frame = QFrame()
            frame.setStyleSheet(f"background-color: {card_bg}; border-radius: 8px; margin-bottom: 5px; border: {card_border};")
            frame.setFixedHeight(120)
            
            layout = QHBoxLayout(frame)
            
            # Image
            img_lbl = QLabel()
            img_lbl.setFixedSize(100, 100)
            img_lbl.setStyleSheet(f"background-color: {img_bg}; border-radius: 5px;")
            img_lbl.setScaledContents(True)
            if item.get("photo_path"):
                pixmap = self.data_manager.load_pixmap(item["photo_path"], max_size=(200, 200)) # Optimize for thumbnail
                if not pixmap.isNull():
                    img_lbl.setPixmap(pixmap)
                else:
                    img_lbl.setText("Нет фото")
                    img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    img_lbl.setStyleSheet(f"background-color: {img_bg}; border-radius: 5px; color: {note_color};")
            else:
                img_lbl.setText("Нет фото")
                img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_lbl.setStyleSheet(f"background-color: {img_bg}; border-radius: 5px; color: {note_color};")
                
            layout.addWidget(img_lbl)
            
            # Info
            info_layout = QVBoxLayout()
            name_lbl = QLabel(item.get("name", "Без названия"))
            name_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {text_color};")
            
            price = item.get("buy_price", 0)
            try:
                price_val = float(price)
            except (ValueError, TypeError):
                price_val = 0.0
                
            price_lbl = QLabel(f"Покупка: ${price_val:,.0f}")
            price_lbl.setStyleSheet("color: #e74c3c;")
            
            note_lbl = QLabel(item.get("note", ""))
            note_lbl.setStyleSheet(f"color: {note_color}; font-size: 12px;")
            
            info_layout.addWidget(name_lbl)
            info_layout.addWidget(price_lbl)
            info_layout.addWidget(note_lbl)
            info_layout.addStretch()
            
            layout.addLayout(info_layout)
            
            # Actions
            action_layout = QVBoxLayout()
            
            sell_btn = QPushButton("💰 Продать")
            sell_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    padding: 5px; 
                    border-radius: 4px;
                    color: {t['success']};
                    font-weight: bold;
                    border: 1px solid {t['success']};
                }}
                QPushButton:hover {{
                    background-color: {t['success']}1A;
                }}
            """)
            sell_btn.clicked.connect(lambda checked, i=item: self.open_sell_dialog(i))
            
            del_btn = QPushButton("✕")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    padding: 5px; 
                    border-radius: 4px;
                    color: {t['danger']};
                    font-weight: bold;
                    font-size: 16px;
                    border: 1px solid {t['danger']};
                }}
                QPushButton:hover {{
                    background-color: {t['danger']}1A;
                }}
            """)
            del_btn.clicked.connect(lambda checked, i_id=item.get("id"): self.delete_item(i_id, False))
            
            action_layout.addWidget(sell_btn)
            action_layout.addWidget(del_btn)
            action_layout.addStretch()
            
            layout.addLayout(action_layout)
            
            return frame
        except Exception as e:
            logging.error(f"Error in create_inventory_card: {e}")
            # Placeholder for inventory card
            err_frame = QFrame()
            err_frame.setFixedHeight(120)
            err_frame.setStyleSheet(f"background-color: #330000; border-radius: 8px;")
            err_layout = QVBoxLayout(err_frame)
            err_layout.addWidget(QLabel(f"Ошибка отображения: {item.get('name', '???')}"))
            return err_frame

    def create_sold_card(self, item):
        try:
            t = StyleManager.get_theme(self.current_theme)
            
            bg_color = t["bg_secondary"]
            border = f"1px solid {t['border']}"
            img_bg = t["bg_tertiary"]

            frame = QFrame()
            frame.setStyleSheet(f"background-color: {bg_color}; border-radius: 8px; border: {border};")
            frame.setFixedSize(180, 180)
            
            # Overlay Layout using Grid
            layout = QGridLayout(frame)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Image (Background-like)
            img_lbl = QLabel()
            img_lbl.setStyleSheet(f"background-color: {img_bg}; border-radius: 8px; border: none;")
            img_lbl.setScaledContents(False) # Maintain aspect ratio
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if item.get("photo_path"):
                pixmap = self.data_manager.load_pixmap(item["photo_path"])
                if not pixmap.isNull():
                     # Scale pixmap to fit label while keeping aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        QSize(180, 180),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    img_lbl.setPixmap(scaled_pixmap)
                else:
                    img_lbl.setText("Нет фото")
                    img_lbl.setStyleSheet(f"color: rgba(255,255,255,100); background-color: {img_bg}; border-radius: 8px;")
            else:
                img_lbl.setText("Нет фото")
                img_lbl.setStyleSheet(f"color: rgba(255,255,255,100); background-color: {img_bg}; border-radius: 8px;")
            
            # Add image to grid covering everything
            layout.addWidget(img_lbl, 0, 0, 3, 2)
            
            # Sold Overlay Text
            sold_lbl = QLabel("ПРОДАНО")
            sold_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sold_lbl.setStyleSheet("color: rgba(255, 255, 255, 150); font-weight: bold; font-size: 20px; background: transparent; border: none;")
            layout.addWidget(sold_lbl, 1, 0, 1, 2)
            
            # Name Label (Bottom Center)
            name_lbl = QLabel(item.get("name", "Без названия"))
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lbl.setStyleSheet("color: white; font-weight: bold; background-color: rgba(0,0,0,150); padding: 4px; border-radius: 4px; border: none;")
            layout.addWidget(name_lbl, 1, 0, 1, 2, Qt.AlignmentFlag.AlignBottom)

            # Buy Price (Bottom Left)
            buy_container = QFrame()
            buy_container.setStyleSheet(f"background-color: {t['danger']}; border-radius: 4px; border: none;")
            buy_layout = QHBoxLayout(buy_container)
            buy_layout.setContentsMargins(5, 2, 5, 2)
            
            try:
                buy_price_val = float(item.get('buy_price', 0))
            except (ValueError, TypeError):
                buy_price_val = 0.0
                
            buy_lbl = QLabel(f"${buy_price_val:,.0f}")
            buy_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 12px; border: none; background: transparent;")
            buy_layout.addWidget(buy_lbl)
            
            layout.addWidget(buy_container, 2, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
            
            # Sell Price (Bottom Right)
            sell_container = QFrame()
            sell_container.setStyleSheet(f"background-color: {t['success']}; border-radius: 4px; border: none;")
            sell_layout = QHBoxLayout(sell_container)
            sell_layout.setContentsMargins(5, 2, 5, 2)
            
            try:
                sell_price_val = float(item.get('sell_price', 0))
            except (ValueError, TypeError):
                sell_price_val = 0.0
                
            sell_lbl = QLabel(f"${sell_price_val:,.0f}")
            sell_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 12px; border: none; background: transparent;")
            sell_layout.addWidget(sell_lbl)
            
            layout.addWidget(sell_container, 2, 1, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

            # Delete Button (Top Right, hidden by default or small)
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(24, 24)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    color: white; 
                    border-radius: 12px;
                    border: none;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {t['danger']};
                }}
            """)
            del_btn.clicked.connect(lambda checked, i_id=item.get("id"): self.delete_item(i_id, True))
            layout.addWidget(del_btn, 0, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            
            return frame
        except Exception as e:
            logging.error(f"Error in create_sold_card: {e}")
            # Return a placeholder frame to prevent crash
            err_frame = QFrame()
            err_frame.setFixedSize(180, 180)
            err_lbl = QLabel("Ошибка")
            err_layout = QVBoxLayout(err_frame)
            err_layout.addWidget(err_lbl)
            return err_frame

    def open_sell_dialog(self, item):
        # Styled Input Dialog
        # from gui.custom_dialogs import AlertDialog # Already imported at top
        
        try:
            item_id = item.get("id")
            if not item_id:
                logging.error(f"open_sell_dialog: Item has no ID: {item}")
                AlertDialog(self, "Ошибка", "Некорректные данные предмета (нет ID).").exec()
                return

            logging.info(f"Opening sell dialog for item: {item.get('name')} (ID: {item_id})")
            
            dialog = InputDialog(self, "Продажа", "Введите сумму продажи:", "")
            if dialog.exec():
                val = dialog.get_value()
                if val is not None:
                    if val < 0:
                        logging.warning(f"User entered negative sell price: {val}")
                        AlertDialog(self, "Ошибка", "Сумма не может быть отрицательной.").exec()
                        return

                    logging.info(f"User confirmed sell with price: {val}")
                    
                    try:
                        success = self.data_manager.sell_clothes_item(item_id, val)
                        if success:
                            self.refresh_data()
                            # Optional: Show success message? Usually refresh is enough.
                            logging.info("Item sold successfully, UI refreshed.")
                        else:
                            logging.error("sell_clothes_item returned False")
                            AlertDialog(self, "Ошибка", "Не удалось продать предмет.\nВозможно, он уже удален или возникла ошибка данных.").exec()
                    except Exception as e:
                        logging.error(f"Error during sell operation: {e}", exc_info=True)
                        AlertDialog(self, "Ошибка", f"Произошла ошибка при выполнении продажи:\n{e}").exec()
                else:
                    logging.warning("User entered invalid sell price (not a number)")
                    AlertDialog(self, "Ошибка", "Некорректная сумма").exec()
            else:
                logging.info("Sell dialog cancelled by user")
        except Exception as e:
            logging.error(f"Crash in open_sell_dialog: {e}", exc_info=True)
            try:
                AlertDialog(self, "Критическая ошибка", f"Произошла ошибка при открытии диалога:\n{e}").exec()
            except:
                print(f"Failed to show alert dialog: {e}")


    def delete_item(self, item_id, is_sold):
        dialog = ConfirmationDialog(self, "Удаление", "Вы уверены, что хотите удалить этот предмет?")
        if dialog.exec():
            self.data_manager.delete_clothes_item(item_id, is_sold)
            self.refresh_data()

    def clear_layout(self, layout):
        if isinstance(layout, QGridLayout):
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        else:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

