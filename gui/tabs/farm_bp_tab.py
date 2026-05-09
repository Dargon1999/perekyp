from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QGridLayout, QDialog, QTableWidget, 
    QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect, QAbstractItemView,
    QLineEdit, QListView, QTableView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QAbstractListModel, QModelIndex, QRect, QAbstractTableModel
from PyQt6.QtGui import QCursor, QColor, QFont, QPainter, QTextOption
from datetime import datetime, timedelta
import logging
from gui.title_bar import CustomTitleBar
from gui.custom_dialogs import StyledDialogBase
from gui.styles import StyleManager
from gui.animations import AnimationManager
from gui.tabs.generic_tab import GenericTab

class TaskModel(QAbstractListModel):
    def __init__(self, tasks, parent=None):
        super().__init__(parent)
        self.tasks = tasks # List of dictionaries

    def rowCount(self, parent=QModelIndex()):
        return len(self.tasks)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        task = self.tasks[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return task
        return None

class FarmBPTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        
        # Define Tasks Configuration
        # (Name, Base Reward, Icon, IsMulti)
        self.tasks_config = [
            # ... (keep the same config)
            ("3 часа в онлайне", 2, "⏳", True),
            ("Нули в казино", 2, "🎰", False),
            ("25 действий на стройке", 2, "🏗️", False),
            ("25 действий в порту", 2, "⚓", False),
            ("25 действий в шахте", 2, "⛏️", False),
            ("3 победы в Дэнс Баттлах", 2, "💃", False),
            ("Заказ материалов для бизнеса вручную", 1, "📦", False),
            ("20 подходов в тренажерном зале", 1, "🏋️", False),
            ("Успешная тренировка в тире", 1, "🎯", False),
            ("10 посылок на почте", 1, "✉️", False),
            ("Арендовать киностудию", 2, "🎬", False),
            ("Купить лотерейный билет", 1, "🎫", False),
            ("Выиграть гонку в картинге", 1, "🏎️", False),
            ("10 действий на ферме", 1, "🚜", False),
            ("Потушить 25 \"огоньков\" пожарным", 1, "🚒", False),
            ("Выкопать 1 сокровище(не мусор)", 1, "💎", False),
            ("Проехать 1 уличную гонку", 1, "🏁", False),
            ("Выполнить 3 заказа дальнобойщиком", 2, "🚚", False),
            ("Два раза оплатить смену внешности у хирурга в EMS", 2, "🏥", False),
            ("Добавить 5 видео в кинотеатре", 1, "🎥", False),
            ("Выиграть 5 игр в тренировочном комплексе", 1, "🥋", False),
            ("Выиграть 3 любых игры на арене", 1, "🏟️", False),
            ("2 круга на любом маршруте автобусника", 2, "🚌", False),
            ("5 раз снять 100% шкуру с животных", 2, "🦌", False),
            ("7 закрашенных граффити", 1, "🎨", False),
            ("Сдать 5 контрабанды", 2, "🎒", False),
            ("Участие в каптах/бизварах", 1, "⚔️", False),
            ("Сдать Хаммер с ВЗХ", 3, "🔨", False),
            ("5 выданных медкарт в EMS", 2, "💊", False),
            ("Закрыть 15 вызовов в EMS", 2, "🚑", False),
            ("Отредактировать 40 объявлений в WN", 2, "📰", False),
            ("Взломать 15 замков на ограблениях домов или автоугонах", 2, "🔓", False),
            ("Закрыть 5 кодов в силовых структурах", 2, "🚓", False),
            ("Поставить на учет 2 автомобиля (для LSPD)", 1, "🚔", False),
            ("Произвести 1 арест в КПЗ", 1, "👮", False),
            ("Выкупить двух человек из КПЗ", 2, "🔓", False),
            ("Посетить любой сайт в браузере", 1, "🌐", False),
            ("Зайти в любой канал в Brawl", 1, "💬", False),
            ("Поставить лайк любой анкете в Match", 1, "❤️", False),
            ("Прокрутить за DP серебрянный, золотой или driver кейс", 10, "💼", False),
            ("Кинуть мяч питомцу 15 раз", 2, "🎾", False),
            ("15 выполненных питомцем команд", 2, "🐕", False),
            ("Ставка в колесе удачи в казино", 3, "🎡", False),
            ("Проехать 1 станцию на метро", 2, "🚇", False),
            ("Поймать 20 рыб", 4, "🎣", False),
            ("Выполнить 2 квеста любых клубов", 4, "♣️", False),
            ("Починить деталь в автосервисе", 1, "🔧", False),
            ("Забросить 2 мяча в баскетболе", 1, "🏀", False),
            ("Забить 2 гола в футболе", 1, "⚽", False),
            ("Победить в армрестлинге", 1, "💪", False),
            ("Победить в дартс", 1, "🎯", False),
            ("Поиграть 1 минуту в волейбол", 1, "🏐", False),
            ("Поиграть 1 минуту в настольный теннис", 1, "🏓", False),
            ("Поиграть 1 минуту в большой теннис", 1, "🎾", False),
            ("Сыграть в мафию в казино", 3, "🕴️", False),
            ("Сделать платеж по лизингу", 1, "💳", False),
            ("Посадить траву в теплице", 4, "🌿", False),
            ("Запустить переработку обезболивающих в лаборатории", 4, "🧪", False),
            ("Принять участие в двух аирдропах", 4, "✈️", False)
        ]
        
        # Multiplier States
        self.x2_active = False
        self.vip_active = False
        
        # Performance Cache
        self._stats_cache = {
            "today_bp": 0,
            "total_bp": 0,
            "task_counts": {},
            "last_virtual_date": None,
            "last_transaction_count": 0
        }
        
        # Debounce for multiplier changes
        self.multiplier_timer = QTimer(self)
        self.multiplier_timer.setSingleShot(True)
        self.multiplier_timer.timeout.connect(self._apply_multipliers)
        
        # Model for virtualization
        self.model_data = []
        for name, base, icon, is_multi in self.tasks_config:
            self.model_data.append({
                "name": name,
                "base_reward": base,
                "icon": icon,
                "is_multi": is_multi,
                "count": 0
            })
        self.task_model = TaskModel(self.model_data, self)

        # Auto-refresh setup
        self.last_refresh_date = None
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_auto_refresh)
        self.refresh_timer.start(60000) # Check every minute
        
        self.init_ui()
        
    def get_virtual_date(self, dt=None):
        """
        Returns the 'Virtual Date' for the Farm BP system.
        The day starts at 06:00 AM.
        - If time is 06:00 - 23:59, date is today.
        - If time is 00:00 - 05:59, date is yesterday.
        """
        if dt is None:
            dt = datetime.now()
            
        if dt.hour < 6:
            return dt.date() - timedelta(days=1)
        return dt.date()

    def check_auto_refresh(self):
        """Check if we crossed the 6:00 AM boundary."""
        now = datetime.now()
        virtual_date = self.get_virtual_date(now)
        
        if self.last_refresh_date is None:
             self.last_refresh_date = virtual_date
             return

        if virtual_date != self.last_refresh_date:
            self.last_refresh_date = virtual_date
            self.perform_auto_refresh()

    def perform_auto_refresh(self):
        logging.info("Auto-refreshing Farm BP for new virtual day")
        try:
            # Just refresh data, logic handles the date filtering
            self.refresh_data()
            
            logging.info("Auto-refresh completed")
            
            # Visual confirmation
            original_text = self.today_label.text()
            self.today_label.setText(original_text + " (Новый день!)")
            self.today_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2ecc71;") # Green
            
            # Revert after 5 seconds
            QTimer.singleShot(5000, lambda: self.refresh_data()) 
            
        except Exception as e:
            logging.error(f"Error during auto-refresh: {e}")

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header Area
        self.header = QFrame()
        self.header_layout = QVBoxLayout(self.header)
        self.header_layout.setContentsMargins(20, 15, 20, 15)
        self.header_layout.setSpacing(10)
        
        # Top Row: Stats
        self.stats_layout = QHBoxLayout()
        self.today_label = QLabel("Сегодня: 0 BP")
        self.today_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #f39c12;")
        
        self.total_label = QLabel("Всего: 0 BP")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #95a5a6;")
        
        self.stats_layout.addWidget(self.today_label)
        self.stats_layout.addSpacing(20)
        self.stats_layout.addWidget(self.total_label)
        self.stats_layout.addStretch()

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск задания...")
        self.search_input.setMinimumWidth(150)
        self.search_input.setMaximumWidth(300)
        
        # Debounce timer for search
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_filter)
        self.search_input.textChanged.connect(self.on_search_changed)
        
        self.header_layout.addWidget(self.search_input, 0, Qt.AlignmentFlag.AlignRight)
        
        # Bottom Row: Toggles
        self.toggles_layout = QHBoxLayout()
        self.toggles_layout.setSpacing(10)
        
        self.x2_btn = QPushButton("X2 Сервер")
        self.x2_btn.setCheckable(True)
        self.x2_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.x2_btn.toggled.connect(self.on_toggles_changed)
        
        self.vip_btn = QPushButton("VIP Gold/Plat")
        self.vip_btn.setCheckable(True)
        self.vip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vip_btn.toggled.connect(self.on_toggles_changed)
        
        self.history_btn = QPushButton("📜 История")
        self.history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_btn.clicked.connect(self.show_history)

        self.toggles_layout.addWidget(self.x2_btn)
        self.toggles_layout.addWidget(self.vip_btn)
        self.toggles_layout.addWidget(self.history_btn)
        self.toggles_layout.addStretch()
        
        self.header_layout.addLayout(self.stats_layout)
        self.header_layout.addLayout(self.toggles_layout)
        
        self.layout.addWidget(self.header)
        
        # Scroll Area for Tasks
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(8)
        self.content_layout.setContentsMargins(20, 10, 20, 20)
        
        self.task_widgets = []
        for name, base, icon, is_multi in self.tasks_config:
            tw = TaskWidget(name, base, icon, is_multi, self)
            self.content_layout.addWidget(tw)
            self.task_widgets.append(tw)
            
        self.content_layout.addStretch()
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)
        
        # Apply initial theme immediately after creation
        initial_theme = self.data_manager.get_setting("theme", "dark")
        self.apply_theme(initial_theme)
        
        self.is_initialized = False
        # self.refresh_data() # Deferred loading

    def showEvent(self, event):
        if not self.is_initialized:
            # Use singleShot to defer loading and allow UI to render first
            QTimer.singleShot(100, lambda: self.refresh_data())
            self.is_initialized = True
        super().showEvent(event)

    def on_search_changed(self, text):
        # Restart timer on every keystroke (debouncing)
        self.search_timer.start(300) # 300ms delay

    def perform_filter(self):
        text = self.search_input.text().lower()
        # Optimization: Disable updates while hiding/showing many widgets
        self.content_widget.setUpdatesEnabled(False)
        try:
            for tw in self.task_widgets:
                if text in tw.name.lower():
                    tw.show()
                else:
                    tw.hide()
        finally:
            self.content_widget.setUpdatesEnabled(True)

    def filter_tasks(self, text):
        # Deprecated: replaced by perform_filter with debouncing
        pass

    def refresh_data(self, force=False):
        # Calculate stats based on Virtual Date
        virtual_date = self.get_virtual_date()
        
        # Optimization: Check if we actually need to recalculate
        transactions = self.data_manager.get_transactions("farm_bp")
        
        if not force and \
           self._stats_cache["last_virtual_date"] == virtual_date and \
           self._stats_cache["last_transaction_count"] == len(transactions):
            return # Use existing data in widgets (they already have counts)

        today_bp = 0
        total_bp = 0
        task_counts = {}
        
        # Performance: Use local references for speed
        vd_str = virtual_date.strftime("%d.%m.%Y")
        
        for t in transactions:
            amount = float(t["amount"])
            total_bp += amount
            
            t_date_str = t["date"]
            
            # Fast comparison if strings match (most common)
            if t_date_str == vd_str:
                today_bp += amount
                name = t.get("item_name") or t.get("comment")
                if name:
                    task_counts[name] = task_counts.get(name, 0) + 1
            else:
                # Fallback for different date formats only if strings don't match
                try:
                    if "." in t_date_str:
                        day, month, year = map(int, t_date_str.split("."))
                        t_date = datetime(year, month, day).date()
                    else:
                        year, month, day = map(int, t_date_str.split("-"))
                        t_date = datetime(year, month, day).date()
                    
                    if t_date == virtual_date:
                        today_bp += amount
                        name = t.get("item_name") or t.get("comment")
                        if name:
                            task_counts[name] = task_counts.get(name, 0) + 1
                except:
                    continue
        
        # Update cache
        self._stats_cache.update({
            "today_bp": today_bp,
            "total_bp": total_bp,
            "task_counts": task_counts,
            "last_virtual_date": virtual_date,
            "last_transaction_count": len(transactions)
        })

        # Update UI Labels
        self.today_label.setText(f"Сегодня: {int(today_bp)} BP")
        self.total_label.setText(f"Всего: {int(total_bp)} BP")
        
        # Optimization: Batch update widgets
        self.content_widget.setUpdatesEnabled(False)
        try:
            for tw in self.task_widgets:
                tw.set_count(task_counts.get(tw.name, 0))
        finally:
            self.content_widget.setUpdatesEnabled(True)

    def on_toggles_changed(self):
        # Debounce multiplier updates to avoid 60+ UI refreshes while clicking fast
        self.multiplier_timer.start(50) # 50ms delay

    def _apply_multipliers(self):
        self.x2_active = self.x2_btn.isChecked()
        self.vip_active = self.vip_btn.isChecked()
        
        # Batch update reward displays
        self.content_widget.setUpdatesEnabled(False)
        try:
            for tw in self.task_widgets:
                tw.update_reward_display()
        finally:
            self.content_widget.setUpdatesEnabled(True)

    def add_bp_transaction(self, task_name, base_reward):
        # 1. Optimistic UI Update
        mult = 1
        if self.x2_active: mult *= 2
        if self.vip_active: mult *= 2
        amount = base_reward * mult
        
        # Find widget and update it immediately
        for tw in self.task_widgets:
            if tw.name == task_name:
                tw.set_count(tw.count + 1)
                break
        
        # Update labels immediately
        self._stats_cache["today_bp"] += amount
        self._stats_cache["total_bp"] += amount
        self.today_label.setText(f"Сегодня: {int(self._stats_cache['today_bp'])} BP")
        self.total_label.setText(f"Всего: {int(self._stats_cache['total_bp'])} BP")
        
        # 2. Defer Save to DataManager (prevents UI freeze during disk write)
        virtual_date = self.get_virtual_date()
        date_str = virtual_date.strftime("%d.%m.%Y")
        
        QTimer.singleShot(0, lambda: self.data_manager.add_transaction(
            "farm_bp", 
            amount, 
            task_name, 
            date_str,
            task_name
        ))
        
        # 3. Update cache to prevent full refresh from overwriting
        self._stats_cache["last_transaction_count"] += 1
        self._stats_cache["task_counts"][task_name] = self._stats_cache["task_counts"].get(task_name, 0) + 1

    def remove_bp_transaction(self, task_name, delete_all=False):
        # 1. Optimistic UI Update (Calculate delta first)
        transactions = self.data_manager.get_transactions("farm_bp")
        today_virtual_date = self.get_virtual_date()
        vd_str = today_virtual_date.strftime("%d.%m.%Y")
        
        to_delete_ids = []
        total_delta = 0
        deleted_count = 0
        
        # Optimization: Fast find transactions to delete
        for t in transactions:
            if t["date"] == vd_str:
                t_name = t.get("item_name") or t.get("comment")
                if t_name == task_name:
                    to_delete_ids.append(t["id"])
                    total_delta += float(t["amount"])
                    deleted_count += 1
                    if not delete_all:
                        break
        
        if not to_delete_ids:
            return

        # Update widget and labels immediately
        for tw in self.task_widgets:
            if tw.name == task_name:
                tw.set_count(max(0, tw.count - deleted_count))
                break
        
        self._stats_cache["today_bp"] -= total_delta
        self._stats_cache["total_bp"] -= total_delta
        self.today_label.setText(f"Сегодня: {int(self._stats_cache['today_bp'])} BP")
        self.total_label.setText(f"Всего: {int(self._stats_cache['total_bp'])} BP")
        
        # 2. Defer Save to DataManager
        def do_delete():
            for tid in to_delete_ids:
                self.data_manager.delete_transaction("farm_bp", tid)
        
        QTimer.singleShot(0, do_delete)
            
        # 3. Update cache
        self._stats_cache["last_transaction_count"] -= deleted_count
        self._stats_cache["task_counts"][task_name] = max(0, self._stats_cache["task_counts"].get(task_name, 0) - deleted_count)

    def show_history(self):
        dialog = HistoryDialog(self, self.data_manager)
        dialog.exec()

    def apply_theme(self, theme):
        self.current_theme = theme
        t = StyleManager.get_theme(theme)
        
        bg = t["bg_main"]
        header_bg = t["bg_secondary"]
        text_color = t["text_main"]
        sub_text = t["text_secondary"]
        item_bg = t["bg_secondary"]
        item_hover = t["bg_tertiary"]
        item_active = t["accent"] # When checked
        btn_bg = t["bg_tertiary"]
        btn_text = t["text_main"]
        btn_active = t["accent"]
            
        self.setStyleSheet(f"background-color: {bg};")
        self.header.setStyleSheet(f"background-color: {header_bg}; border-bottom: 1px solid #333;")
        self.today_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: #f39c12; background: transparent; border: none;")
        self.total_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {sub_text}; background: transparent; border: none;")
        
        # Central stylesheet for TaskWidgets to avoid individual setStyleSheet calls
        self.content_widget.setStyleSheet(f"""
            #TaskWidget {{
                background-color: {item_bg};
                border: 2px solid transparent;
                border-radius: 12px;
            }}
            #TaskWidget:hover {{
                background-color: {item_hover};
            }}
            #TaskWidget[is_done="true"] {{
                background-color: {item_active};
                border: 2px solid {item_active};
            }}
            #TaskWidget QLabel {{
                border: none;
                background: transparent;
            }}
            #TaskWidget QLabel#TaskIcon {{
                font-size: 20px;
            }}
            #TaskWidget QLabel#TaskName {{
                color: {text_color};
                font-size: 14px;
                font-weight: 500;
            }}
            #TaskWidget QLabel#TaskReward {{
                color: #7f8c8d;
                font-size: 15px;
                font-weight: bold;
            }}
            #TaskWidget QLabel#TaskCount {{
                color: {text_color};
                font-weight: bold;
                font-size: 16px;
            }}
            #TaskWidget[is_done="true"] QLabel {{
                color: white;
            }}
            #TaskWidget[is_done="true"] QLabel#TaskReward {{
                color: white;
            }}
        """)

        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {btn_text};
                border: 1px solid {btn_text};
                border-radius: 5px;
                padding: 5px 15px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:checked {{
                background-color: {btn_active}33;
                color: {btn_active};
                border: 1px solid {btn_active};
            }}
            QPushButton:hover {{
                background-color: {btn_text}1A;
            }}
        """
        self.x2_btn.setStyleSheet(btn_style)
        self.vip_btn.setStyleSheet(btn_style)
        self.history_btn.setStyleSheet(btn_style)

        # Search Input Style
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {t['border']};
                border-radius: 15px;
                padding: 5px 10px;
                background-color: transparent;
                color: {text_color};
            }}
            QLineEdit:focus {{
                border: 1px solid {t['accent']};
            }}
        """)
        
        # Update reward values (multipliers might have changed if this is called after init)
        for tw in self.task_widgets:
            tw.update_reward_display()

class HistoryModel(QAbstractTableModel):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._headers = ["Дата", "Задание", "BP"]
        self._theme = StyleManager.get_theme()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        trans = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return trans["date"]
            if col == 1: return trans.get("item_name") or trans.get("comment", "")
            if col == 2: return f"+{int(trans['amount'])}"
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 2: return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 2: return QColor(self._theme['success'])
            
        return None

class HistoryDialog(QDialog):
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.main_tab = parent
        self.data_manager = data_manager
        
        # Theme setup
        current_theme = getattr(parent, "current_theme", "dark")
        t = StyleManager.get_theme(current_theme)
        
        self.bg_color = t["bg_secondary"]
        self.border_color = t["border"]
        self.text_color = t["text_main"]
        self.shadow_color = QColor(0, 0, 0, 100)
        
        self.table_bg = t["bg_tertiary"]
        self.table_grid = t["border"]
        self.table_text = t["text_main"]
        self.header_bg = t["bg_main"]
        self.header_text = t["text_secondary"]
        self.btn_bg = "transparent"
        self.btn_text = t["text_main"]
        self.btn_active = t["accent"]

        # Window setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(700, 600)
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        self.layout.addWidget(self.container)
        
        # Content Layout
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        # Title Bar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.title_label.setText("История Фарм BP")
        # Pass theme string instead of hardcoded logic if CustomTitleBar supports it
        # Assuming CustomTitleBar needs "light" or "dark", but we have modern themes.
        # Let's rely on global stylesheet application for CustomTitleBar if possible,
        # or just pass "dark" as it's usually dark.
        # But CustomTitleBar logic in previous files was refactored.
        # Let's check title_bar.py if needed, but for now we set transparent bg.
        self.title_bar.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        self.title_bar.profile_btn.hide()
        self.title_bar.active_profile_label.hide()
        self.container_layout.addWidget(self.title_bar)
        
        # Inner Content
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        self.container_layout.addWidget(self.content_widget)
        
        self.setup_ui()

    def showEvent(self, event):
        AnimationManager.fade_in(self.container)
        super().showEvent(event)
        
    def setup_ui(self):
        # Filter Buttons
        filter_layout = QHBoxLayout()
        self.history_filter = "today"
        
        self.filter_btns = {}
        filters = [("today", "Сегодня"), ("week", "Неделя"), ("month", "Месяц"), ("all", "Все время")]
        
        for key, label in filters:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.btn_text};
                    border: 1px solid {self.btn_text};
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: 500;
                }}
                QPushButton:checked {{
                    background-color: {self.btn_active}33;
                    color: {self.btn_active};
                    border: 1px solid {self.btn_active};
                }}
                QPushButton:hover {{
                    background-color: {self.btn_active}1A;
                    color: {self.btn_active};
                }}
            """)
            btn.clicked.connect(lambda checked, k=key: self.update_history_filter(k))
            filter_layout.addWidget(btn)
            self.filter_btns[key] = btn
            
        self.filter_btns["today"].setChecked(True)
        filter_layout.addStretch()
        self.content_layout.addLayout(filter_layout)
        
        # Table (Virtualization via QTableView)
        self.table = QTableView()
        self.history_model = HistoryModel()
        self.table.setModel(self.history_model)
        
        self.table.setFont(QFont("Segoe UI", 12))
        self.table.horizontalHeader().setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Table Style
        self.table.setStyleSheet(f"""
            QTableView {{
                background-color: {self.table_bg};
                border: none;
                font-size: 14px;
                color: {self.table_text};
                padding: 5px;
            }}
            QHeaderView::section {{
                background-color: {self.header_bg};
                color: {self.header_text};
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }}
            QScrollBar:vertical {{
                background: {self.bg_color};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #555;
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        self.content_layout.addWidget(self.table)
        
        # Initial Load
        self.update_history_filter("today")

    def update_history_filter(self, filter_key):
        # Update buttons state
        for k, btn in self.filter_btns.items():
            btn.setChecked(k == filter_key)
            
        # Optimization: Caching transactions access
        transactions = self.data_manager.get_transactions("farm_bp")
        filtered = []
        
        # Use Virtual Date for consistency
        if self.main_tab and hasattr(self.main_tab, 'get_virtual_date'):
            today_date = self.main_tab.get_virtual_date()
        else:
            today_date = datetime.now().date()
            
        # Optimization: Pre-calculate week start
        start_week = today_date - timedelta(days=today_date.weekday())
        
        for t in transactions:
            t_date_str = t["date"]
            try:
                # Fast date check
                if filter_key == "today":
                    if t_date_str == today_date.strftime("%d.%m.%Y"):
                        filtered.append(t)
                        continue
                
                # Full parse only if needed
                if "." in t_date_str:
                    d, m, y = map(int, t_date_str.split("."))
                    t_date = datetime(y, m, d).date()
                else:
                    y, m, d = map(int, t_date_str.split("-"))
                    t_date = datetime(y, m, d).date()
                
                if filter_key == "today":
                    if t_date == today_date: filtered.append(t)
                elif filter_key == "week":
                    if start_week <= t_date <= today_date: filtered.append(t)
                elif filter_key == "month":
                    if t_date.year == today_date.year and t_date.month == today_date.month: filtered.append(t)
                else: # all
                    filtered.append(t)
            except:
                continue
        
        # Update model instead of re-creating table items (Virtualization!)
        self.history_model.beginResetModel()
        self.history_model._data = filtered
        self.history_model.endResetModel()

    def update_history_filter_legacy(self, filter_key, table):
        # Kept for compatibility if needed, but logic moved to update_history_filter
        pass



class HoverButton(QPushButton):
    def __init__(self, text_normal, text_hover, parent=None):
        super().__init__(text_normal, parent)
        self.text_normal = text_normal
        self.text_hover = text_hover
        
    def enterEvent(self, event):
        self.setText(self.text_hover)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setText(self.text_normal)
        super().leaveEvent(event)

class TaskWidget(QFrame):
    def __init__(self, name, base_reward, icon, is_multi, parent_tab):
        super().__init__()
        self.setObjectName("TaskWidget")
        self.name = name
        self.base_reward = base_reward
        self.icon = icon
        self.is_multi = is_multi
        self.parent_tab = parent_tab
        self.count = 0
        self.count_label = QLabel("0")
        self.count_label.setFixedWidth(30)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Default Theme Values (to prevent crash before theme is applied)
        self.normal_bg = "#2d2d2d"
        self.hover_bg = "#353535"
        self.active_bg = "#2c3e50"
        self.text_main_color = "white"
        self.arrow_color = "white"
        
        self.init_ui()
        
    def init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 6, 15, 6)
        self.layout.setSpacing(15)
        
        # Cursor styling
        if not self.is_multi:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("ЛКМ: Отметить/Снять выполнение")
        
        # Icon
        self.icon_label = QLabel(self.icon)
        self.icon_label.setObjectName("TaskIcon")
        self.icon_label.setFixedSize(30, 30)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Name
        self.name_label = QLabel(self.name)
        self.name_label.setObjectName("TaskName")
        self.name_label.setWordWrap(True)
        
        # Right Side Container (Reward + Controls)
        self.right_layout = QHBoxLayout()
        self.right_layout.setSpacing(10)
        
        # Reward Label
        self.reward_label = QLabel(f"+{self.base_reward}")
        self.reward_label.setObjectName("TaskReward")
        self.reward_label.setFixedWidth(40)
        self.reward_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Add widgets
        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.name_label, 1) # Stretch factor 1
        
        if self.is_multi:
            # Counter controls for Multi tasks (REPLACED Arrow buttons with direct mouse control)
            self.count_label.setFixedWidth(40)
            self.count_label.setObjectName("TaskCount")
            
            # We don't need buttons anymore, the whole widget will be clickable
            self.right_layout.addWidget(self.count_label)
            
            # Add visual hint for multi-tasks
            self.setToolTip("ЛКМ: Добавить (+1) | ПКМ: Убрать (-1)")
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.right_layout.addWidget(self.reward_label)
        self.layout.addLayout(self.right_layout)
        
        self.update_reward_display()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_multi:
                self.on_plus()
            else:
                self.toggle_single_task()
        elif event.button() == Qt.MouseButton.RightButton:
            if self.is_multi:
                self.on_minus()
            else:
                if self.count > 0:
                    self.toggle_single_task() # Toggle off if on
        super().mousePressEvent(event)

    def toggle_single_task(self):
        if self.count > 0:
            self.parent_tab.remove_bp_transaction(self.name, delete_all=True)
        else:
            self.parent_tab.add_bp_transaction(self.name, self.base_reward)

    def apply_theme(self, bg, hover, active, text, btn_bg, btn_text, btn_active):
        # Deprecated: Theme handled by parent's central stylesheet
        pass

    def update_style(self):
        # Optimization: Use dynamic properties instead of setStyleSheet
        is_done = self.count > 0
        self.setProperty("is_done", "true" if is_done else "false")
        
        # Trigger style refresh
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Reward Display updated separately
        self.update_reward_display()

    def update_reward_display(self):
        mult = 1
        if self.parent_tab.x2_active: mult *= 2
        if self.parent_tab.vip_active: mult *= 2
        val = self.base_reward * mult
        self.reward_label.setText(f"+{val}")

    def set_count(self, count):
        if self.count == count:
            return
            
        self.count = count
        if self.is_multi:
            self.count_label.setText(str(count))
        
        self.update_style()
        self.update_reward_display()

    def on_plus(self):
        self.parent_tab.add_bp_transaction(self.name, self.base_reward)

    def on_minus(self):
        if self.count > 0:
            self.parent_tab.remove_bp_transaction(self.name)
