from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QFileDialog, QScrollArea, QGridLayout, 
    QFrame, QMessageBox, QTabWidget, QStackedWidget, QButtonGroup, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QSize, QByteArray, QBuffer, QIODevice, pyqtSignal, QTimer, QFileInfo
from PyQt6.QtGui import QPixmap, QImage, QIcon, QKeySequence, QShortcut, QImageReader, QPainter, QPen, QColor
from PyQt6.QtWidgets import QApplication, QLabel
import logging
import os
import traceback

from gui.custom_dialogs import ConfirmationDialog, InputDialog, AlertDialog
from gui.styles import StyleManager

class DeleteButton(QPushButton):
    def __init__(self, size=30, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_hovered = False
        
    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        bg_color = QColor(231, 76, 60, 40 if not self.is_hovered else 80)
        border_color = QColor(231, 76, 60, 100 if not self.is_hovered else 255)
        
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)
        
        # Draw X
        pen_color = QColor(255, 77, 77) if not self.is_hovered else QColor(255, 255, 255)
        painter.setPen(QPen(pen_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        
        margin = self.width() * 0.3
        painter.drawLine(int(margin), int(margin), int(self.width() - margin), int(self.height() - margin))
        painter.drawLine(int(self.width() - margin), int(margin), int(margin), int(self.height() - margin))

class DeleteButtonOverlay(QPushButton):
    def __init__(self, size=28, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_hovered = False
        
    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circular background
        if not self.is_hovered:
            bg_color = QColor(30, 30, 30, 220)
            border_color = QColor(255, 255, 255, 80)
        else:
            bg_color = QColor(231, 76, 60, 255)
            border_color = QColor(231, 76, 60, 255)
            
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        
        # Draw X
        pen_color = QColor(255, 77, 77) if not self.is_hovered else QColor(255, 255, 255)
        painter.setPen(QPen(pen_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        
        margin = self.width() * 0.35
        painter.drawLine(int(margin), int(margin), int(self.width() - margin), int(self.height() - margin))
        painter.drawLine(int(self.width() - margin), int(margin), int(margin), int(self.height() - margin))

class ImageDropLabel(QLabel):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    paste_requested = pyqtSignal()
    image_dropped = pyqtSignal(str)
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
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
                    self.image_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()
        
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

class TradeItemWidget(QWidget):
    def __init__(self, data_manager, main_window, category_key):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        self.category_key = category_key
        self.current_theme = "dark"
        
        self.layout = QHBoxLayout(self)
        
        # Left Panel (Input)
        self.setup_left_panel()
        
        # Right Panel (Inventory/Sold)
        self.setup_right_panel()
        
        # Connect to data_changed signal
        self.data_manager.data_changed.connect(self.refresh_data)
        
        self.is_initialized = False
        # self.refresh_data() # Deferred

    def showEvent(self, event):
        if not self.is_initialized:
            self.refresh_data()
            self.is_initialized = True
        super().showEvent(event)

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
        self.appearance_price_input.setStyleSheet(input_style)
        self.note_input.setStyleSheet(input_style + "padding-top: 10px;")
        
        self.image_label.setStyleSheet(f"border: 2px dashed {t['border']}; border-radius: 10px; color: {t['text_secondary']}; background-color: {t['input_bg']};")

        # Style new stat cards
        card_style = f"""
            background-color: {t['bg_secondary']}99;
            border: 1px solid {t['border']};
            border-radius: 12px;
        """
        self.card_purchases.setStyleSheet(card_style)
        self.card_sales.setStyleSheet(card_style)
        self.card_profit.setStyleSheet(card_style)

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
        
        # Toggle appearance price input visibility
        show_coa = self.data_manager.get_setting("showCostOfAppearance", False)
        self.appearance_price_input.setVisible(show_coa)
        
        self.refresh_data()

    def setup_left_panel(self):
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(400)
        
        layout = QVBoxLayout(self.left_panel)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.image_label = ImageDropLabel("Ctrl+V для вставки\nДвойной клик для выбора файла")
        self.image_label.setFixedSize(360, 300)
        self.image_label.setScaledContents(False)
        
        self.image_label.clicked.connect(lambda: self.image_label.setFocus())
        self.image_label.double_clicked.connect(self.select_image)
        self.image_label.paste_requested.connect(self.paste_image)
        self.image_label.image_dropped.connect(self.handle_dropped_image)
        
        self.current_image_path = None
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название товара")
        self.name_input.setFixedHeight(40)
        
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Цена покупки ($)")
        self.price_input.setFixedHeight(40)
        
        self.appearance_price_input = QLineEdit()
        self.appearance_price_input.setPlaceholderText("Стоимость появления ($)")
        self.appearance_price_input.setFixedHeight(40)
        
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Примечание...")
        self.note_input.setMaximumHeight(100)
        
        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(50)
        self.save_btn.clicked.connect(self.save_item)
        
        layout.addWidget(self.image_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.price_input)
        layout.addWidget(self.appearance_price_input)
        layout.addWidget(self.note_input)
        layout.addWidget(self.save_btn)
        layout.addStretch()
        
        self.layout.addWidget(self.left_panel)

        self.paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        self.paste_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.paste_shortcut.activated.connect(self.paste_image)
        
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_image()
        super().keyPressEvent(event)

    def setup_right_panel(self):
        self.right_panel = QWidget()
        layout = QVBoxLayout(self.right_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # --- Financial Stats Section ---
        self.stats_container = QWidget()
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(10)

        # Helper to create a stat card
        def create_stat_card(title, icon, color):
            card = QFrame()
            card.setObjectName("StatCard")
            card.setStyleSheet(f"""
                #StatCard {{
                    background-color: rgba(44, 62, 80, 0.6);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 12, 15, 12)
            card_layout.setSpacing(4)

            header = QHBoxLayout()
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(f"font-size: 18px; color: {color};")
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet("font-size: 12px; color: #95a5a6; font-weight: bold; text-transform: uppercase;")
            header.addWidget(icon_lbl)
            header.addWidget(title_lbl)
            header.addStretch()
            card_layout.addLayout(header)

            val_lbl = QLabel("$0")
            val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {color}; font-family: 'Segoe UI', sans-serif;")
            card_layout.addWidget(val_lbl)
            
            return card, val_lbl

        # Create Cards
        self.card_purchases, self.val_purchases = create_stat_card("Покупки", "📥", "#e74c3c")
        self.card_sales, self.val_sales = create_stat_card("Продажи", "📤", "#3498db")
        self.card_profit, self.val_profit = create_stat_card("Доход", "💰", "#2ecc71")

        stats_layout.addWidget(self.card_purchases, 1)
        stats_layout.addWidget(self.card_sales, 1)
        stats_layout.addWidget(self.card_profit, 1)
        
        layout.addWidget(self.stats_container)

        # --- View Controls Section ---
        controls_layout = QHBoxLayout()
        
        self.view_inventory_btn = QPushButton("📦 Склад")
        self.view_sold_btn = QPushButton("⁝ Продано")
        self.export_excel_btn = QPushButton("📊 Excel")
        
        for btn in [self.view_inventory_btn, self.view_sold_btn, self.export_excel_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.setMinimumWidth(100)

        self.view_inventory_btn.setCheckable(True)
        self.view_sold_btn.setCheckable(True)
        self.view_inventory_btn.setChecked(True)
        
        self.view_inventory_btn.clicked.connect(lambda: self.switch_view(0))
        self.view_sold_btn.clicked.connect(lambda: self.switch_view(1))
        self.export_excel_btn.clicked.connect(self.export_data)
        
        controls_layout.addWidget(self.view_inventory_btn)
        controls_layout.addWidget(self.view_sold_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.export_excel_btn)
        
        layout.addLayout(controls_layout)
        
        self.stack = QStackedWidget()
        
        # Inventory Page
        self.inventory_scroll = QScrollArea()
        self.inventory_scroll.setWidgetResizable(True)
        self.inventory_scroll.setStyleSheet("background-color: transparent; border: none;")
        self.inventory_container = QWidget()
        self.inventory_layout = QVBoxLayout(self.inventory_container)
        self.inventory_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.inventory_scroll.setWidget(self.inventory_container)
        self.stack.addWidget(self.inventory_scroll)
        
        # Sold Page
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

    # --- Logic ---

    def validate_image_file(self, file_path):
        if not os.path.exists(file_path): return False, "Файл не найден."
        info = QFileInfo(file_path)
        if not info.exists() or not info.isFile() or info.size() == 0: return False, "Некорректный файл."
        reader = QImageReader(file_path)
        if not reader.canRead(): return False, "Неподдерживаемый формат."
        return True, ""

    def select_image(self, event):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if file_path:
            valid, error = self.validate_image_file(file_path)
            if not valid:
                QMessageBox.warning(self, "Ошибка", f"Не удалось открыть файл:\n{error}")
                return
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                base64_str = self.data_manager.save_pixmap_image(pixmap)
                self.set_preview_image(base64_str)

    def handle_dropped_image(self, file_path):
        if not file_path: return
        valid, error = self.validate_image_file(file_path)
        if not valid:
            QMessageBox.warning(self, "Ошибка", f"Ошибка файла:\n{error}")
            return
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            base64_str = self.data_manager.save_pixmap_image(pixmap)
            self.set_preview_image(base64_str)

    def paste_image(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        saved_path = None
        
        if mime_data.hasImage():
            pixmap = clipboard.pixmap()
            if not pixmap.isNull():
                saved_path = self.data_manager.save_pixmap_image(pixmap)
        elif mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                         pixmap = QPixmap(file_path)
                         if not pixmap.isNull():
                             saved_path = self.data_manager.save_pixmap_image(pixmap)
                             break
        
        if saved_path:
            self.set_preview_image(saved_path)
            self.show_paste_success()
        else:
             widget = QApplication.focusWidget()
             if not (isinstance(widget, (QLineEdit, QTextEdit)) and mime_data.hasText()):
                 QMessageBox.warning(self, "Ошибка", "Не удалось вставить изображение.")

    def show_paste_success(self):
        self.image_label.setStyleSheet("border: 3px solid #2ecc71; border-radius: 10px; background-color: rgba(46, 204, 113, 0.1);")
        QTimer.singleShot(500, lambda: self.apply_theme(self.current_theme))

    def set_preview_image(self, path):
        self.current_image_path = path
        if not path:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Ctrl+V для вставки\nДвойной клик для выбора файла")
            return
            
        pixmap = self.data_manager.load_pixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.setText("")
        else:
            self.image_label.setText("Ошибка загрузки")

    def save_item(self):
        name = self.name_input.text().strip()
        price_str = self.price_input.text().strip().replace(",", ".")
        coa_str = self.appearance_price_input.text().strip().replace(",", ".") or "0"
        note = self.note_input.toPlainText().strip()
        
        if not name:
            AlertDialog(self, "Ошибка", "Введите название товара", "ОК").exec()
            self.name_input.setFocus()
            return
            
        if not price_str:
            AlertDialog(self, "Ошибка", "Введите цену покупки", "ОК").exec()
            self.price_input.setFocus()
            return
            
        try:
            price = float(price_str)
            coa_price = float(coa_str)
            
            if price < 0 or coa_price < 0:
                raise ValueError("Цена не может быть отрицательной")
                
        except ValueError as e:
            AlertDialog(self, "Ошибка", f"Некорректная цена: {str(e)}", "ОК").exec()
            return
        
        try:
            # Show loading state
            self.save_btn.setEnabled(False)
            self.save_btn.setText("⌛ Сохранение...")
            QApplication.processEvents()
            
            # Use generic method
            success = self.data_manager.add_trade_item(
                self.category_key, name, price, note, 
                self.current_image_path, coa_price=coa_price
            )
            
            if success:
                # Success feedback
                self.name_input.clear()
                self.price_input.clear()
                self.appearance_price_input.clear()
                self.note_input.clear()
                self.set_preview_image(None)
                self.image_label.setText("Ctrl+V для вставки\nДвойной клик для выбора файла")
                
                # Reset ad cost if enabled
                if self.data_manager.get_setting("listing_cost_enabled", True):
                    ad_cost = self.data_manager.get_setting("listing_cost", 0.0)
                    if ad_cost > 0:
                        self.appearance_price_input.setText(str(int(ad_cost)))
                
                # Visual success indicator
                self.save_btn.setStyleSheet(self.save_btn.styleSheet() + "background-color: #2ecc71; color: white;")
                self.save_btn.setText("✅ Сохранено!")
                
                QTimer.singleShot(1500, lambda: self.apply_theme(self.current_theme))
                
                logging.info(f"Successfully saved trade item: {name}")
                self.refresh_data()
            else:
                raise Exception("DataManager returned False during save")
                
        except Exception as e:
            logging.error(f"Error saving trade item: {e}\n{traceback.format_exc()}")
            AlertDialog(self, "Ошибка сохранения", f"Произошла ошибка при сохранении:\n{str(e)}", "ОК").exec()
        finally:
            self.save_btn.setEnabled(True)
            self.save_btn.setText("💾 Сохранить")

    def refresh_data(self):
        # Update Stats
        stats = self.data_manager.get_category_stats(self.category_key)
        if stats:
            self.val_purchases.setText(f"${int(stats['expenses']):,}")
            self.val_sales.setText(f"${int(stats['income']):,}")
            self.val_profit.setText(f"${int(stats['pure_profit']):,}")
            
        # Update Global Balance
        if hasattr(self.main_window, 'update_balance_display'):
            self.main_window.update_balance_display()
            
        # Update Lists
        self.update_inventory_list()
        self.update_sold_list()

        # Auto-fill and dynamic visibility for ad cost (Task 1)
        is_ad_cost_enabled = self.data_manager.get_setting("listing_cost_enabled", True)
        
        # Ensure it's explicitly shown/hidden
        if is_ad_cost_enabled:
            self.appearance_price_input.show()
            ad_cost = self.data_manager.get_setting("listing_cost", 0.0)
            if ad_cost > 0 and not self.appearance_price_input.text():
                self.appearance_price_input.setText(str(ad_cost))
        else:
            self.appearance_price_input.hide()

    def update_inventory_list(self):
        # Clear layout
        while self.inventory_layout.count():
            child = self.inventory_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        items = self.data_manager.get_trade_inventory(self.category_key)
        show_coa = self.data_manager.get_setting("showCostOfAppearance", False)
        
        # Check if we should show buy_price (Task 4)
        show_buy_price = self.data_manager.get_setting("showBuyPriceInInventory", True)
        
        for item in items:
            row = QFrame()
            row.setStyleSheet("background-color: rgba(255,255,255,0.05); border-radius: 8px;")
            row_layout = QHBoxLayout(row)
            
            # Icon
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(60, 60)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Check both photo_path and image_path for compatibility
            img_path = item.get("photo_path") or item.get("image_path")
            
            if img_path:
                pix = self.data_manager.load_pixmap(img_path, (60, 60))
                if not pix.isNull():
                    icon_lbl.setPixmap(pix)
                else:
                    icon_lbl.setText("🖼️") # Fallback icon
            else:
                icon_lbl.setText("📦") # Default icon
                
            icon_lbl.setStyleSheet("background-color: rgba(0,0,0,0.2); border-radius: 4px; font-size: 24px;")
            row_layout.addWidget(icon_lbl)
            
            # Info
            info_layout = QVBoxLayout()
            name_lbl = QLabel(item.get("name"))
            name_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
            info_layout.addWidget(name_lbl)
            
            if show_buy_price:
                price_text = f"Куплено за: ${int(float(item.get('buy_price', 0))):,}"
                price_lbl = QLabel(price_text)
                info_layout.addWidget(price_lbl)
            
            row_layout.addLayout(info_layout)
            
            # Cost of Appearance Column (Task 2)
            if show_coa:
                coa_layout = QVBoxLayout()
                coa_val = int(float(item.get('cost_of_appearance', 0)))
                coa_lbl_title = QLabel("Стоимость появления")
                coa_lbl_title.setStyleSheet("font-size: 11px; color: #7f8c8d;")
                coa_lbl_val = QLabel(f"${coa_val:,}")
                coa_lbl_val.setStyleSheet("font-weight: bold; font-size: 13px; color: #f1c40f;")
                coa_layout.addWidget(coa_lbl_title)
                coa_layout.addWidget(coa_lbl_val)
                row_layout.insertSpacing(2, 40)
                row_layout.addLayout(coa_layout)
            
            row_layout.addStretch()
            
            # Actions
            sell_btn = QPushButton("💰 Продать")
            sell_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            sell_btn.clicked.connect(lambda checked, i=item: self.sell_item_dialog(i))
            
            del_btn = DeleteButton(30)
            del_btn.clicked.connect(lambda checked, i=item: self.delete_item(i.get('id'), False))
            
            row_layout.addWidget(sell_btn)
            row_layout.addWidget(del_btn)
            
            self.inventory_layout.addWidget(row)

    def update_sold_list(self):
        # Clear grid
        while self.sold_grid.count():
            child = self.sold_grid.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        items = self.data_manager.get_trade_sold(self.category_key)
        
        row, col = 0, 0
        cols = 3 # 3 columns grid
        
        # Ensure columns stretch equally
        for c in range(cols):
            self.sold_grid.setColumnStretch(c, 1)
        
        for item in items:
            card = QFrame()
            # Remove fixed size to allow responsiveness, but set min/max to maintain 3 per row visually
            card.setMinimumWidth(180) 
            card.setFixedHeight(280)
            card.setStyleSheet("background-color: rgba(255,255,255,0.05); border-radius: 10px;")
            
            # Use a container layout for the whole card
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(0)

            # Top overlay for image and delete button
            top_widget = QWidget()
            top_widget.setFixedHeight(160)
            top_layout = QGridLayout(top_widget)
            top_layout.setContentsMargins(0, 0, 0, 0)
            top_layout.setSpacing(0)

            # Image (background of top area)
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Check both photo_path and image_path
            img_path = item.get("photo_path") or item.get("image_path")
            
            if img_path:
                pix = self.data_manager.load_pixmap(img_path)
                if not pix.isNull():
                    scaled = pix.scaled(180, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    img_lbl.setPixmap(scaled)
                else:
                    img_lbl.setText("🖼️")
            else:
                img_lbl.setText("💰")
                
            img_lbl.setStyleSheet("font-size: 48px; background-color: rgba(0,0,0,0.1);")
            
            top_layout.addWidget(img_lbl, 0, 0)

            # Delete button (overlay on top right)
            del_btn = DeleteButtonOverlay(28)
            del_btn.setToolTip("Удалить из истории")
            del_btn.clicked.connect(lambda checked, i=item: self.delete_item(i.get('id'), True))
            
            # Position del_btn in top right
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addStretch()
            btn_layout.addWidget(del_btn)
            
            top_layout.addWidget(btn_container, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            
            card_layout.addWidget(top_widget)

            # Text Info Area
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(10, 5, 10, 10)
            
            name_lbl = QLabel(item.get("name"))
            name_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
            name_lbl.setWordWrap(True)
            info_layout.addWidget(name_lbl)
            
            profit = int(float(item.get("sell_price", 0)) - float(item.get("buy_price", 0)))
            show_coa = self.data_manager.get_setting("showCostOfAppearance", False)
            if show_coa:
                profit -= int(float(item.get("cost_of_appearance", 0)))
                
            color = "#2ecc71" if profit >= 0 else "#e74c3c"
            
            price_info_text = f"Прод: ${int(float(item.get('sell_price', 0))):,}"
            if show_coa:
                coa = int(float(item.get('cost_of_appearance', 0)))
                price_info_text += f" | Появ: ${coa:,}"
                
            price_info = QLabel(price_info_text)
            price_info.setStyleSheet("color: #aaa; font-size: 12px;")
            info_layout.addWidget(price_info)

            profit_lbl = QLabel(f"Прибыль: ${profit:,}")
            profit_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
            info_layout.addWidget(profit_lbl)
            
            card_layout.addWidget(info_widget)
            card_layout.addStretch()
            
            self.sold_grid.addWidget(card, row, col)
            
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def sell_item_dialog(self, item):
        dlg = InputDialog(self, "Продажа", f"Введите цену продажи для '{item['name']}':")
        if dlg.exec():
            price = dlg.get_value()
            if price:
                self.data_manager.sell_trade_item(self.category_key, item["id"], price)
                self.data_manager.data_changed.emit() # Force analytics cache refresh
                self.refresh_data()

    def delete_item(self, item_id, is_sold):
        msg = "Вы уверены, что хотите удалить этот товар?"
        if ConfirmationDialog(self, "Подтверждение", msg).exec():
            self.data_manager.delete_trade_item(self.category_key, item_id, is_sold)
            self.refresh_data()

    def export_data(self):
        try:
            import pandas as pd
            import openpyxl
        except ImportError:
            msg = "Для экспорта необходимо установить библиотеки pandas и openpyxl.\n\nЖелаете установить их сейчас автоматически?"
            if ConfirmationDialog(self, "Установка зависимостей", msg).exec():
                # Show a temporary overlay or just a message
                progress = AlertDialog(self, "Установка", "Установка библиотек... Пожалуйста, подождите.\nПриложение может ненадолго зависнуть.", "ОК")
                progress.show()
                QApplication.processEvents()
                
                try:
                    import subprocess
                    import sys
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
                    AlertDialog(self, "Успех", "Библиотеки успешно установлены! Попробуйте экспортировать еще раз.", "ОК").exec()
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка установки", f"Не удалось установить библиотеки автоматически:\n{str(e)}\n\nПожалуйста, выполните команду вручную:\npip install pandas openpyxl")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", "", "Excel Files (*.xlsx)")
        if not file_path:
            return

        if not file_path.endswith('.xlsx'):
            file_path += '.xlsx'

        try:
            inventory = self.data_manager.get_trade_inventory(self.category_key)
            sold = self.data_manager.get_trade_sold(self.category_key)

            # Prepare Inventory DataFrame
            inv_data = []
            for item in inventory:
                inv_data.append({
                    "Название": item.get("name"),
                    "Цена покупки ($)": float(item.get("buy_price", 0)),
                    "Примечание": item.get("note", ""),
                    "Дата": item.get("date", "")
                })
            
            # Prepare Sold DataFrame
            sold_data = []
            for item in sold:
                buy_price = float(item.get("buy_price", 0))
                sell_price = float(item.get("sell_price", 0))
                sold_data.append({
                    "Название": item.get("name"),
                    "Цена покупки ($)": buy_price,
                    "Цена продажи ($)": sell_price,
                    "Прибыль ($)": sell_price - buy_price,
                    "Примечание": item.get("note", ""),
                    "Дата": item.get("date", "")
                })

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                if inv_data:
                    pd.DataFrame(inv_data).to_excel(writer, sheet_name='На складе', index=False)
                if sold_data:
                    pd.DataFrame(sold_data).to_excel(writer, sheet_name='Продано', index=False)

            QMessageBox.information(self, "Успех", f"Отчет успешно сохранен в:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")


class BuySellTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 1. Top Navigation Bar (Like Settings)
        self.nav_bar = QFrame()
        self.nav_bar.setFixedHeight(60)
        self.nav_bar.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333;")
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(15)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.btn_group.idClicked.connect(self.switch_tab)
        
        # Tabs definition
        # Key corresponds to data category in data_manager
        self.tabs_def = [
            (0, "Одежда", "clothes_new"),
            (1, "Машины", "cars_trade"),
            (2, "Другое", "clothes") # Legacy "clothes" data moved here
        ]
        
        for idx, name, key in self.tabs_def:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(120, 40)
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 20px;
                    color: #aaa;
                    font-weight: bold;
                    background: transparent;
                    font-size: 14px;
                }
                QPushButton:checked {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton:hover:!checked {
                    color: white;
                }
            """)
            self.btn_group.addButton(btn, idx)
            nav_layout.addWidget(btn)
            
            if idx == 0:
                btn.setChecked(True)
        
        nav_layout.addStretch()
        self.layout.addWidget(self.nav_bar)
        
        # 2. Content Stack
        self.stack = QStackedWidget()
        self.widgets = {}
        
        for idx, name, key in self.tabs_def:
            widget = TradeItemWidget(data_manager, main_window, key)
            self.stack.addWidget(widget)
            self.widgets[idx] = widget
            
        self.layout.addWidget(self.stack)
        
    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        # Optional: refresh data when switching
        self.widgets[index].refresh_data()
        
    def apply_theme(self, theme_name):
        # Propagate theme to all sub-widgets
        for idx, widget in self.widgets.items():
            widget.apply_theme(theme_name)
        
        t = StyleManager.get_theme(theme_name)
        self.nav_bar.setStyleSheet(f"background-color: {t['bg_secondary']}; border-bottom: 1px solid {t['border']};")
