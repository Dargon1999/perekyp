from PyQt5 import QtWidgets, QtCore, QtGui
from widgets.common import CommonUI, CommonLogger
from utils.mem_reduct_api import MemReductAPI
import time

class MemReductWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api = MemReductAPI()
        self._init_ui()
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(2000)

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group, g_layout = CommonUI.create_settings_group("🧠 Mem Reduct")
        
        self.stats_label = QtWidgets.QLabel("Загрузка данных...")
        self.stats_label.setStyleSheet("color: white; font-family: monospace; font-size: 12px;")
        g_layout.addWidget(self.stats_label)

        # Profiles
        self.profile_combo = QtWidgets.QComboBox()
        self.profile_combo.addItems(["Лёгкая очистка", "Средняя очистка", "Агрессивная (Admin)"])
        self.profile_combo.setStyleSheet("background: #333; color: white;")
        g_layout.addWidget(self.profile_combo)

        self.clean_btn = QtWidgets.QPushButton("🧹 Очистить память")
        self.clean_btn.clicked.connect(self._clean)
        self.clean_btn.setStyleSheet("""
            QPushButton { background: #0A84FF; color: white; font-weight: bold; padding: 5px; }
            QPushButton:hover { background: #007AFF; }
        """)
        g_layout.addWidget(self.clean_btn)

        self.info_label = QtWidgets.QLabel("")
        self.info_label.setStyleSheet("color: #2EE279; font-weight: bold;")
        g_layout.addWidget(self.info_label)

        layout.addWidget(group)

    def _update_stats(self):
        stats = self.api.get_stats()
        if not stats:
            self.stats_label.setText("DLL не найдена или ошибка API")
            return

        text = (
            f"Всего:    {self.api.format_bytes(stats.total_phys)}\n"
            f"Занято:   {self.api.format_bytes(stats.used_phys)}\n"
            f"Свободно: {self.api.format_bytes(stats.avail_phys)}\n"
            f"Кэш:      {self.api.format_bytes(stats.system_cache)}"
        )
        self.stats_label.setText(text)

    def _clean(self):
        level = self.profile_combo.currentIndex()
        
        stats_before = self.api.get_stats()
        if not stats_before: return

        if self.api.clean(level):
            time.sleep(0.5)
            stats_after = self.api.get_stats()
            if stats_after:
                saved = stats_before.used_phys - stats_after.used_phys
                if saved > 0:
                    self.info_label.setText(f"✅ Освобождено: {self.api.format_bytes(saved)}")
                else:
                    self.info_label.setText("✅ Память уже оптимизирована")
        else:
            self.info_label.setText("❌ Ошибка очистки")
