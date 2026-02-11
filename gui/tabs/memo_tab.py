from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QScrollArea, QGridLayout, QLineEdit, QTextEdit, QSizePolicy,
    QSpinBox, QDialog, QFileDialog, QApplication, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QByteArray, QSize, QBuffer, QIODevice, pyqtSignal, QMimeData, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QTextOption, QKeySequence
from PyQt6.QtSvg import QSvgRenderer
import os
import logging
from gui.custom_dialogs import StyledDialogBase, AlertDialog, ConfirmationDialog
from gui.tabs.helper_tab import ImageZoomDialog
from gui.styles import StyleManager

def create_svg_icon(svg_content, size=24):
    renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

PENCIL_SVG = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3 17.25V21H6.75L17.81 9.94L14.06 6.19L3 17.25ZM20.71 7.04C21.1 6.65 21.1 6.02 20.71 5.63L18.37 3.29C17.98 2.9 17.35 2.9 16.96 3.29L15.13 5.12L18.88 8.87L20.71 7.04Z" fill="white"/>
</svg>
"""

CROSS_SVG = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M19 6.41L17.59 5L12 10.59L6.41 5L5 6.41L10.59 12L5 17.59L6.41 19L12 13.41L17.59 19L19 17.59L13.41 12L19 6.41Z" fill="#ff5555"/>
</svg>
"""

class AutoResizingTextEdit(QTextEdit):
    image_pasted = pyqtSignal(QMimeData)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.default_font_size = 11
        self.min_font_size = 8
        self.textChanged.connect(self.adjust_font_size)
        
        font = self.font()
        font.setPointSize(self.default_font_size)
        self.setFont(font)

    def insertFromMimeData(self, source):
        if source.hasImage():
            self.image_pasted.emit(source)
        else:
            super().insertFromMimeData(source)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_font_size()

    def adjust_font_size(self):
        # Dynamic font sizing based on text length and widget width
        text = self.toPlainText()
        text_len = len(text)
        
        # Heuristic: ratio of text length to widget width
        # If we have a lot of text in a narrow space, shrink font
        width = self.viewport().width()
        if width <= 0: return

        font = self.font()
        current_size = self.default_font_size

        # Simple thresholding based on characters per (approximate) line width
        # Assuming avg char width is ~8px at size 11
        chars_per_line = width / 8
        estimated_lines = text_len / chars_per_line if chars_per_line > 0 else 1

        if estimated_lines > 10: # If it looks like > 10 lines
            current_size = 9
        elif estimated_lines > 5:
            current_size = 10
        elif text_len > 300: # Fallback to absolute length
            current_size = 8
        elif text_len > 150:
            current_size = 10

        # Ensure valid point size (> 0)
        final_size = int(max(6, current_size))
        if final_size > 0:
            font.setPointSize(final_size)
            self.setFont(font)
        
        # Auto-resize height
        doc_height = self.document().size().height()
        h = int(doc_height + 15)
        h = max(h, 60)
        h = min(h, 300) # Cap height to avoid taking too much space
        if self.height() != h:
            self.setFixedHeight(h)

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MemoTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header / Toolbar
        toolbar_layout = QHBoxLayout()
        
        header = QLabel("Блокнот")
        header.setObjectName("Header")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        self.add_btn = QPushButton("Добавить раздел")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Increase width to ensure text is visible
        self.add_btn.setFixedSize(160, 40)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71; 
                color: white; 
                border: none; 
                border-radius: 5px; 
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.add_btn.clicked.connect(self.add_section_dialog)
        
        toolbar_layout.addWidget(header)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.add_btn)
        
        self.layout.addLayout(toolbar_layout)
        
        # Scroll Area for Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.grid_container)
        self.layout.addWidget(self.scroll_area)
        
        self.is_initialized = False
        # self.refresh_data() # Deferred loading

    def showEvent(self, event):
        if not self.is_initialized:
            self.refresh_data()
            self.is_initialized = True
        super().showEvent(event)

    def apply_theme(self, theme_name):
        t = StyleManager.get_theme(theme_name)
        
        self.setStyleSheet(f"background-color: {t['bg_main']};")
        
        # Main Add Button
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['success']};
                border: 1px solid {t['success']};
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {t['success']}1A;
            }}
        """)
        
        # Apply to all section widgets
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), MemoSection):
                item.widget().apply_theme(t)
        
    def refresh_data(self):
        # Save scroll position
        v_scroll = self.scroll_area.verticalScrollBar().value()

        # Clear existing items
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        # Load sections
        sections = self.data_manager.get_memo_sections()
        t = StyleManager.get_theme(self.main_window.current_theme if hasattr(self.main_window, 'current_theme') else 'dark')

        # Populate grid (3 columns wide)
        columns = 3
        for i, section in enumerate(sections):
            row = i // columns
            col = i % columns
            
            sec_widget = MemoSection(self.data_manager, section, self)
            sec_widget.apply_theme(t)
            self.grid_layout.addWidget(sec_widget, row, col)
            
        # Restore scroll position
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(v_scroll)

    def add_section_dialog(self):
        dialog = MemoSectionSetupDialog(self, "Новый раздел")
        if dialog.exec():
            title, headers = dialog.get_data()
            if title and headers:
                if self.data_manager.add_memo_section(title, headers):
                    self.refresh_data()
                else:
                    AlertDialog(self, "Ошибка", "Не удалось создать раздел.").exec()

    def delete_section(self, section_id):
        if self.data_manager.delete_memo_section(section_id):
            self.refresh_data()

class MemoSection(QFrame):
    def __init__(self, data_manager, section_data, parent_tab):
        super().__init__()
        self.data_manager = data_manager
        self.section_id = section_data["id"]
        self.title = section_data["title"]
        self.headers = section_data.get("headers", ["№", "Статья", "Наказание"]) # Fallback
        self.parent_tab = parent_tab
        
        # Ensure minimum width for responsive layout with scrolling
        self.setMinimumWidth(350)
        
        # Style the frame
        self.setObjectName("MemoSectionFrame")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # Header Row
        header_layout = QHBoxLayout()
        
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setObjectName("Header")
        
        # Edit Title Button
        edit_title_btn = QPushButton()
        edit_title_btn.setIcon(create_svg_icon(PENCIL_SVG))
        edit_title_btn.setIconSize(QSize(20, 20))
        edit_title_btn.setFixedSize(30, 30)
        edit_title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_title_btn.setToolTip("Изменить название")
        edit_title_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        edit_title_btn.clicked.connect(self.edit_title)
        self.edit_title_btn = edit_title_btn
        
        # Delete Section Button
        del_sec_btn = QPushButton()
        del_sec_btn.setIcon(create_svg_icon(CROSS_SVG))
        del_sec_btn.setIconSize(QSize(20, 20))
        del_sec_btn.setFixedSize(30, 30)
        del_sec_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_sec_btn.setToolTip("Удалить раздел")
        del_sec_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        del_sec_btn.clicked.connect(self.delete_section)
        self.del_sec_btn = del_sec_btn
        
        header_layout.addWidget(self.title_lbl)
        header_layout.addWidget(edit_title_btn)
        header_layout.addStretch()
        header_layout.addWidget(del_sec_btn)
        
        self.layout.addLayout(header_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Try to make first column fit contents if it's small (like "No")
        if len(self.headers) > 0:
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet("""
            QTableWidget::item:hover { background-color: transparent; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
            QTableWidget::item:selected:hover { background-color: #3498db; color: white; }
        """)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self.edit_item)
        # self.table.setMinimumHeight(200) # Give it some height
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Добавить")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_item)
        
        self.edit_btn = QPushButton("Изменить")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self.edit_selected)
        
        self.del_btn = QPushButton("Удалить")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.clicked.connect(self.delete_item)
        
        self.add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.edit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.del_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        
        self.layout.addLayout(btn_layout)

    def apply_theme(self, t):
        self.setStyleSheet(f"""
            QFrame#MemoSectionFrame {{
                background-color: {t['bg_secondary']};
                border-radius: 10px;
                border: 1px solid {t['border']};
            }}
        """)
        
        self.title_lbl.setStyleSheet(f"color: {t['text_main']}; font-size: 18px; font-weight: bold; border: none; background: transparent;")
        
        # Table
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {t['bg_tertiary']};
                color: {t['text_main']};
                border: 1px solid {t['border']};
                border-radius: 5px;
                gridline-color: {t['border']};
            }}
            QHeaderView::section {{
                background-color: {t['bg_secondary']};
                color: {t['text_secondary']};
                padding: 5px;
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QTableWidget::item:selected {{
                background-color: {t['accent']};
                color: white;
            }}
        """)
        
        # Action Buttons (Add/Edit/Delete)
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {t['text_main']};
                border: 1px solid {t['border']};
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t['bg_tertiary']};
                color: {t['accent']};
                border-color: {t['accent']};
            }}
        """
        self.add_btn.setStyleSheet(btn_style)
        self.edit_btn.setStyleSheet(btn_style)
        self.del_btn.setStyleSheet(btn_style)
        
        # Header Buttons (Edit Title, Delete Section)
        header_btn_style = f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {t['bg_tertiary']};
            }}
        """
        self.edit_title_btn.setStyleSheet(header_btn_style)
        self.del_sec_btn.setStyleSheet(header_btn_style)
        
        self.items = []
        self.refresh_table_data()
        
    def refresh_table_data(self):
        self.items = self.data_manager.get_memo_items(self.section_id)
        
        # Add "Фото" header if not present
        headers = list(self.headers)
        headers.append("Фото")
        
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # Enable horizontal scrolling by using Interactive mode instead of Stretch
        # This prevents columns from being too narrow on small screens
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        
        # Image column fixed size
        photo_col_idx = len(headers) - 1
        self.table.horizontalHeader().setSectionResizeMode(photo_col_idx, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(photo_col_idx, 60)
        
        # Set default width for other columns to ensure readability
        for i in range(len(headers) - 1):
             self.table.setColumnWidth(i, 150)
        
        # Logic to fill space: Stretch the last text column (usually "Punishment" or "Note")
        if len(headers) > 1:
             # Last text column is at index len(headers) - 2
             last_text_col = len(headers) - 2
             self.table.horizontalHeader().setSectionResizeMode(last_text_col, QHeaderView.ResizeMode.Stretch)

        if len(headers) > 2:
             # First column (No) to content if it exists
             self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setRowCount(0)
        self.table.setWordWrap(True) # Enable word wrap
        
        for item in self.items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Handle legacy data (col1, col2, col3) vs new data (values list)
            values = item.get("values", [])
            if not values and "col1" in item:
                 # Migration on the fly for display
                 values = [item.get("col1", ""), item.get("col2", ""), item.get("col3", "")]
            
            # Ensure values list matches header length (excluding Photo)
            while len(values) < len(self.headers):
                values.append("")
                
            for i, val in enumerate(values):
                if i < self.table.columnCount() - 1:
                    t_item = QTableWidgetItem(str(val))
                    t_item.setFlags(t_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Read-only
                    self.table.setItem(row, i, t_item)
            
            # Photo Column
            image_path = item.get("image_path")
            photo_item = QTableWidgetItem()
            photo_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            if image_path:
                pix = self.data_manager.load_pixmap(image_path)
                
                if not pix.isNull():
                    # Scale to icon size
                    icon_pix = pix.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    photo_item.setData(Qt.ItemDataRole.DecorationRole, icon_pix)
                    photo_item.setToolTip("Нажмите для просмотра")
                        
            self.table.setItem(row, len(headers)-1, photo_item)
            
        self.table.resizeRowsToContents()
        self.adjust_table_height()

    def adjust_table_height(self):
        # Calculate total height of table content to prevent internal vertical scrolling
        height = self.table.horizontalHeader().height()
        
        # Iterate rows to get exact height (resizeRowsToContents was called just before)
        for i in range(self.table.rowCount()):
            height += self.table.rowHeight(i)
        
        # Add buffer for borders/margins
        height += 5
        
        # Ensure a minimum height (e.g., enough for header + ~3 empty rows or just a min size)
        # But user wants to see "first three columns" (maybe rows?) fully. 
        # If we interpret "first three columns" as horizontal columns, we just need to ensure 
        # the table is tall enough not to show a vertical scrollbar that might obscure the right side.
        
        # Setting a minimum height of 250px (approx 7-8 rows) to ensure first 3 columns/rows are visible
        height = max(height, 250)
        
        self.table.setFixedHeight(height)

    def add_item(self):
        dialog = MemoEditDialog(self, f"Добавить запись", headers=self.headers)
        if dialog.exec():
            try:
                values, image_path = dialog.get_data()
                logging.info(f"Adding item to section {self.section_id}: values={values}, image={image_path}")
                if self.data_manager.add_memo_item(self.section_id, values, image_path):
                    self.refresh_table_data()
                    logging.info("Item added and table refreshed")
                else:
                    logging.error("Failed to add memo item (data_manager returned False)")
                    AlertDialog(self, "Ошибка", "Не удалось сохранить запись.").exec()
            except Exception as e:
                logging.error(f"Error adding memo item: {e}", exc_info=True)
                AlertDialog(self, "Ошибка", f"Произошла ошибка при сохранении: {e}").exec()
            
    def edit_item(self, item_widget):
        # item_widget is just used to trigger
        # If triggered by double click (item_widget not None), use its row
        row = -1
        if item_widget:
             row = item_widget.row()
        else:
             row = self.get_selected_row()
             
        if row < 0 or row >= len(self.items):
            # No alert here as it might be double click on empty area (though unlikely with SelectRows)
            return
            
        # Check if clicked on Photo column (last column)
        col = -1
        if item_widget:
            col = item_widget.column()
            
        memo_item = self.items[row]
        
        # If clicked on photo column and there is an image, open zoom
        if col == self.table.columnCount() - 1 and memo_item.get("image_path"):
            self.show_image_zoom(memo_item.get("image_path"))
            return
        
        # Ensure we have a valid ID (fallback for really old data in memory, though migration handles this)
        if "id" not in memo_item:
             AlertDialog(self, "Ошибка", "Некорректная запись (нет ID). Попробуйте перезапустить приложение.").exec()
             return

        dialog = MemoEditDialog(self, f"Изменить запись", headers=self.headers, item=memo_item)
        if dialog.exec():
            try:
                values, image_path = dialog.get_data()
                logging.info(f"Updating item {memo_item.get('id')} in section {self.section_id}: values={values}, image={image_path}")
                if self.data_manager.update_memo_item(self.section_id, memo_item["id"], values, image_path):
                    self.refresh_table_data()
                    logging.info("Item updated and table refreshed")
                else:
                    logging.error("Failed to update memo item (data_manager returned False)")
                    AlertDialog(self, "Ошибка", "Не удалось сохранить изменения.").exec()
            except Exception as e:
                logging.error(f"Error updating memo item: {e}", exc_info=True)
                AlertDialog(self, "Ошибка", f"Произошла ошибка при сохранении: {e}").exec()

    def show_image_zoom(self, image_path):
        pix = self.data_manager.load_pixmap(image_path)
        if not pix.isNull():
            ImageZoomDialog(pix, self).exec()

    def get_selected_row(self):
        row = self.table.currentRow()
        if row >= 0:
            return row
        
        # Fallback to selected items if currentRow is lost
        selected = self.table.selectedItems()
        if selected:
            return selected[0].row()
            
        return -1

    def edit_selected(self):
        row = self.get_selected_row()
        if row < 0:
            AlertDialog(self, "Ошибка", "Выберите запись для изменения").exec()
            return
        # Trigger edit with the first item of the row
        self.edit_item(self.table.item(row, 0))

    def delete_item(self):
        row = self.get_selected_row()
        if row < 0:
            AlertDialog(self, "Ошибка", "Выберите запись для удаления").exec()
            return
        
        if row >= len(self.items):
            return
        
        memo_item = self.items[row]
        
        confirm = ConfirmationDialog(self, "Подтверждение", "Удалить запись?")
        if confirm.exec():
            if self.data_manager.delete_memo_item(self.section_id, memo_item["id"]):
                self.refresh_table_data()
            else:
                 AlertDialog(self, "Ошибка", "Не удалось удалить запись.").exec()
            


    def edit_title(self):
        # Only editing title for now, not structure
        dialog = MemoSectionNameDialog(self, "Переименовать раздел", self.title)
        if dialog.exec():
            new_title = dialog.get_text()
            if new_title and new_title != self.title:
                self.data_manager.update_memo_section_title(self.section_id, new_title)
                self.title = new_title
                self.title_lbl.setText(new_title)
                
    def delete_section(self):
        confirm = ConfirmationDialog(self, "Удаление раздела", f"Удалить раздел '{self.title}' и все его записи?")
        if confirm.exec():
            self.parent_tab.delete_section(self.section_id)

class MemoSectionNameDialog(StyledDialogBase):
    def __init__(self, parent, title, text=""):
        super().__init__(parent, title)
        self.resize(400, 280)
        
        t = StyleManager.get_theme(self._theme)
        
        self.input = QLineEdit()
        self.input.setText(text)
        self.input.setPlaceholderText("Название раздела")
        self.content_layout.addWidget(QLabel("Название:"))
        self.content_layout.addWidget(self.input)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['success']};
                border: 1px solid {t['success']};
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t['success']}1A;
            }}
        """)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['danger']};
                border: 1px solid {t['danger']};
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t['danger']}1A;
            }}
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        self.content_layout.addLayout(btn_layout)
        
    def get_text(self):
        return self.input.text()

class MemoSectionSetupDialog(StyledDialogBase):
    def __init__(self, parent, title="Новый раздел"):
        super().__init__(parent, title, width=700)
        self.resize(700, 550)
        
        # Use styles from StyledDialogBase (self.text_color, etc.)
        
        # --- Title Input ---
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 10)
        title_layout.setSpacing(5)
        
        lbl_title = QLabel("Название раздела")
        lbl_title.setStyleSheet(f"color: {self.secondary_text_color}; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;")
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Например: Кодекс Этики")
        self.title_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.input_bg}; 
                color: {self.text_color};
                border: 1px solid {self.input_border};
                border-radius: 8px;
                padding: 12px;
                font-size: 15px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.accent_color};
                background-color: {self.input_bg};
            }}
        """)
        
        title_layout.addWidget(lbl_title)
        title_layout.addWidget(self.title_input)
        self.content_layout.addWidget(title_container)
        
        # --- Settings Section (Columns) ---
        settings_container = QWidget()
        settings_layout = QHBoxLayout(settings_container)
        settings_layout.setContentsMargins(0, 0, 0, 10)
        
        lbl_col = QLabel("Количество столбцов")
        lbl_col.setStyleSheet(f"color: {self.secondary_text_color}; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;")
        
        self.col_spin = QSpinBox()
        self.col_spin.setRange(1, 7)
        self.col_spin.setValue(3)
        self.col_spin.setFixedWidth(100)
        self.col_spin.setFixedHeight(38)
        # Use global spinbox style via StyledDialogBase or explicit if needed
        # StyledDialogBase sets QSpinBox style in container stylesheet, but we can refine it
        
        self.col_spin.valueChanged.connect(self.update_column_inputs)
        
        settings_layout.addWidget(lbl_col)
        settings_layout.addWidget(self.col_spin)
        settings_layout.addStretch()
        self.content_layout.addWidget(settings_container)
        
        # --- Grid Section ---
        # Scroll Area for Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.columns_container = QWidget()
        self.columns_container.setStyleSheet("background: transparent;")
        
        # Grid Layout: 3 columns fixed width
        self.columns_layout = QGridLayout(self.columns_container)
        self.columns_layout.setContentsMargins(5, 5, 5, 5)
        self.columns_layout.setSpacing(15)
        self.columns_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Ensure 3 columns are equally stretched
        for col_idx in range(3):
            self.columns_layout.setColumnStretch(col_idx, 1)
        
        self.scroll_area.setWidget(self.columns_container)
        self.content_layout.addWidget(self.scroll_area)
        
        # Store widgets and placeholders
        self.column_widgets = []
        self.placeholders = []
        
        # Initial inputs
        self.update_column_inputs()
        
        # --- Footer Section (Buttons) ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        # Use create_button from StyledDialogBase if available, or manual matching style
        save_btn = self.create_button("Создать", role="primary", clicked_slot=self.accept)
        cancel_btn = self.create_button("Отмена", role="secondary", clicked_slot=self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        self.content_layout.addLayout(btn_layout)
        
    def update_column_inputs(self):
        # 1. Clear ALL placeholders FIRST
        self.clear_placeholders()
        
        target_count = self.col_spin.value()
        current_count = len(self.column_widgets)
        
        # 2. Update active widgets
        if target_count > current_count:
            # Add new columns
            for i in range(current_count, target_count):
                self.add_column_widget(i)
        elif target_count < current_count:
            # Remove columns from end
            for i in range(current_count - 1, target_count - 1, -1):
                self.remove_column_widget(i)
        
        # 3. Add new placeholders if needed
        self.update_placeholders(target_count)
        
        # Force layout update to prevent invisibility
        self.columns_container.adjustSize()
        self.columns_layout.activate()

    def clear_placeholders(self):
        # Explicitly remove from layout and delete
        for p in self.placeholders:
            if p is not None:
                self.columns_layout.removeWidget(p)
                p.setParent(None)
                p.deleteLater()
        self.placeholders = []
                
    def update_placeholders(self, count):
        remainder = count % 3
        if remainder != 0:
            missing = 3 - remainder
            start_idx = count
            for i in range(missing):
                idx = start_idx + i
                row = idx // 3
                col = idx % 3
                
                p = QFrame()
                p.setStyleSheet(f"""
                    background-color: {self.input_bg}40;
                    border: 2px dashed {self.input_border};
                    border-radius: 8px;
                """)
                p.setFixedHeight(75) # Match approx height of widget
                
                l = QLabel("—", p)
                l.setAlignment(Qt.AlignmentFlag.AlignCenter)
                l.setStyleSheet(f"color: {self.secondary_text_color}; opacity: 0.3; font-size: 20px;")
                pl = QVBoxLayout(p)
                pl.addWidget(l)
                
                self.columns_layout.addWidget(p, row, col)
                self.placeholders.append(p)
                
    def add_column_widget(self, index):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Compact, cleaner card look matching global inputs
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {self.input_bg};
                border-radius: 8px;
                border: 1px solid {self.input_border};
            }}
        """)
        
        lbl = QLabel(f"Столбец {index+1}")
        lbl.setStyleSheet(f"color: {self.secondary_text_color}; font-size: 11px; font-weight: 600; border: none; background: transparent; text-transform: uppercase;")
        
        inp = QLineEdit()
        hints = ["№", "Статья", "Наказание", "Примечание", "Доп. инфо", "Срок", "Штраф", "Уровень", "Тип"]
        if index < len(hints):
            inp.setPlaceholderText(hints[index])
        else:
            inp.setPlaceholderText(f"Заголовок")
            
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {self.text_color};
                border: none;
                border-bottom: 1px solid {self.input_border};
                border-radius: 0px;
                padding: 4px 0px;
                font-size: 14px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border-bottom: 2px solid {self.accent_color};
            }}
            QLineEdit:hover {{
                border-bottom: 1px solid {self.text_color};
            }}
        """)
        
        layout.addWidget(lbl)
        layout.addWidget(inp)
        
        # Grid positioning: 3 columns per row
        row = index // 3
        col = index % 3
        self.columns_layout.addWidget(container, row, col)
        
        self.column_widgets.append({
            "container": container,
            "input": inp
        })
        
        # Animation - ensure end value is definitely 1 and cleanup
        effect = QGraphicsOpacityEffect(container)
        effect.setOpacity(0) # Start invisible
        container.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Cleanup effect after animation to ensure full visibility and performance
        # (Removing effect restores default painting which is fully opaque)
        anim.finished.connect(lambda: container.setGraphicsEffect(None))
        
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        container.anim = anim

    def remove_column_widget(self, index):
        if 0 <= index < len(self.column_widgets):
            data = self.column_widgets.pop(index)
            container = data["container"]
            
            # Explicitly remove from layout immediately
            self.columns_layout.removeWidget(container)
            container.setParent(None)
            container.deleteLater()
            
    def accept(self):
        title = self.title_input.text().strip()
        if not title:
            AlertDialog(self, "Ошибка", "Введите название раздела").exec()
            self.title_input.setFocus()
            return
        super().accept()

    def get_data(self):
        title = self.title_input.text().strip()
        headers = []
        for item in self.column_widgets:
            inp = item["input"]
            text = inp.text().strip()
            if not text:
                text = inp.placeholderText()
            headers.append(text)
        return title, headers

class MemoEditDialog(StyledDialogBase):
    def __init__(self, parent, title, headers=None, item=None):
        super().__init__(parent, title)
        self.resize(500, 600)
        self.inputs = []
        self.image_path = None
        self.parent_tab = parent
        
        if not headers:
            headers = ["Поле 1", "Поле 2", "Поле 3"]
            
        # Pre-fill values if item exists
        values = []
        if item:
            values = item.get("values", [])
            # Legacy fallback
            if not values and "col1" in item:
                values = [item.get("col1", ""), item.get("col2", ""), item.get("col3", "")]
            self.image_path = item.get("image_path")
        
        # Scroll Area for Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 10, 0) # Right margin for scrollbar
        layout.setSpacing(15)
        
        # Create inputs dynamically
        for i, header in enumerate(headers):
            lbl = QLabel(f"{header}:")
            lbl.setStyleSheet(f"color: {self.text_color}; font-weight: bold;")
            
            inp = AutoResizingTextEdit()
            inp.image_pasted.connect(self.handle_pasted_image)
            # Allow resizing, min height 60
            inp.setMinimumHeight(60)
            if i < len(values):
                inp.setPlainText(str(values[i]))
            
            self.inputs.append(inp)
            layout.addWidget(lbl)
            layout.addWidget(inp)
            
        # Image Section
        img_label = QLabel("Фото:")
        img_label.setStyleSheet(f"color: {self.text_color}; font-weight: bold;")
        layout.addWidget(img_label)
        
        img_layout = QHBoxLayout()
        self.preview_lbl = ClickableLabel()
        self.preview_lbl.setFixedSize(100, 100)
        self.preview_lbl.setStyleSheet(f"border: 1px dashed {self.secondary_text_color}; border-radius: 5px;")
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setText("Нет фото")
        self.preview_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_lbl.setToolTip("Нажмите для просмотра в полном размере")
        self.preview_lbl.clicked.connect(self.show_zoom)
        
        if self.image_path:
            self.load_preview()
            
        btn_layout = QVBoxLayout()
        sel_img_btn = QPushButton("Выбрать фото")
        sel_img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_img_btn.clicked.connect(self.select_image)
        sel_img_btn.setToolTip("Выберите файл или нажмите Ctrl+V для вставки из буфера обмена")
        sel_img_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; border-radius: 4px; padding: 6px; border: none; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        
        clr_img_btn = QPushButton("Удалить фото")
        clr_img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clr_img_btn.clicked.connect(self.clear_image)
        clr_img_btn.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border-radius: 4px; padding: 6px; border: none; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        
        btn_layout.addWidget(sel_img_btn)
        btn_layout.addWidget(clr_img_btn)
        btn_layout.addStretch()
        
        img_layout.addWidget(self.preview_lbl)
        img_layout.addLayout(btn_layout)
        layout.addLayout(img_layout)
        
        # Add container to scroll
        scroll.setWidget(container)
        self.content_layout.addWidget(scroll)
            
        # Dialog Buttons
        dlg_btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("background-color: #2ecc71; color: white; border: none; padding: 8px 15px; border-radius: 4px; font-weight: bold;")
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("background-color: #e74c3c; color: white; border: none; padding: 8px 15px; border-radius: 4px; font-weight: bold;")
        
        dlg_btn_layout.addStretch()
        dlg_btn_layout.addWidget(save_btn)
        dlg_btn_layout.addWidget(cancel_btn)
        self.content_layout.addLayout(dlg_btn_layout)
        
    def load_preview(self):
        if not self.image_path:
            self.preview_lbl.setText("Нет фото")
            self.preview_lbl.setPixmap(QPixmap())
            return
            
        # Use parent's data manager to load
        dm = self.parent_tab.data_manager
        pix = dm.load_pixmap(self.image_path)
        
        if not pix.isNull():
            self.preview_lbl.setPixmap(pix.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.preview_lbl.setText("")
        else:
             self.preview_lbl.setText("Ошибка")

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.image_path = path 
            pix = QPixmap(path)
            self.preview_lbl.setPixmap(pix.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.preview_lbl.setText("")

    def clear_image(self):
        self.image_path = None
        self.load_preview()

    def handle_pasted_image(self, mime_data):
        if mime_data.hasImage():
            pixmap = QPixmap(mime_data.imageData())
            if not pixmap.isNull():
                dm = self.parent_tab.data_manager
                self.image_path = dm.save_image_to_base64(pixmap)
                self.load_preview()
                return

        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        pixmap = QPixmap(file_path)
                        if not pixmap.isNull():
                            dm = self.parent_tab.data_manager
                            self.image_path = dm.save_image_to_base64(pixmap)
                            self.load_preview()
                        return

    def show_zoom(self):
        if self.image_path:
             dm = self.parent_tab.data_manager
             pix = dm.load_pixmap(self.image_path)
             if not pix.isNull():
                 ImageZoomDialog(pix, self).exec()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste):
            clipboard = QApplication.clipboard()
            self.handle_pasted_image(clipboard.mimeData())
        super().keyPressEvent(event)

    def get_data(self):
        values = [inp.toPlainText() for inp in self.inputs]
        
        # Process image
        final_image_path = self.image_path
        
        # If it's a local file path (not base64 and not relative in appdata), convert to base64
        if final_image_path and not final_image_path.startswith("data:image") and os.path.isabs(final_image_path):
             # Convert to base64
             dm = self.parent_tab.data_manager
             pix = QPixmap(final_image_path)
             if not pix.isNull():
                 final_image_path = dm.save_image_to_base64(pix)
        
        return values, final_image_path