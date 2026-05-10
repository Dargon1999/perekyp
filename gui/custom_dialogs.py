from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
    QFrame, QLineEdit, QApplication, QGraphicsDropShadowEffect,
    QListWidget, QAbstractItemView, QProgressBar, QWidget, QSizeGrip,
    QFileDialog, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect, QTimer, QEvent
from PyQt6.QtGui import QColor, QDoubleValidator, QCursor
import os
import json
import zipfile

from gui.styles import StyleManager
from gui.animations import AnimationManager

class ResizeMixin:
    def setup_resizing(self):
        self._resizing = False
        self._resize_edge = None
        self._resize_margin = 10
        self._resizable = True 
        self._movable = True # New flag to control background dragging
        self.setMouseTracking(True)
        # Size Grip for bottom-right corner
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background: transparent;")
        self.size_grip.resize(20, 20)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if not self._resizable:
            return super().eventFilter(obj, event) if hasattr(super(), 'eventFilter') else False

        if event.type() in [QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease]:
            # Use QCursor.pos() for global position and map to local
            global_pos = QCursor.pos()
            pos = self.mapFromGlobal(global_pos)
            
            edge = self._get_resize_edge(pos)
            
            if edge and not self._resizing:
                if event.type() == QEvent.Type.MouseMove:
                    self._update_cursor(edge)
                elif event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                    self._resizing = True
                    self._resize_edge = edge
                    self._drag_pos = global_pos
                    return True
            elif not self._resizing and event.type() == QEvent.Type.MouseMove:
                # Reset cursor if not on edge and not resizing
                if self.cursor().shape() in [
                    Qt.CursorShape.SizeHorCursor, 
                    Qt.CursorShape.SizeVerCursor, 
                    Qt.CursorShape.SizeFDiagCursor, 
                    Qt.CursorShape.SizeBDiagCursor
                ]:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
            
            if self._resizing:
                if event.type() == QEvent.Type.MouseMove:
                    self._handle_resize(global_pos)
                elif event.type() == QEvent.Type.MouseButtonRelease:
                    self._resizing = False
                    self._resize_edge = None
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                return True

        return super().eventFilter(obj, event) if hasattr(super(), 'eventFilter') else False
        
    def set_resizable(self, enabled):
        self._resizable = enabled
        if hasattr(self, 'size_grip'):
            self.size_grip.setVisible(enabled)

    def set_movable(self, enabled):
        self._movable = enabled

    def resizeEvent(self, event):
        if hasattr(self, 'size_grip'):
            self.size_grip.move(self.width() - 20, self.height() - 20)
        # Safely call super().resizeEvent if it exists in MRO
        try:
            super().resizeEvent(event)
        except (AttributeError, TypeError):
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._resizable:
                edge = self._get_resize_edge(event.pos())
                if edge:
                    self._resizing = True
                    self._resize_edge = edge
                    self._drag_pos = event.globalPosition().toPoint()
                    event.accept()
                    return
            
            # Start moving logic if not resizing and moving is enabled
            if hasattr(self, '_movable') and self._movable:
                self._moving = True
                self._drag_pos = event.globalPosition().toPoint()
                event.accept()
                return
        try:
            super().mousePressEvent(event)
        except (AttributeError, TypeError):
            pass

    def mouseMoveEvent(self, event):
        if self._resizing and self._resizable:
            self._handle_resize(event.globalPosition().toPoint())
            event.accept()
        elif hasattr(self, '_moving') and self._moving:
             # Handle moving
             diff = event.globalPosition().toPoint() - self._drag_pos
             self.move(self.pos() + diff)
             self._drag_pos = event.globalPosition().toPoint()
             event.accept()
        else:
            if self._resizable:
                edge = self._get_resize_edge(event.pos())
                if edge:
                    self._update_cursor(edge)
                    return
            
            self.setCursor(Qt.CursorShape.ArrowCursor)
            try:
                super().mouseMoveEvent(event)
            except (AttributeError, TypeError):
                pass

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._resizing = False
            self._moving = False # Reset moving
            self._resize_edge = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        try:
            super().mouseReleaseEvent(event)
        except (AttributeError, TypeError):
            pass

    def _get_resize_edge(self, pos):
        m = self._resize_margin
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        
        edge = 0
        if x < m: edge |= 1 # Left
        if x > w - m: edge |= 2 # Right
        if y < m: edge |= 4 # Top
        if y > h - m: edge |= 8 # Bottom
        
        return edge if edge else None

    def _update_cursor(self, edge):
        cursors = {
            1: Qt.CursorShape.SizeHorCursor,
            2: Qt.CursorShape.SizeHorCursor,
            4: Qt.CursorShape.SizeVerCursor,
            8: Qt.CursorShape.SizeVerCursor,
            5: Qt.CursorShape.SizeFDiagCursor, # Top-Left
            10: Qt.CursorShape.SizeFDiagCursor, # Bottom-Right
            6: Qt.CursorShape.SizeBDiagCursor, # Top-Right
            9: Qt.CursorShape.SizeBDiagCursor, # Bottom-Left
        }
        self.setCursor(cursors.get(edge, Qt.CursorShape.ArrowCursor))

    def _handle_resize(self, global_pos):
        diff = global_pos - self._drag_pos
        
        geo = self.geometry()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        
        # New geometry variables
        new_x, new_y, new_w, new_h = x, y, w, h
        
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()
        max_w = self.maximumWidth()
        max_h = self.maximumHeight()
        
        if self._resize_edge & 1: # Left
            potential_w = w - diff.x()
            if potential_w < min_w:
                diff_x = w - min_w
                new_x += diff_x
                new_w = min_w
            elif potential_w > max_w:
                diff_x = w - max_w
                new_x += diff_x
                new_w = max_w
            else:
                new_x += diff.x()
                new_w = potential_w
                
        if self._resize_edge & 2: # Right
            new_w = max(min_w, min(max_w, w + diff.x()))
            
        if self._resize_edge & 4: # Top
            potential_h = h - diff.y()
            if potential_h < min_h:
                diff_y = h - min_h
                new_y += diff_y
                new_h = min_h
            elif potential_h > max_h:
                diff_y = h - max_h
                new_y += diff_y
                new_h = max_h
            else:
                new_y += diff.y()
                new_h = potential_h
                
        if self._resize_edge & 8: # Bottom
            new_h = max(min_h, min(max_h, h + diff.y()))
            
        self.setGeometry(new_x, new_y, new_w, new_h)
        self._drag_pos = global_pos

class StyledDialogBase(ResizeMixin, QDialog):
    _theme = "dark"

    @classmethod
    def set_global_theme(cls, theme_name):
        cls._theme = theme_name

    def __init__(self, parent, title, width=400):
        super().__init__(parent)
        self.setup_resizing()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Internal state for maximization
        self._is_maximized = False
        self._normal_geometry = None

        # Reduced default size and set minimum
        target_width = int(width * 0.7) if width > 320 else width
        if target_width < 320: target_width = 320
        self.resize(target_width, 250)
        self.setMinimumWidth(320)
        self.setMinimumHeight(200)
        
        self.setWindowTitle(title)
        self.setAccessibleName(title)
        self.setAccessibleDescription(f"Dialog window: {title}")

        # Animation Setup
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Theme colors from StyleManager
        t = StyleManager.get_theme(self._theme)
        
        bg_color = t['bg_secondary']
        border_color = t['border']
        self.text_color = t['text_main']
        self.secondary_text_color = t['text_secondary']
        self.input_bg = t['input_bg']
        self.input_border = t['border']
        self.accent_color = t['accent']
        self.danger_color = t['danger']
        self.success_color = t['success']
        
        shadow_color = QColor(0, 0, 0, 100) if self._theme == "dark" else QColor(0, 0, 0, 30)
        
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            QLabel {{ color: {self.text_color}; }}
            QLineEdit {{
                background-color: {self.input_bg};
                color: {self.text_color};
                border: 1px solid {self.input_border};
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.accent_color};
            }}
            QComboBox {{
                background-color: {self.input_bg};
                color: {self.text_color};
                border: 1px solid {self.input_border};
                border-radius: 8px;
                padding: 8px;
            }}
            QSpinBox {{
                background-color: {self.input_bg};
                color: {self.text_color};
                border: 1px solid {self.input_border};
                border-radius: 8px;
                padding: 8px;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.1);
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        self.layout.addWidget(self.container)
        
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(25, 20, 25, 25)
        self.content_layout.setSpacing(20)
        
        # Header (Title + Window Actions)
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 5)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {self.text_color}; font-size: 20px; font-weight: bold;")
        self.header_layout.addWidget(title_lbl)
        self.header_layout.addStretch()
        
        # Window Action Buttons
        self.btn_maximize = QPushButton("▢")
        self.btn_maximize.setToolTip("Развернуть")
        self.btn_maximize.setFixedSize(30, 30)
        self.btn_maximize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_maximize.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.secondary_text_color};
                font-size: 16px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.1);
                color: white;
            }}
        """)
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        self.header_layout.addWidget(self.btn_maximize)
        
        self.btn_close_top = QPushButton("✕")
        self.btn_close_top.setToolTip("Закрыть")
        self.btn_close_top.setFixedSize(30, 30)
        self.btn_close_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_top.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.secondary_text_color};
                font-size: 16px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {self.danger_color};
                color: white;
            }}
        """)
        self.btn_close_top.clicked.connect(self.reject)
        self.header_layout.addWidget(self.btn_close_top)
        
        self.content_layout.addLayout(self.header_layout)

    def toggle_maximize(self):
        screen = QApplication.primaryScreen()
        if not screen: return
        
        available_geo = screen.availableGeometry()
        
        if not self._is_maximized:
            # Maximize
            self._normal_geometry = self.geometry()
            self.setGeometry(available_geo)
            self.btn_maximize.setText("❐")
            self.btn_maximize.setToolTip("Восстановить")
            self._is_maximized = True
            self.set_resizable(False)
            self.container.setStyleSheet(self.container.styleSheet().replace("border-radius: 12px;", "border-radius: 0px;"))
        else:
            # Restore
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            else:
                # Fallback if no geometry saved
                w, h = 800, 600
                self.setGeometry(
                    available_geo.x() + (available_geo.width() - w) // 2,
                    available_geo.y() + (available_geo.height() - h) // 2,
                    w, h
                )
            self.btn_maximize.setText("▢")
            self.btn_maximize.setToolTip("Развернуть")
            self._is_maximized = False
            self.set_resizable(True)
            self.container.setStyleSheet(self.container.styleSheet().replace("border-radius: 0px;", "border-radius: 12px;"))

    def showEvent(self, event):
        # Animate container appearance
        AnimationManager.fade_in(self.container)
        
        # Center the dialog on screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
                
        super().showEvent(event)

    def closeEvent(self, event):
        # We can't easily animate close because close() destroys the widget immediately
        # usually. But for dialogs we can reimplement reject/accept.
        super().closeEvent(event)
        
    def create_button(self, text, role="primary", clicked_slot=None):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(40)
        
        bg = self.accent_color if role == "primary" else \
             self.danger_color if role == "danger" else \
             self.success_color if role == "success" else "transparent"
             
        text_col = "white" if role in ["primary", "danger", "success"] else self.text_color
        border = f"1px solid {self.input_border}" if role == "secondary" else "none"
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_col};
                border: {border};
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        
        if clicked_slot:
            btn.clicked.connect(clicked_slot)
            
        return btn


class ConfirmationDialog(StyledDialogBase):
    def __init__(self, parent, title, message, yes_text="Да", no_text="Нет"):
        super().__init__(parent, title)
        
        # Theme colors
        t = StyleManager.get_theme(self._theme)
        border_color = t['border']
        
        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f"color: {self.secondary_text_color}; font-size: 14px;")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setWordWrap(True)
        self.content_layout.addWidget(msg_lbl)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_yes = QPushButton(yes_text)
        self.btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_yes.setFixedHeight(35)
        self.btn_yes.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['danger']};
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        self.btn_yes.clicked.connect(self.accept)
        
        self.btn_no = QPushButton(no_text)
        self.btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_no.setFixedHeight(35)
        self.btn_no.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['text_secondary']};
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        self.btn_no.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_no)
        btn_layout.addWidget(self.btn_yes)
        
        self.content_layout.addLayout(btn_layout)

class AlertDialog(StyledDialogBase):
    def __init__(self, parent, title, message, btn_text="OK"):
        super().__init__(parent, title)
        
        # Theme colors
        t = StyleManager.get_theme(self._theme)
        
        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f"color: {self.secondary_text_color}; font-size: 14px;")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setWordWrap(True)
        self.content_layout.addWidget(msg_lbl)
        
        btn_layout = QHBoxLayout()
        
        self.btn_ok = QPushButton(btn_text)
        self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ok.setFixedHeight(35)
        self.btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['accent']};
                border: 1px solid {t['accent']};
                border-radius: 5px;
                font-weight: bold;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {t['accent']}1A;
            }}
        """)
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addStretch()
        
        self.content_layout.addLayout(btn_layout)

class InputDialog(StyledDialogBase):
    def __init__(self, parent, title, message, default_value=""):
        super().__init__(parent, title)
        
        # Theme colors
        t = StyleManager.get_theme(self._theme)
        border_color = t['border']
        
        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f"color: {t['text_secondary']}; font-size: 14px;")
        self.content_layout.addWidget(msg_lbl)
        
        self.input = QLineEdit(str(default_value))
        self.input.setValidator(QDoubleValidator(0.0, 999999999.0, 2))
        self.content_layout.addWidget(self.input)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_ok = QPushButton("OK")
        self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ok.setFixedHeight(35)
        self.btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['success']};
                border: 1px solid {t['success']};
                border-radius: 5px;
                font-weight: bold;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {t['success']}1A;
            }}
        """)
        self.btn_ok.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(35)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.text_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                font-weight: bold;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                border-color: {t['accent']};
                color: {t['accent']};
            }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        
        self.content_layout.addLayout(btn_layout)
        
    @staticmethod
    def get_text(parent, title, message, default_value=""):
        dlg = InputDialog(parent, title, message, default_value)
        # Remove DoubleValidator for text input
        dlg.input.setValidator(None)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.input.text(), True
        return "", False

    def get_value(self):
        try:
            return float(self.input.text().replace(",", "."))
        except ValueError:
            return None

class TaskSelectionDialog(StyledDialogBase):
    def __init__(self, parent, tasks=None):
        super().__init__(parent, "Выберите задания")
        
        if tasks is None:
            tasks = ["Задание 1", "Задание 2", "Задание 3", "Задание 4", "Задание 5"]
            
        t = StyleManager.get_theme(self._theme)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.addItems(tasks)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {t['input_bg']};
                color: {t['text_main']};
                border: 1px solid {t['border']};
                border-radius: 5px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 5px;
            }}
            QListWidget::item:selected {{
                background-color: {t['accent']}40;
                color: {t['accent']};
                border: 1px solid {t['accent']};
                border-radius: 3px;
            }}
        """)
        self.content_layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_select = QPushButton("Выбрать")
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.setFixedHeight(35)
        self.btn_select.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['accent']};
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        self.btn_select.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(35)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['text_main']};
                border: 1px solid {t['border']};
                border-radius: 5px;
                font-weight: bold;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                border-color: {t['accent']};
                color: {t['accent']};
            }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_select)
        
        self.content_layout.addLayout(btn_layout)
        
    def get_selected_tasks(self):
        return [item.text() for item in self.list_widget.selectedItems()]

class UpdateProgressDialog(StyledDialogBase):
    def __init__(self, parent):
        super().__init__(parent, "Новое обновление", width=450)
        
        # Make dialog larger for better error display
        self.resize(450, 300)
        
        t = StyleManager.get_theme(self._theme)
        
        self.status_label = QLabel("Подготовка к загрузке...")
        self.status_label.setStyleSheet(f"color: {t['text_main']}; font-size: 14px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)  # Enable word wrap for long error messages
        self.status_label.setMinimumHeight(60)
        self.content_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {t['border']};
                border-radius: 5px;
                background-color: {t['input_bg']};
                text-align: center;
                color: {t['text_main']};
            }}
            QProgressBar::chunk {{
                background-color: {t['accent']};
                border-radius: 4px;
            }}
        """)
        self.content_layout.addWidget(self.progress_bar)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(30)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['text_secondary']};
                border: 1px solid {t['border']};
                border-radius: 5px;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                color: {t['text_main']};
                border-color: {t['text_main']};
            }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        self.content_layout.addLayout(btn_layout)
        
        # Store full error message
        self._full_error = None

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        if value < 100:
            self.status_label.setText(f"Загрузка обновления: {value}%")
        else:
            self.status_label.setText("Загрузка завершена")

    def set_status(self, text):
        self.status_label.setText(text)
        if "Перезапуск" in text or "Установка" in text:
             self.progress_bar.setValue(100)
             self.btn_cancel.setVisible(False)
        elif "Откат" in text or "Восстановление" in text:
             t = StyleManager.get_theme(self._theme)
             self.status_label.setStyleSheet(f"color: {t['warning']}; font-size: 14px;")
             self.progress_bar.setVisible(False)
        elif "Прервано" in text:
             t = StyleManager.get_theme(self._theme)
             self.status_label.setStyleSheet(f"color: {t['warning']}; font-size: 14px;")
             self.btn_cancel.setText("Закрыть")

    def update_progress(self, value):
        self.set_progress(value)

    def on_error(self, message):
        import tempfile
        import datetime
        import os
        import logging
        
        # Store full error
        self._full_error = message
        
        # Write detailed error to log file
        try:
            from version import VERSION
            temp_dir = tempfile.gettempdir()
            log_file = os.path.join(temp_dir, f'MoneyTracker_error_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"MoneyTracker Error Log\n")
                f.write(f"Time: {datetime.datetime.now().isoformat()}\n")
                f.write(f"Version: {VERSION}\n")
                f.write(f"{'='*50}\n\n")
                f.write(f"Full Error Message:\n{message}\n")
                f.write(f"{'='*50}\n")
            logging.info(f"Error log written to: {log_file}")
        except Exception as e:
            logging.warning(f"Failed to write error log: {e}")
        
        # Format the message nicely
        formatted_msg = self._format_error(message)
        
        # Create detailed tooltip
        tooltip = f"Полная ошибка:\n{message}\n\nЛог: {log_file if 'log_file' in dir() else 'Не удалось сохранить'}"
        
        self.status_label.setText(formatted_msg)
        self.status_label.setToolTip(tooltip)
        t = StyleManager.get_theme(self._theme)
        self.status_label.setStyleSheet(f"color: {t['danger']}; font-size: 13px;")
        self.btn_cancel.setText("Закрыть")
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(False)
        
        # Print to console for debugging
        logging.error(f"Update error: {message}")
    
    def _format_error(self, msg):
        """Format error message for display"""
        # Split long messages into multiple lines
        max_width = 60  # characters per line
        lines = []
        current_line = ""
        
        for word in msg.split():
            if len(current_line) + len(word) + 1 <= max_width:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return "\n".join(lines) if len(lines) > 1 else msg

    def on_interrupted(self, reason="Загрузка прервана"):
        self.set_status(f"Прервано: {reason}")
        self.progress_bar.setVisible(False)
        self.btn_cancel.setText("Закрыть")

    def on_finished(self, path):
        self.set_status("Обновление загружено. Перезапуск...")
        self.progress_bar.setValue(100)
        self.btn_cancel.setVisible(False)
        
        # Trigger restart after a short delay
        from PyQt6.QtCore import QTimer
        if hasattr(self.parent(), 'update_manager'):
            QTimer.singleShot(1500, lambda: self.parent().update_manager.restart_application(path))

class UpdateConfirmDialog(StyledDialogBase):
    def __init__(self, parent, version_info):
        super().__init__(parent, "Новое обновление")
        
        t = StyleManager.get_theme(self._theme)
        
        # Handle version_info being a dict or string
        if isinstance(version_info, dict):
            version_str = version_info.get('version', 'Unknown')
            notes = version_info.get('notes', '')
        else:
            version_str = str(version_info)
            notes = ""
            
        text = f"Доступна новая версия: {version_str}\n"
        if notes:
            text += f"\n{notes}\n"
        text += "\nХотите обновить сейчас?"
        
        msg = QLabel(text)
        msg.setStyleSheet(f"color: {t['text_main']}; font-size: 14px;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True) # Ensure long notes wrap
        self.content_layout.addWidget(msg)
        
        btn_layout = QHBoxLayout()
        
        self.btn_yes = QPushButton("Обновить")
        self.btn_yes.setStyleSheet(f"background-color: {t['accent']}; color: white; padding: 8px 15px; border-radius: 5px;")
        self.btn_yes.clicked.connect(self.accept)
        
        self.btn_no = QPushButton("Позже")
        self.btn_no.setStyleSheet(f"background-color: transparent; color: {t['text_main']}; border: 1px solid {t['border']}; padding: 8px 15px; border-radius: 5px;")
        self.btn_no.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_no)
        btn_layout.addWidget(self.btn_yes)
        self.content_layout.addLayout(btn_layout)

class RestoreProfileDialog(StyledDialogBase):
    def __init__(self, parent, data_manager):
        super().__init__(parent, "Восстановление профиля", width=500)
        self.data_manager = data_manager
        
        t = StyleManager.get_theme(self._theme)
        
        # Instructions
        info_lbl = QLabel("Выберите файл резервной копии (.zip или .json) для восстановления.\n"
                          "Данные будут объединены с текущими. Существующие записи не будут перезаписаны.")
        info_lbl.setStyleSheet(f"color: {t['text_main']}; font-size: 14px;")
        info_lbl.setWordWrap(True)
        self.content_layout.addWidget(info_lbl)
        
        # File Selection
        file_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Путь к файлу резервной копии...")
        self.path_input.setStyleSheet(f"padding: 8px; border: 1px solid {t['border']}; border-radius: 5px; color: {t['text_main']}; background: {t['input_bg']};")
        
        self.btn_browse = QPushButton("Обзор...")
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.setStyleSheet(f"background-color: {t['bg_tertiary']}; color: {t['text_main']}; padding: 8px 15px; border-radius: 5px; border: none;")
        self.btn_browse.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.path_input)
        file_layout.addWidget(self.btn_browse)
        self.content_layout.addLayout(file_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {t['border']};
                border-radius: 5px;
                background-color: {t['input_bg']};
                text-align: center;
                color: {t['text_main']};
            }}
            QProgressBar::chunk {{
                background-color: {t['accent']};
                border-radius: 4px;
            }}
        """)
        self.content_layout.addWidget(self.progress_bar)
        
        # Log Area
        self.log_area = QLabel("")
        self.log_area.setWordWrap(True)
        self.log_area.setStyleSheet(f"color: {t['text_secondary']}; font-size: 12px; margin-top: 10px;")
        self.content_layout.addWidget(self.log_area)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = self.create_button("Отмена", "secondary", self.reject)
        self.btn_restore = self.create_button("Восстановить", "primary", self.start_restore)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_restore)
        self.content_layout.addLayout(btn_layout)

    def create_button(self, text, style_type, callback):
        t = StyleManager.get_theme(self._theme)
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        
        if style_type == "primary":
            bg = t['accent']
            color = "white"
            border = "none"
        else:
            bg = "transparent"
            color = t['text_main']
            border = f"1px solid {t['border']}"
            
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: {border};
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        return btn

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите резервную копию", "", "Backup Files (*.zip *.json)")
        if path:
            self.path_input.setText(path)

    def start_restore(self):
        path = self.path_input.text()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Ошибка", "Файл не выбран или не существует.")
            return
            
        self.btn_restore.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.path_input.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_area.setText("Анализ файла...")
        
        # Run in timer to allow UI update
        QTimer.singleShot(100, lambda: self.process_restore(path))

    def process_restore(self, path):
        try:
            data_to_import = {}
            
            if path.endswith('.zip'):
                with zipfile.ZipFile(path, 'r') as zf:
                    # Look for data.json first
                    target_file = None
                    if 'data.json' in zf.namelist():
                        target_file = 'data.json'
                    else:
                        # Find any json file
                        json_files = [n for n in zf.namelist() if n.endswith('.json')]
                        if json_files:
                            target_file = json_files[0]
                            
                    if target_file:
                        with zf.open(target_file) as f:
                            data_to_import = json.load(f)
                    else:
                        raise Exception("В архиве не найдено JSON файлов.")
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    data_to_import = json.load(f)
            
            self.progress_bar.setValue(30)
            self.log_area.setText("Импорт данных...")
            
            # Use DataManager to merge
            if hasattr(self.data_manager, 'import_profile_data'):
                count = self.data_manager.import_profile_data(data_to_import)
                self.progress_bar.setValue(100)
                self.log_area.setText(f"Успешно! Импортировано объектов: {count}")
                QMessageBox.information(self, "Успех", f"Восстановление завершено.\nДобавлено/обновлено записей: {count}")
                self.accept()
            else:
                raise Exception("DataManager does not support import_profile_data")
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.btn_restore.setEnabled(True)
            self.btn_browse.setEnabled(True)
            self.path_input.setEnabled(True)
            self.log_area.setText(f"Ошибка: {str(e)}")
            QMessageBox.critical(self, "Ошибка восстановления", str(e))

class CleanupProgressDialog(StyledDialogBase):
    def __init__(self, parent, title="Очистка системы"):
        super().__init__(parent, title, width=500)
        self.setMinimumHeight(350)
        
        t = StyleManager.get_theme(self._theme)
        
        self.status_label = QLabel("Подготовка к очистке...")
        self.status_label.setStyleSheet(f"color: {t['text_main']}; font-size: 14px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {t['border']};
                border-radius: 8px;
                background-color: {t['input_bg']};
                text-align: center;
                color: {t['text_main']};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {t['accent']};
                border-radius: 7px;
            }}
        """)
        self.content_layout.addWidget(self.progress_bar)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['input_bg']};
                color: {t['text_secondary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 10px;
            }}
        """)
        self.content_layout.addWidget(self.log_area if hasattr(self, 'log_area') else self.log_view)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(35)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['text_secondary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                color: {t['danger']};
                border-color: {t['danger']};
            }}
        """)
        self.btn_cancel.clicked.connect(self.request_cancel)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        self.content_layout.addLayout(btn_layout)
        
        self._is_cancelled = False

    def request_cancel(self):
        self._is_cancelled = True
        self.status_label.setText("Отмена операции...")
        self.btn_cancel.setEnabled(False)

    def is_cancelled(self):
        return self._is_cancelled

    def append_log(self, text):
        if hasattr(self, 'log_view'):
            self.log_view.append(text)
            self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def set_progress(self, value):
        self.progress_bar.setValue(value)

    def set_status(self, text):
        self.status_label.setText(text)

    def on_finished(self, summary):
        self.status_label.setText("Очистка завершена")
        self.btn_cancel.setText("Закрыть")
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.clicked.disconnect()
        self.btn_cancel.clicked.connect(self.accept)
        
        if summary:
            self.append_log("\n" + "="*40)
            self.append_log(summary)
            self.append_log("="*40)
