from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
    QFrame, QLineEdit, QApplication, QGraphicsDropShadowEffect,
    QListWidget, QAbstractItemView, QProgressBar, QWidget, QSizeGrip,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect, QTimer
from PyQt6.QtGui import QColor, QDoubleValidator, QCursor
import os
import json
import zipfile

from gui.styles import StyleManager

class ResizeMixin:
    def setup_resizing(self):
        self._resizing = False
        self._resize_edge = None
        self._resize_margin = 10
        self.setMouseTracking(True)
        # Size Grip for bottom-right corner
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background: transparent;")
        self.size_grip.resize(20, 20)
        
    def resizeEvent(self, event):
        if hasattr(self, 'size_grip'):
            self.size_grip.move(self.width() - 20, self.height() - 20)
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._drag_pos = event.globalPosition().toPoint()
                event.accept()
                return
            else:
                # Start moving logic if not resizing
                self._moving = True
                self._drag_pos = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            self._handle_resize(event.globalPosition().toPoint())
            event.accept()
        elif hasattr(self, '_moving') and self._moving:
             # Handle moving
             diff = event.globalPosition().toPoint() - self._drag_pos
             self.move(self.pos() + diff)
             self._drag_pos = event.globalPosition().toPoint()
             event.accept()
        else:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._update_cursor(edge)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._resizing = False
            self._moving = False # Reset moving
            self._resize_edge = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

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
        self._drag_pos = global_pos
        
        geo = self.geometry()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        
        if self._resize_edge & 1: # Left
            x += diff.x()
            w -= diff.x()
        if self._resize_edge & 2: # Right
            w += diff.x()
        if self._resize_edge & 4: # Top
            y += diff.y()
            h -= diff.y()
        if self._resize_edge & 8: # Bottom
            h += diff.y()
            
        if w >= self.minimumWidth() and h >= self.minimumHeight():
            self.setGeometry(x, y, w, h)

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
        self.layout.setContentsMargins(10, 10, 10, 10)
        
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
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(shadow_color)
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
        self.layout.addWidget(self.container)
        
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(25, 25, 25, 25)
        self.content_layout.setSpacing(20)
        
        # Header (Title + Close Button)
        header_layout = QHBoxLayout()
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {self.text_color}; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        
        # Optional: Add close button X in top right if needed, but usually actions are at bottom
        
        self.content_layout.addLayout(header_layout)

        # Animation Setup
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(250)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def showEvent(self, event):
        self.setWindowOpacity(0)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(1)
        self.opacity_anim.start()
        
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
        super().__init__(parent, "Новое обновление")
        
        t = StyleManager.get_theme(self._theme)
        
        self.status_label = QLabel("Подготовка к загрузке...")
        self.status_label.setStyleSheet(f"color: {t['text_main']}; font-size: 14px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)  # Enable word wrap for long error messages
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
        self.status_label.setText(f"Ошибка: {message}")
        t = StyleManager.get_theme(self._theme)
        self.status_label.setStyleSheet(f"color: {t['danger']}; font-size: 14px;")
        self.btn_cancel.setText("Закрыть")
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(False)

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
