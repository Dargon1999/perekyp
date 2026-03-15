from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QDialog, QLineEdit, QComboBox, 
    QSpinBox, QProgressBar, QGridLayout, QMessageBox, QApplication, QStyle,
    QSystemTrayIcon, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, QRectF, QPointF, QRegularExpression, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QIcon, QFont, QPixmap, QPainter, QBrush, QColor, QPainterPath, QPolygonF, QRegularExpressionValidator, QKeySequence, QShortcut
from datetime import datetime, timedelta
import math
import logging
import os

from gui.styles import StyleManager
from gui.custom_dialogs import AlertDialog, ConfirmationDialog, StyledDialogBase
from utils import resource_path

logger = logging.getLogger(__name__)

class Switch(QCheckBox):
    def __init__(self, parent=None, active_color="#3498db", bg_color="#444"):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active_color = active_color
        self._bg_color = bg_color
        self.setMinimumSize(50, 26)
        self.setFixedHeight(26)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        
        # Draw background pill
        rect = QRectF(0, 0, 50, 26)
        if self.isChecked():
            p.setBrush(QColor(self._active_color))
        else:
            p.setBrush(QColor(self._bg_color))
        p.drawRoundedRect(rect, 13, 13)
        
        # Draw knob (circle)
        p.setBrush(QColor("#ffffff"))
        knob_pos = 26 if self.isChecked() else 2
        p.drawEllipse(knob_pos, 2, 22, 22)
        p.end()

class OptionRow(QFrame):
    def __init__(self, text, tooltip, is_checked, accent_color, input_bg, input_border, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {input_bg};
                border-radius: 12px;
                border: 1px solid {input_border};
            }}
            QFrame:hover {{
                border: 1px solid {accent_color};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        self.label = QLabel(text)
        self.label.setStyleSheet("border: none; font-size: 14px; background: transparent;")
        
        self.switch = Switch(active_color=accent_color, bg_color="#444")
        self.switch.setChecked(is_checked)
        self.switch.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # Let Row handle clicks
        
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.switch)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.switch.setChecked(not self.switch.isChecked())
            event.accept()
        else:
            super().mousePressEvent(event)

    def isChecked(self):
        return self.switch.isChecked()

class TimerSettingsDialog(StyledDialogBase):
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, "Настройки таймера", width=500)
        self.data_manager = data_manager
        
        # Explicitly set size to avoid squashing in StyledDialogBase
        self.setMinimumHeight(550)
        self.resize(500, 550)
        
        # Load theme colors
        self.theme = StyledDialogBase._theme
        t = StyleManager.get_theme(self.theme)
        self.bg_color = t['bg_secondary']
        self.text_color = t['text_main']
        self.secondary_text_color = t['text_secondary']
        self.input_bg = t['input_bg']
        self.input_border = t['border']
        self.accent_color = t['accent']
        self.success_color = t['success']
        self.danger_color = t['danger']
        
        # Audio setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Connect player signals for feedback
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.player.errorOccurred.connect(self.on_player_error)
        
        self.setup_settings_ui()
        
    def setup_settings_ui(self):
        # Clear any existing layout content if needed, but here it's fresh
        # Apply consistent padding and spacing
        self.content_layout.setSpacing(30) # Increased spacing between sections
        self.content_layout.setContentsMargins(30, 20, 30, 30)
        
        # --- Section 1: Sound ---
        sound_section = QVBoxLayout()
        sound_section.setSpacing(15)
        
        sound_label = QLabel("🎵 Звуковое уведомление:")
        sound_label.setStyleSheet(f"color: {self.text_color}; font-size: 14px; font-weight: bold;")
        sound_section.addWidget(sound_label)
        
        self.sound_combo = QComboBox()
        self.sound_combo.setMinimumHeight(45) # Use minimum instead of fixed
        self.sound_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.input_bg};
                color: {self.text_color};
                border: 1px solid {self.input_border};
                border-radius: 10px;
                padding: 0 15px;
                font-size: 14px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 40px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.bg_color};
                color: {self.text_color};
                selection-background-color: {self.accent_color};
                border: 1px solid {self.input_border};
                outline: none;
                padding: 8px;
            }}
        """)
        
        self.sounds = [
            ("Стандартный", "beep.wav"),
            ("Колокольчик", "bell.wav"),
            ("Цифровой", "digital.wav"),
            ("Сирена", "siren.wav"),
            ("Электронный", "electronic.wav"),
            ("Мягкий", "soft.wav"),
            ("Внимание", "alert.wav")
        ]
        
        for name, _ in self.sounds:
            self.sound_combo.addItem(name)
            
        current_sound = self.data_manager.get_setting("timer_sound", "beep.wav")
        for i, (name, file) in enumerate(self.sounds):
            if file == current_sound:
                self.sound_combo.setCurrentIndex(i)
                break
                
        sound_section.addWidget(self.sound_combo)
        
        # Preview button
        self.preview_btn = self.create_button("▶ Прослушать выбранный звук", "primary", self.preview_sound)
        self.preview_btn.setFixedHeight(50)
        self.preview_btn.setStyleSheet(self.preview_btn.styleSheet() + "font-size: 14px; font-weight: bold; border-radius: 10px;")
        sound_section.addWidget(self.preview_btn)
        
        self.content_layout.addLayout(sound_section)
        
        # --- Section 2: Window Options ---
        options_section = QVBoxLayout()
        options_section.setSpacing(15)
        
        options_label = QLabel("🖥️ Параметры окна:")
        options_label.setStyleSheet(f"color: {self.text_color}; font-size: 14px; font-weight: bold;")
        options_section.addWidget(options_label)
        
        is_topmost = self.data_manager.get_setting("timer_topmost", False)
        self.topmost_row = OptionRow(
            "Показать поверх всех окон",
            "При срабатывании таймера окно уведомления будет поверх всех окон и свернет остальные",
            is_topmost,
            self.accent_color, self.input_bg, self.input_border, self
        )
        options_section.addWidget(self.topmost_row)
        
        is_loop = self.data_manager.get_setting("timer_loop", False)
        self.loop_row = OptionRow(
            "Зациклить звук (повторять)",
            "Звук будет повторяться до тех пор, пока вы не нажмете ОК или закроете уведомление",
            is_loop,
            self.accent_color, self.input_bg, self.input_border, self
        )
        options_section.addWidget(self.loop_row)
        
        self.content_layout.addLayout(options_section)
        
        self.content_layout.addStretch()
        
        # --- Footer: Actions ---
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(15)
        
        save_btn = self.create_button("💾 Сохранить", "success", self.save_settings)
        save_btn.setFixedHeight(50)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.success_color};
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: #27ae60;
                margin-top: -2px;
            }}
            QPushButton:pressed {{
                margin-top: 1px;
            }}
        """)
        
        cancel_btn = self.create_button("❌ Отмена", "danger", self.reject)
        cancel_btn.setFixedHeight(50)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.danger_color};
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
                margin-top: -2px;
            }}
            QPushButton:pressed {{
                margin-top: 1px;
            }}
        """)
        
        footer_layout.addWidget(save_btn)
        footer_layout.addWidget(cancel_btn)
        self.content_layout.addLayout(footer_layout)

    def preview_sound(self):
        index = self.sound_combo.currentIndex()
        if index >= 0:
            sound_file = self.sounds[index][1]
            sound_path = resource_path(os.path.join("assets", "sounds", sound_file))
            
            logger.info(f"Attempting to preview sound: {sound_path}")
            
            if os.path.exists(sound_path):
                try:
                    self.player.setSource(QUrl.fromLocalFile(sound_path))
                    self.audio_output.setVolume(1.0)
                    self.player.play()
                    self.preview_btn.setText("⏳ Воспроизведение...")
                    self.preview_btn.setEnabled(False)
                except Exception as e:
                    logger.error(f"Error during playback: {e}")
                    self.preview_btn.setText("❌ Ошибка воспроизведения")
                    QTimer.singleShot(2000, lambda: self.reset_preview_button())
            else:
                logger.error(f"Sound file not found: {sound_path}")
                self.preview_btn.setText("❌ Файл не найден")
                QApplication.beep()
                QTimer.singleShot(2000, lambda: self.reset_preview_button())

    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.reset_preview_button()

    def on_player_error(self, error, error_str):
        logger.error(f"MediaPlayer Error: {error_str} (Code: {error})")
        self.preview_btn.setText(f"❌ Ошибка: {error}")
        QTimer.singleShot(3000, lambda: self.reset_preview_button())

    def reset_preview_button(self):
        self.preview_btn.setText("▶ Прослушать выбранный звук")
        self.preview_btn.setEnabled(True)

    def save_settings(self):
        index = self.sound_combo.currentIndex()
        if index >= 0:
            self.data_manager.set_setting("timer_sound", self.sounds[index][1])
            
        self.data_manager.set_setting("timer_topmost", self.topmost_row.isChecked())
        self.data_manager.set_setting("timer_loop", self.loop_row.isChecked())
        self.accept()

class FullscreenNotification(QDialog):
    def __init__(self, timer_name, sound_path=None, loop_sound=False):
        super().__init__()
        self.timer_name = timer_name
        self.sound_path = sound_path
        self.loop_sound = loop_sound
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Fullscreen
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Dark overlay
        overlay = QFrame()
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        layout.addWidget(overlay)
        
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(50, 50, 50, 50)
        overlay_layout.setSpacing(30)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        icon_lbl = QLabel("⏰")
        icon_lbl.setStyleSheet("font-size: 120px; color: #f1c40f;")
        overlay_layout.addWidget(icon_lbl)
        
        # Title
        title_lbl = QLabel("ТАЙМЕР ЗАВЕРШЕН!")
        title_lbl.setStyleSheet("font-size: 48px; font-weight: bold; color: #e74c3c;")
        overlay_layout.addWidget(title_lbl)
        
        # Message
        msg_lbl = QLabel(f"Таймер «{timer_name}» истек!")
        msg_lbl.setStyleSheet("font-size: 32px; color: white;")
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(msg_lbl)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        
        ok_btn = QPushButton("ОК")
        ok_btn.setFixedSize(200, 60)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        ok_btn.clicked.connect(self.accept)
        
        snooze_btn = QPushButton("Отложить (5 мин)")
        snooze_btn.setFixedSize(300, 60)
        snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        snooze_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        snooze_btn.clicked.connect(self.snooze)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(snooze_btn)
        overlay_layout.addLayout(btn_layout)
        
        # ESC Shortcut
        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.esc_shortcut.activated.connect(self.reject)
        
        # Sound player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        if self.sound_path and os.path.exists(self.sound_path):
            self.player.setSource(QUrl.fromLocalFile(self.sound_path))
            self.audio_output.setVolume(1.0)
            if self.loop_sound:
                self.player.setLoops(QMediaPlayer.Loops.Infinite)
            else:
                self.player.setLoops(QMediaPlayer.Loops.Once)
            self.player.play()
        else:
            QApplication.beep()

    def snooze(self):
        self.done(10) # Custom code for snooze

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)

    def accept(self):
        self.player.stop()
        super().accept()

    def reject(self):
        self.player.stop()
        super().reject()


class AddTimerDialog(StyledDialogBase):
    def __init__(self, parent=None, timer_data=None):
        self.timer_data = timer_data
        title = "Редактирование таймера" if timer_data else "Создание таймера"
        super().__init__(parent, title, width=450)
        
        self.content_layout.setSpacing(15)
        
        # Name
        self.content_layout.addWidget(QLabel("Название таймера:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Оставьте пустым для авто-названия")
        self.name_input.setMaxLength(100) # Increased to 100
        self.name_input.setAccessibleName("Название таймера")
        self.name_input.setAccessibleDescription("Введите название таймера (до 100 символов)")
        
        # Validation: Allow all languages, but prevent XSS by escaping later
        # We allow almost anything but limit length and escape during save
        self.content_layout.addWidget(self.name_input)
        
        # Type
        self.content_layout.addWidget(QLabel("Тип таймера:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Аренда Транспорта", "Аренда Дома", "Контракт", "Другое"])
        self.type_combo.setAccessibleName("Тип таймера")
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        self.content_layout.addWidget(self.type_combo)
        
        # Time Inputs
        self.time_group = QFrame()
        self.time_group.setStyleSheet(f"background-color: {self.input_bg}; border-radius: 8px; border: 1px solid {self.input_border}; padding: 10px;")
        self.time_layout = QGridLayout(self.time_group)
        
        self.days_spin = QSpinBox()
        self.days_spin.setRange(0, 99999)
        self.days_spin.setSuffix(" дн.")
        
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 23)
        self.hours_spin.setSuffix(" ч.")
        
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setSuffix(" мин.")
        
        self.days_lbl = QLabel("Дни:")
        self.hours_lbl = QLabel("Часы:")
        self.minutes_lbl = QLabel("Минуты:")
        
        self.time_layout.addWidget(self.days_lbl, 0, 0)
        self.time_layout.addWidget(self.days_spin, 0, 1)
        self.time_layout.addWidget(self.hours_lbl, 1, 0)
        self.time_layout.addWidget(self.hours_spin, 1, 1)
        self.time_layout.addWidget(self.minutes_lbl, 2, 0)
        self.time_layout.addWidget(self.minutes_spin, 2, 1)
        
        self.content_layout.addWidget(QLabel("Длительность:"))
        self.content_layout.addWidget(self.time_group)
        
        # Info Label based on type
        self.info_lbl = QLabel("Введите время вручную.")
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setStyleSheet(f"color: {self.secondary_text_color}; font-size: 12px;")
        self.content_layout.addWidget(self.info_lbl)
        
        # Pre-fill if editing
        if self.timer_data:
            self.name_input.setText(self.timer_data.get("name", ""))
            self.type_combo.setCurrentText(self.timer_data.get("type", "Другое"))
            
            total_seconds = self.timer_data.get("duration", 0)
            td = timedelta(seconds=int(total_seconds))
            self.days_spin.setValue(td.days)
            hours, remainder = divmod(td.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            self.hours_spin.setValue(hours)
            self.minutes_spin.setValue(minutes)
        
        # Initial state update
        self.on_type_changed(self.type_combo.currentText())
        
        self.content_layout.addStretch()
        
        # Buttons
        self.add_button_box_custom()

    def add_button_box_custom(self):
        btn_layout = QHBoxLayout()
        btn_text = "Сохранить" if self.timer_data else "Создать"
        save_btn = self.create_button(btn_text, "success", self.validate_and_accept)
        cancel_btn = self.create_button("Отмена", "danger", self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        self.content_layout.addLayout(btn_layout)

    def on_type_changed(self, text):
        # Reset spins
        self.days_spin.setValue(0)
        self.hours_spin.setValue(0)
        self.minutes_spin.setValue(0)
        
        # Ensure all are visible first to reset layout state
        for w in [self.days_lbl, self.days_spin, self.hours_lbl, self.hours_spin, self.minutes_lbl, self.minutes_spin]:
            w.setVisible(True)
        
        # Set placeholder text and behavior based on type
        if text == "Аренда Транспорта":
            self.hours_spin.setValue(1)
            self.info_lbl.setText("Для аренды транспорта время указывается в часах.")
            # Show only Hours
            self.days_lbl.setVisible(False)
            self.days_spin.setVisible(False)
            self.minutes_lbl.setVisible(False)
            self.minutes_spin.setVisible(False)
            if not self.name_input.text():
                self.name_input.setPlaceholderText("Например: Транспорт #1")
            
        elif text == "Аренда Дома":
            self.days_spin.setValue(1)
            self.info_lbl.setText("Для аренды дома время указывается в днях.")
            # Show only Days
            self.hours_lbl.setVisible(False)
            self.hours_spin.setVisible(False)
            self.minutes_lbl.setVisible(False)
            self.minutes_spin.setVisible(False)
            if not self.name_input.text():
                self.name_input.setPlaceholderText("Например: Дом #55")
            
        elif text == "Контракт":
            self.hours_spin.setValue(1)
            self.info_lbl.setText("Для контрактов время указывается в часах и минутах.")
            # Show Hours and Minutes (Hide Days)
            self.days_lbl.setVisible(False)
            self.days_spin.setVisible(False)
            if not self.name_input.text():
                self.name_input.setPlaceholderText("Например: Контракт на рыбу")
            
        else: # Другое
            self.info_lbl.setText("Укажите любое время (Дни, Часы, Минуты).")
            # Show All (Already visible due to reset)
            if not self.name_input.text():
                self.name_input.setPlaceholderText("Название таймера")
        
        # Force layout update and resize to fit content
        self.time_layout.activate()
        self.time_group.adjustSize()
        self.layout.activate()
        self.adjustSize()

    def showEvent(self, event):
        super().showEvent(event)
        # Ensure layout is correct after showing
        self.on_type_changed(self.type_combo.currentText())
        self.adjustSize()

    def validate_and_accept(self):
        total_seconds = (self.days_spin.value() * 86400) + \
                        (self.hours_spin.value() * 3600) + \
                        (self.minutes_spin.value() * 60)
                        
        if total_seconds <= 0:
            AlertDialog(self, "Ошибка", "Укажите время больше 0").exec()
            return
            
        self.accept()

    def get_data(self):
        total_seconds = (self.days_spin.value() * 86400) + \
                        (self.hours_spin.value() * 3600) + \
                        (self.minutes_spin.value() * 60)
        
        # Name logic
        raw_name = self.name_input.text().strip()
        timer_type = self.type_combo.currentText()
        
        if raw_name:
            # Escape HTML characters to prevent basic XSS when rendering in labels
            name = raw_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")
        else:
            # Contextual default names
            name = timer_type
            
        return name, timer_type, total_seconds


class TimerCard(QFrame):
    def __init__(self, timer_data, parent_tab):
        super().__init__()
        self.timer_data = timer_data
        self.parent_tab = parent_tab
        self.setup_ui()
        self.update_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 10px;
                border: 1px solid #444;
            }
            QLabel { color: white; border: none; background: transparent; }
        """)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(140)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        # 1. Icon & Type
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        self.icon_lbl = QLabel("⏱️")
        self.icon_lbl.setStyleSheet("font-size: 32px;")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.type_lbl = QLabel(self.timer_data["type"])
        self.type_lbl.setStyleSheet("color: #bdc3c7; font-size: 12px; font-weight: bold;")
        self.type_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Hide type label if it's the same as the name (to avoid duplication)
        if self.timer_data["name"] == self.timer_data["type"]:
            self.type_lbl.setVisible(False)
        
        info_layout.addWidget(self.icon_lbl)
        info_layout.addWidget(self.type_lbl)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # 2. Main Content (Name, Progress, Time)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)
        
        self.name_lbl = QLabel(self.timer_data["name"])
        self.name_lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        self.time_lbl = QLabel("Loading...")
        self.time_lbl.setStyleSheet("font-size: 24px; font-family: monospace; font-weight: bold; color: #f1c40f;")
        
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #2c3e50;
                border-radius: 20px;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 20px;
            }
        """)
        
        content_layout.addWidget(self.name_lbl)
        content_layout.addWidget(self.time_lbl)
        content_layout.addWidget(self.progress)
        layout.addLayout(content_layout, 1) # Stretch factor 1
        
        # 3. Actions
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_toggle = QPushButton()
        self.btn_toggle.setFixedSize(40, 40)
        self.btn_toggle.setToolTip("Пауза / Старт")
        self.btn_toggle.setStyleSheet("""
            QPushButton { 
                background-color: #e67e22; 
                border-radius: 20px; 
                border: none; 
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.btn_toggle.clicked.connect(self.toggle_timer)
        
        self.btn_edit = QPushButton()
        self.btn_edit.setFixedSize(40, 40)
        # self.btn_edit.setText("✎") 
        self.btn_edit.setIcon(self.create_edit_icon("white"))
        self.btn_edit.setIconSize(QSize(20, 20))
        self.btn_edit.setToolTip("Редактировать")
        self.btn_edit.setStyleSheet("""
            QPushButton { background-color: #3498db; border-radius: 20px; border: none; color: white; font-weight: bold; font-size: 18px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_edit.clicked.connect(self.edit_timer)
        
        self.btn_delete = QPushButton()
        self.btn_delete.setFixedSize(40, 40)
        self.btn_delete.setIconSize(QSize(20, 20))
        self.btn_delete.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.btn_delete.setToolTip("Удалить")
        self.btn_delete.setStyleSheet("""
            QPushButton { background-color: #c0392b; border-radius: 20px; border: none; }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.btn_delete.clicked.connect(self.delete_timer)
        
        actions_layout.addWidget(self.btn_toggle)
        actions_layout.addWidget(self.btn_edit)
        actions_layout.addWidget(self.btn_delete)
        layout.addLayout(actions_layout)

    def toggle_timer(self):
        is_running = self.timer_data["is_running"]
        action = "pause" if is_running else "resume"
        if self.parent_tab.data_manager.update_timer_status(self.timer_data["id"], action):
            self.timer_data["is_running"] = not is_running
            self.btn_toggle.setText("▶" if is_running else "||")
            self.parent_tab.refresh_data()

    def edit_timer(self):
        self.parent_tab.open_edit_timer_dialog(self.timer_data)

    def delete_timer(self):
        if ConfirmationDialog(self, "Удаление", f"Удалить таймер '{self.timer_data['name']}'?").exec():
            if self.parent_tab.data_manager.delete_timer(self.timer_data["id"]):
                self.parent_tab.refresh_data()

    def create_edit_icon(self, color, size=64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Save state
        painter.save()
        
        # Center and rotate (Pencil angle)
        painter.translate(size/2, size/2)
        painter.rotate(135) # Pointing down-right
        
        # Dimensions
        w = size * 0.25
        h = size * 0.45
        
        # Draw Body
        painter.drawRect(QRectF(-w/2, -h/2, w, h))
        
        # Draw Tip
        path = QPainterPath()
        path.moveTo(-w/2, h/2)
        path.lineTo(w/2, h/2)
        path.lineTo(0, h/2 + w) # Pointy end
        path.closeSubpath()
        painter.drawPath(path)
        
        # Draw Eraser/Cap
        cap_h = size * 0.1
        painter.setBrush(QBrush(QColor(color).lighter(150))) # Slightly different shade
        painter.drawRoundedRect(QRectF(-w/2, -h/2 - cap_h, w, cap_h), 2, 2)
        
        painter.restore()
        painter.end()
        return QIcon(pixmap)

    def create_pause_icon(self, color, size=64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw two vertical bars
        bar_w = size * 0.25
        bar_h = size * 0.6
        gap = size * 0.2
        
        x1 = (size - (2*bar_w + gap)) / 2
        y1 = (size - bar_h) / 2
        
        painter.drawRoundedRect(QRectF(x1, y1, bar_w, bar_h), 4, 4)
        painter.drawRoundedRect(QRectF(x1 + bar_w + gap, y1, bar_w, bar_h), 4, 4)
        painter.end()
        return QIcon(pixmap)

    def create_play_icon(self, color, size=64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw triangle
        # Center triangle
        h = size * 0.5
        w = size * 0.45
        
        x = (size - w) / 2 + (size * 0.05) # slight offset to look centered visually
        y = (size - h) / 2
        
        # Points: (x, y), (x, y+h), (x+w, y+h/2)
        polygon = QPolygonF([
            QPointF(x, y),
            QPointF(x, y + h),
            QPointF(x + w, y + h/2)
        ])
        painter.drawPolygon(polygon)
        painter.end()
        return QIcon(pixmap)

    def update_ui(self):
        # Calculate remaining time
        now = datetime.now().timestamp()
        
        if self.timer_data["is_running"]:
            remaining = self.timer_data["end_time"] - now
            self.btn_toggle.setText("")
            self.btn_toggle.setIcon(self.create_pause_icon("white"))
            self.btn_toggle.setIconSize(QSize(20, 20))
            self.btn_toggle.setToolTip("Пауза")
            self.btn_toggle.setStyleSheet("""
                QPushButton { 
                    background-color: #f1c40f; 
                    border-radius: 20px; 
                    border: none; 
                    color: white;
                    font-size: 16px; /* Added */
                    font-weight: bold; /* Added */
                } 
                QPushButton:hover { background-color: #f39c12; }
            """)
        else:
            remaining = self.timer_data.get("paused_remaining", 0)
            self.btn_toggle.setText("")
            self.btn_toggle.setIcon(self.create_play_icon("white"))
            self.btn_toggle.setIconSize(QSize(20, 20))
            self.btn_toggle.setToolTip("Возобновить")
            self.btn_toggle.setStyleSheet("""
                QPushButton { 
                    background-color: #2ecc71; 
                    border-radius: 20px; 
                    border: none; 
                    color: white;
                    font-size: 16px; /* Added */
                    font-weight: bold; /* Added */
                } 
                QPushButton:hover { background-color: #27ae60; }
            """)
            
        if remaining < 0: remaining = 0
        
        # Format string
        td = timedelta(seconds=int(remaining))
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        time_str = f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"
            
        if remaining <= 0 and self.timer_data["is_running"]:
            time_str = "ЗАВЕРШЕНО"
            self.time_lbl.setStyleSheet("color: #e74c3c; font-size: 24px; font-weight: bold;")
        elif not self.timer_data["is_running"]:
            time_str += " (Пауза)"
            self.time_lbl.setStyleSheet("color: #95a5a6; font-size: 24px; font-weight: bold;")
        else:
            self.time_lbl.setStyleSheet("color: #f1c40f; font-size: 24px; font-weight: bold;")
            
        self.time_lbl.setText(time_str)
        
        # Progress Bar
        total = self.timer_data["duration"]
        if total > 0:
            percent = int((remaining / total) * 100)
            self.progress.setValue(percent)
            
            # Color coding
            color = "#2ecc71" # Green > 50%
            if percent < 25: color = "#e74c3c" # Red
            elif percent < 50: color = "#f39c12" # Yellow
            
            self.progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #2c3e50;
                    border-radius: 5px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 5px;
                }}
            """)
        
        # Check for completion to trigger parent notification logic (handled in parent loop usually, but visual update is here)


class TimerCompleteDialog(StyledDialogBase):
    def __init__(self, parent, timer_name):
        super().__init__(parent, "Таймер завершен!", width=400)
        
        # Sound
        QApplication.beep()
        
        # Icon
        icon_lbl = QLabel("⏰")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 64px; margin: 10px;")
        self.content_layout.addWidget(icon_lbl)
        
        # Message
        msg = QLabel(f"Таймер «{timer_name}» истек!")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.text_color};")
        self.content_layout.addWidget(msg)
        
        # Button
        btn = self.create_button("Отлично", "success", self.accept)
        self.content_layout.addWidget(btn)

class TimersTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        self.timers = []
        self.timer_widgets = []
        self.notified_timers = set() # Store IDs of timers we already notified about
        
        self.setup_ui()
        
        # Process auto-delete before starting timer loop
        self.process_expired_contracts()
        
        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_tick)
        self.update_timer.start(1000) # 1 second
        
        self.is_initialized = False
        # self.refresh_data() # Deferred loading

    def showEvent(self, event):
        if not self.is_initialized:
            self.refresh_data()
            self.is_initialized = True
        super().showEvent(event)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_lbl = QLabel("🕒 Таймер")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        
        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setToolTip("Настройки уведомлений")
        
        # Draw a custom gear icon using QPainter
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Outer teeth
        painter.setBrush(QColor("#ffffff"))
        painter.translate(20, 20)
        for _ in range(8):
            painter.drawRoundedRect(-4, -16, 8, 32, 2, 2)
            painter.rotate(45)
            
        # Main body
        painter.drawEllipse(-11, -11, 22, 22)
        
        # Center hole (using transparent to see through if background changes)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.drawEllipse(-6, -6, 12, 12)
        painter.end()
        
        self.settings_btn.setIcon(QIcon(pixmap))
        self.settings_btn.setIconSize(QSize(24, 24))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b3b3b;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #555; }
        """)
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        
        add_btn = QPushButton("➕ Добавить таймер")
        add_btn.setFixedSize(220, 40)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        add_btn.clicked.connect(self.open_add_timer_dialog)
        
        # Filter
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "Аренда Транспорта", "Аренда Дома", "Контракт", "Другое"])
        self.filter_combo.setFixedWidth(180)
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #3b3b3b;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 5px;
            }
        """)
        self.filter_combo.currentTextChanged.connect(self.refresh_data)

        header_layout.addWidget(title_lbl)
        header_layout.addWidget(self.settings_btn)
        header_layout.addSpacing(10)
        header_layout.addWidget(add_btn)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Фильтр:"))
        header_layout.addWidget(self.filter_combo)
        
        layout.addLayout(header_layout)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setSpacing(15)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

    def open_add_timer_dialog(self):
        dialog = AddTimerDialog(self)
        if dialog.exec():
            name, t_type, duration = dialog.get_data()
            if self.data_manager.add_timer(name, t_type, duration):
                self.refresh_data()

    def open_settings_dialog(self):
        dialog = TimerSettingsDialog(self, self.data_manager)
        dialog.exec()

    def open_edit_timer_dialog(self, timer_data):
        dialog = AddTimerDialog(self, timer_data)
        if dialog.exec():
            name, t_type, duration = dialog.get_data()
            updates = {
                "name": name,
                "type": t_type,
                "duration": duration
            }
            if self.data_manager.update_timer(timer_data["id"], updates):
                self.refresh_data()

    def refresh_data(self):
        # Clear existing
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.timers = self.data_manager.get_timers()
        self.timer_widgets = []
        
        filter_type = self.filter_combo.currentText()
        
        visible_timers = []
        for t in self.timers:
            if filter_type == "Все" or t["type"] == filter_type:
                visible_timers.append(t)
                
        if not visible_timers:
            lbl = QLabel("Нет активных таймеров. Создайте новый!")
            if filter_type != "Все":
                lbl.setText(f"Нет таймеров типа '{filter_type}'")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #7f8c8d; font-size: 18px; margin-top: 50px;")
            self.cards_layout.addWidget(lbl)
        else:
            # Sort: Active first, then by remaining time
            for timer in visible_timers:
                card = TimerCard(timer, self)
                self.cards_layout.addWidget(card)
                self.timer_widgets.append(card)
                
        self.cards_layout.addStretch()

    def on_tick(self):
        if not hasattr(self, 'timer_widgets'):
            return
            
        now = datetime.now().timestamp()
        
        for card in self.timer_widgets:
            card.update_ui()
            
            # Check for notification
            timer = card.timer_data
            if timer["is_running"]:
                remaining = timer["end_time"] - now
                if remaining <= 0 and timer["id"] not in self.notified_timers:
                    # Check notification mode
                    mode = self.get_notification_mode()
                    
                    if mode == "silent_keep" and timer["type"] == "Контракт":
                         # Mark as notified but don't show dialog
                         self.notified_timers.add(timer["id"])
                    else:
                        # "notify_and_delete" or "notify_keep" or not a contract
                        self.trigger_notification(timer)

    def trigger_notification(self, timer):
        # Mark as notified immediately to prevent double triggers
        self.notified_timers.add(timer["id"])

        # Check if window is hidden (System Tray mode)
        if not self.main_window.isVisible() and hasattr(self.main_window, 'tray_icon'):
             self.main_window.tray_icon.showMessage(
                 "Таймер завершен!",
                 f"Таймер «{timer['name']}» истек!",
                 QSystemTrayIcon.MessageIcon.Information,
                 5000
             )
             
             # Even in tray mode, play the selected sound
             sound_file = self.data_manager.get_setting("timer_sound", "beep.wav")
             sound_path = resource_path(os.path.join("assets", "sounds", sound_file))
             if os.path.exists(sound_path):
                 self.play_standalone_sound(sound_path)
             else:
                 QApplication.beep()

             # Handle auto-delete for tray notification
             mode = self.get_notification_mode()
             if mode == "notify_and_delete" and timer["type"] == "Контракт":
                 self.data_manager.delete_timer(timer["id"])
                 self.refresh_data()
             return
        
        # Get settings
        is_topmost = self.data_manager.get_setting("timer_topmost", False)
        is_loop = self.data_manager.get_setting("timer_loop", False)
        sound_file = self.data_manager.get_setting("timer_sound", "beep.wav")
        sound_path = resource_path(os.path.join("assets", "sounds", sound_file))

        if is_topmost:
            # Minimize all windows (simulate Win+D)
            # Note: This is a Windows-specific shell call, for cross-platform we can't easily do this without specific libs
            # but we can at least make our window topmost and fullscreen.
            if os.name == 'nt':
                try:
                    import ctypes
                    ctypes.windll.user32.ShowCursor(True)
                    # Minimize all windows (Win+D)
                    import subprocess
                    subprocess.run(["powershell", "-Command", "(New-Object -ComObject shell.application).minimizeall()"], capture_output=True)
                except:
                    pass
            
            # Show Fullscreen Notification
            dlg = FullscreenNotification(timer['name'], sound_path, loop_sound=is_loop)
            res = dlg.exec()
            
            if res == 10: # Snooze
                self.snooze_timer(timer)
            else:
                self.on_notification_closed(timer)
        else:
            # Custom Dialog
            dlg = TimerCompleteDialog(self, timer['name'])
            # Make it stay on top
            dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            
            # Play sound
            if os.path.exists(sound_path):
                self.play_standalone_sound(sound_path, loop=is_loop)
            else:
                QApplication.beep()

            # Handle deletion after dialog close
            dlg.finished.connect(lambda result: self.on_notification_closed(timer))
            dlg.show()
            self._current_notification = dlg

    def play_standalone_sound(self, sound_path, loop=False):
        """Helper to play sound without a dedicated dialog."""
        if not hasattr(self, '_standalone_player'):
            self._standalone_player = QMediaPlayer()
            self._standalone_audio = QAudioOutput()
            self._standalone_player.setAudioOutput(self._standalone_audio)
        
        self._standalone_player.setSource(QUrl.fromLocalFile(sound_path))
        self._standalone_audio.setVolume(1.0)
        if loop:
            self._standalone_player.setLoops(QMediaPlayer.Loops.Infinite)
        else:
            self._standalone_player.setLoops(QMediaPlayer.Loops.Once)
        self._standalone_player.play()

    def snooze_timer(self, timer):
        """Snoozes the timer for 5 minutes."""
        # Update timer in DB to +5 minutes from now
        now = datetime.now().timestamp()
        duration = 5 * 60
        updates = {
            "start_time": now,
            "end_time": now + duration,
            "duration": duration,
            "is_running": True,
            "paused_remaining": 0
        }
        if self.data_manager.update_timer(timer["id"], updates):
            # Remove from notified set to allow re-notification
            if timer["id"] in self.notified_timers:
                self.notified_timers.remove(timer["id"])
            self.refresh_data()
            logger.info(f"Timer {timer['name']} snoozed for 5 minutes.")

    def on_notification_closed(self, timer):
        mode = self.get_notification_mode()
        if mode == "notify_and_delete" and timer["type"] == "Контракт":
             self.data_manager.delete_timer(timer["id"])
             self.refresh_data()

    def apply_theme(self, theme):
        # Optional: Implement theme logic if strictly needed, 
        # but current styles are hardcoded dark which fits the app generally.
        pass

    def get_notification_mode(self):
        mode = self.data_manager.get_setting("contract_notification_mode", "")
        if mode: return mode
        
        # Fallback
        if self.data_manager.get_setting("auto_delete_contracts", False):
            return "notify_and_delete"
        else:
            return "notify_keep"

    def process_expired_contracts(self):
        """Check for and delete expired 'Contract' timers if setting is enabled."""
        try:
            mode = self.get_notification_mode()
            if mode != "notify_and_delete":
                return

            timers = self.data_manager.get_timers()
            now = datetime.now().timestamp()
            deleted_count = 0
            
            # We iterate over a copy or collect IDs to delete
            timers_to_delete = []
            
            for t in timers:
                if t["type"] == "Контракт" and t["is_running"]:
                    remaining = t["end_time"] - now
                    if remaining <= 0:
                        timers_to_delete.append(t)
            
            for t in timers_to_delete:
                if self.data_manager.delete_timer(t["id"]):
                    deleted_count += 1
                    logger.info(f"Auto-deleted expired contract: {t['name']} (ID: {t['id']})")
                    
            if deleted_count > 0:
                logger.info(f"Auto-deleted {deleted_count} expired contracts on startup.")
        except Exception as e:
            logger.error(f"Error processing expired contracts: {e}")

    def stop(self):
        """Stop internal timers to allow clean application exit."""
        if hasattr(self, 'update_timer') and self.update_timer.isActive():
            self.update_timer.stop()
            logger.info("TimersTab update timer stopped.")
