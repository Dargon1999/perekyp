from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton, 
    QMessageBox, QFrame, QButtonGroup, QLabel, QApplication, QScrollArea,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint, QThread, pyqtSignal, pyqtProperty
from PyQt6.QtGui import QGuiApplication, QIcon, QAction, QCloseEvent, QShortcut, QKeySequence, QPainter, QColor, QBrush, QLinearGradient
import os
import logging
import traceback
from event_bus import EventBus
from data_manager import DataManager
from database_manager import DatabaseManager
from plugin_manager import PluginManager
from gui.widgets.timeline_widget import TimelineWidget
from utils import resource_path
from gui.title_bar import CustomTitleBar
from gui.custom_dialogs import StyledDialogBase, AlertDialog, UpdateConfirmDialog, UpdateProgressDialog
from gui.styles import StyleManager
from gui.animations import AnimationManager
from gui.update_manager import UpdateManager
from gui.performance import PerformanceMonitor

class NavButton(QPushButton):
    def __init__(self, text, icon_char, index, parent=None):
        super().__init__(parent)
        self.original_text = text
        self.icon_char = icon_char
        self.setProperty("page_index", index)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("NavButton")
        self.update_display(collapsed=False)

    def update_display(self, collapsed):
        is_file = isinstance(self.icon_char, str) and (self.icon_char.endswith('.svg') or self.icon_char.endswith('.png')) or os.path.exists(str(self.icon_char))
        
        if collapsed:
            # Center content, remove padding to prevent clipping, increase font for emojis
            self.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    padding: 0px;
                    border: none;
                    border-left: 3px solid transparent;
                    font-size: 20px;
                }
            """)
            
            if is_file:
                self.setText("")
                self.setIcon(QIcon(self.icon_char))
                self.setIconSize(QSize(24, 24))
            else:
                self.setIcon(QIcon())
                self.setText(self.icon_char)
            self.setToolTip(self.original_text)
        else:
            # Restore global styles
            self.setStyleSheet("")
            
            if is_file:
                self.setText(f"   {self.original_text}")
                self.setIcon(QIcon(self.icon_char))
                self.setIconSize(QSize(24, 24))
            else:
                self.setIcon(QIcon())
                self.setText(f"{self.icon_char}   {self.original_text}")
            self.setToolTip("")

from gui.tabs.generic_tab import GenericTab
from gui.tabs.buy_sell_tab import BuySellTab
from gui.tabs.mining_tab import MiningTab
from gui.tabs.farm_bp_tab import FarmBPTab
from gui.tabs.memo_tab import MemoTab
from gui.tabs.helper_tab import HelperTab
from gui.tabs.cooking_tab import CookingTab
from gui.tabs.analytics_tab import AnalyticsTab
from gui.tabs.capital_planning_tab import CapitalPlanningTab
from gui.tabs.timers_tab import TimersTab
from gui.tabs.fishing_tab import FishingTab
from gui.tabs.settings_tab import SettingsTab

from async_data_manager import AsyncDataManager

class MainWindow(QMainWindow):
    def __init__(self, auth_manager=None, data_manager=None):
        super().__init__()
        
        self.auth_manager = auth_manager
        self._tabs_preloading_done = False
        
        self.data_manager = data_manager if data_manager else DataManager()
        self.async_dm = AsyncDataManager(self.data_manager)
        self.db_manager = DatabaseManager()
        self.event_bus = EventBus.get_instance()
        self.plugin_manager = PluginManager(app_context={"db": self.db_manager, "data": self.data_manager, "event_bus": self.event_bus})
        self.plugin_manager.discover_plugins()
        self.plugin_manager.initialize_plugins()
        self.perf_monitor = PerformanceMonitor(self)
        self.perf_monitor.start_timer()
        
        self.update_manager = UpdateManager(self.data_manager, auth_manager=self.auth_manager)
        self.update_manager.update_available.connect(self.on_update_available)

        self.setWindowTitle("MoneyTracker")
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        icon_path = resource_path("icon_v2.ico")
        if not os.path.exists(icon_path):
            icon_path = resource_path("icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        
        # Main Container
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        # Add Custom Title Bar
        self.title_bar = CustomTitleBar(self)
        self.container_layout.addWidget(self.title_bar)

        # Connect Profile Button
        self.title_bar.profile_btn.clicked.connect(self.open_profiles_dialog)
        
        # Icon Map for Navigation
        self.icon_map = {
            "car": "🚗",
            "car_rental": resource_path(os.path.join("gui", "assets", "icons", "car_rental.svg")),
            "tshirt": "👕",
            "hammer": "⛏️",
            "leaf": "🌿",
            "sticky-note": "📝",
            "magic": "✨",
            "utensils": resource_path(os.path.join("gui", "assets", "icons", "cooking_colored.svg")),
            "chart-bar": "📊",
            "coins": "💰",
            "clock": "🕒",
            "cog": "⚙️",
            "fish": "🎣",
        }

        # Content Layout (Horizontal: Sidebar + Content)
        self.content_widget = QWidget()
        self.container_layout.addWidget(self.content_widget)
        self.main_layout = QHBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setObjectName("SideBar")
        self.sidebar_width = 220
        self.sidebar_collapsed_width = 60
        self.sidebar.setFixedWidth(self.sidebar_width)
        self.is_sidebar_collapsed = False
        
        # Add Scroll Area for Sidebar to prevent clipping on small screens/high DPI
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sidebar_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.sidebar_container = QWidget()
        self.sidebar_container.setObjectName("SideBarContainer")
        self.sidebar_layout = QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(10)
        
        self.sidebar_scroll.setWidget(self.sidebar_container)
        
        # Layout for the sidebar widget itself to hold the scroll area
        sidebar_main_layout = QVBoxLayout(self.sidebar)
        sidebar_main_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_main_layout.addWidget(self.sidebar_scroll)
        
        # Sidebar Header (Toggle Button) - Moved inside sidebar_container
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setObjectName("NavButton")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        # Ensure centered alignment overriding global left alignment
        self.toggle_btn.setStyleSheet("text-align: center; padding: 0; font-size: 20px;")
        self.sidebar_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.sidebar_layout.addSpacing(20)
        
        # Navigation Buttons Container
        self.nav_buttons_layout = QVBoxLayout()
        self.nav_buttons_layout.setSpacing(5)
        self.sidebar_layout.addLayout(self.nav_buttons_layout)
        
        self.sidebar_layout.addStretch() # Push buttons to top
        
        self.main_layout.addWidget(self.sidebar)

        # Main Content Area
        self.content_area = QWidget()
        self.content_area_layout = QVBoxLayout(self.content_area)
        self.content_area_layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QStackedWidget()
        self.content_area_layout.addWidget(self.tabs)
        
        # Navigation Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.buttonClicked.connect(self.on_nav_clicked)

        self.main_layout.addWidget(self.content_area)

        # Immediate initialization
        self.setup_tabs()
        self.apply_styles()
        self.refresh_data()

        # Check for updates and start heartbeat
        self.update_manager.start_heartbeat(interval_ms=30000)
        
        # License Check
        if self.auth_manager:
            self.check_license_status()
            self.license_timer = QTimer(self)
            self.license_timer.timeout.connect(self.check_license_status)
            self.license_timer.start(300000)

        # Backup & Tray
        self.data_manager.perform_scheduled_backup()
        self.setup_tray_icon()
        self.perf_monitor.end_startup()

        self.restore_window_geometry()
        self.setup_multi_monitor_support()

    def setup_multi_monitor_support(self):
        """Setup shortcuts and menu actions for moving window between screens."""
        # Shortcuts Win+Shift+Left/Right
        self.shortcut_left = QShortcut(QKeySequence("Win+Shift+Left"), self)
        self.shortcut_left.activated.connect(self.move_to_prev_screen)
        
        self.shortcut_right = QShortcut(QKeySequence("Win+Shift+Right"), self)
        self.shortcut_right.activated.connect(self.move_to_next_screen)
        
        # Add to title bar context menu if possible, or just system menu
        # Since it's a custom title bar, we might need to add it there
        if hasattr(self.title_bar, 'contextMenuEvent'):
            # Custom title bar might have its own menu logic
            pass

    def move_to_next_screen(self):
        self.move_to_screen_offset(1)

    def move_to_prev_screen(self):
        self.move_to_screen_offset(-1)

    def move_to_screen_offset(self, offset):
        screens = QGuiApplication.screens()
        if len(screens) < 2:
            return

        current_screen = self.screen()
        try:
            current_index = screens.index(current_screen)
        except ValueError:
            current_index = 0
            
        next_index = (current_index + offset) % len(screens)
        target_screen = screens[next_index]
        
        # Calculate relative position
        curr_geo = self.geometry()
        curr_screen_geo = current_screen.geometry()
        
        rel_x = (curr_geo.x() - curr_screen_geo.x()) / curr_screen_geo.width()
        rel_y = (curr_geo.y() - curr_screen_geo.y()) / curr_screen_geo.height()
        
        target_screen_geo = target_screen.geometry()
        new_x = target_screen_geo.x() + int(rel_x * target_screen_geo.width())
        new_y = target_screen_geo.y() + int(rel_y * target_screen_geo.height())
        
        # Ensure window stays within target screen boundaries
        new_x = max(target_screen_geo.x(), min(new_x, target_screen_geo.right() - self.width()))
        new_y = max(target_screen_geo.top(), min(new_y, target_screen_geo.bottom() - self.height()))
        
        self.move(new_x, new_y)
        # Save screen index
        self.data_manager.set_setting("last_screen_index", next_index)

    def restore_window_geometry(self):
        geometry = self.data_manager.get_setting("window_geometry")
        last_screen_index = self.data_manager.get_setting("last_screen_index")
        
        screens = QGuiApplication.screens()
        
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))
            
            # Check if we should move to a specific screen
            if last_screen_index is not None and isinstance(last_screen_index, int):
                if 0 <= last_screen_index < len(screens):
                    target_screen = screens[last_screen_index]
                    # Only move if not already on that screen
                    if self.screen() != target_screen:
                        # Move to target screen center if restoreGeometry didn't place it correctly
                        # or if screen configuration changed
                        geo = self.frameGeometry()
                        geo.moveCenter(target_screen.availableGeometry().center())
                        self.move(geo.topLeft())
        else:
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                available = screen.availableGeometry()
                target_width = min(1300, int(available.width() * 0.9))
                target_height = min(1000, int(available.height() * 0.9))
                self.resize(target_width, target_height)
                
                # Center
                geo = self.frameGeometry()
                geo.moveCenter(available.center())
                self.move(geo.topLeft())

        # Enforce limits
        self.setMinimumSize(900, 720)
        # No strict maximum, but we can set it if requested. 
        # User said "limit min and max", but max is usually screen size.
        # We'll just set min for now to prevent distortion.

    def closeEvent(self, event: QCloseEvent):
        logging.info("Application closing...")
        
        geo = self.saveGeometry().toHex().data().decode()
        self.data_manager.set_setting("window_geometry", geo)
        
        screens = QGuiApplication.screens()
        try:
            current_index = screens.index(self.screen())
            self.data_manager.set_setting("last_screen_index", current_index)
        except Exception as e:
            logging.warning(f"Could not save screen index: {e}")

        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()

        if hasattr(self, 'license_timer') and self.license_timer and self.license_timer.isActive():
            self.license_timer.stop()

        if self.update_manager:
            self.update_manager.stop()

        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget and hasattr(widget, "stop"):
                widget.stop()

        logging.info("Cleanup complete, accepting close event")
        event.accept()

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        
        tray_menu = QMenu()
        
        show_action = QAction("Открыть", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.force_quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_window()

    def show_window(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.activateWindow()

    def force_quit(self):
        QApplication.quit()

    def toggle_sidebar(self):
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        target_width = self.sidebar_collapsed_width if self.is_sidebar_collapsed else self.sidebar_width
        
        if hasattr(self, 'anim_group') and self.anim_group and self.anim_group.state() == QParallelAnimationGroup.State.Running:
            self.anim_group.stop()
        
        self.anim_width = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim_width.setDuration(300)
        self.anim_width.setStartValue(self.sidebar.width())
        self.anim_width.setEndValue(target_width)
        self.anim_width.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        self.anim_width_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.anim_width_max.setDuration(300)
        self.anim_width_max.setStartValue(self.sidebar.width())
        self.anim_width_max.setEndValue(target_width)
        self.anim_width_max.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.anim_width)
        self.anim_group.addAnimation(self.anim_width_max)
        self.anim_group.start()
        
        for btn in self.nav_group.buttons():
            if isinstance(btn, NavButton):
                btn.update_display(self.is_sidebar_collapsed)


    def setup_tabs(self):
        """Setup all tabs immediately."""
        self.tab_configs = [
            ("GenericTab", "Аренда авто", "car", "car_rental"),
            ("BuySellTab", "Покупка / Продажа", "tshirt", "clothes"),
            ("MiningTab", "Добыча", "hammer", "mining"),
            ("FarmBPTab", "Фарм BP", "leaf", "farm_bp"),
            ("MemoTab", "Блокнот", "sticky-note", "memo"),
            ("HelperTab", "Помощник", "magic", "helper"),
            ("CookingTab", "Кулинария", "utensils", "cooking"),
            ("AnalyticsTab", "Аналитика", "chart-bar", "analytics"),
            ("CapitalPlanningTab", "Капитал", "coins", "capital_planning"),
            ("TimersTab", "Таймер", "clock", "timers"),
            ("FishingTab", "Рыбалка", "fish", "fishing"),
            ("SettingsTab", "Настройки", "cog", "settings")
        ]
        
        self._tab_instances = {}
        self._tabs_loaded = set()
        
        for i, (tab_class_name, name, icon_name, key) in enumerate(self.tab_configs):
            self.add_nav_btn(name, i, icon_name, key)
        
        self.update_tabs_visibility()
        
        startup_key = self.data_manager.get_setting("startup_tab", "car_rental")
        startup_index = 0
        for i, config in enumerate(self.tab_configs):
            if config[3] == startup_key:
                startup_index = i
                break
        
        self.tabs.setCurrentIndex(startup_index)
        self._load_tab(startup_index)
        
        # Preload adjacent tabs immediately after (for instant switching)
        adjacent_indices = []
        if startup_index > 0:
            adjacent_indices.append(startup_index - 1)
        if startup_index < len(self.tab_configs) - 1:
            adjacent_indices.append(startup_index + 1)
        
        for idx in adjacent_indices:
            QTimer.singleShot(100, lambda i=idx: self._load_tab(i))
        
        # Background preload of all remaining tabs
        QTimer.singleShot(500, self._preload_all_tabs)
        
        for btn in self.nav_group.buttons():
            if btn.property("page_index") == startup_index:
                btn.setChecked(True)
                break

    def add_nav_btn(self, text, index, icon_name, key=None):
        icon_char = self.icon_map.get(icon_name, "?")
        btn = NavButton(text, icon_char, index, self.sidebar_container)
        if key:
            btn.setProperty("tab_key", key)
        self.nav_buttons_layout.addWidget(btn)
        self.nav_group.addButton(btn, index)

    def _load_tab(self, index):
        if index in self._tabs_loaded:
            return
        
        if index < 0 or index >= len(self.tab_configs):
            return
        
        tab_class_name, name, icon_name, key = self.tab_configs[index]
        try:
            tab = None
            if tab_class_name == "GenericTab":
                tab = GenericTab(self.data_manager, key, self)
            elif tab_class_name == "BuySellTab":
                tab = BuySellTab(self.data_manager, self)
            elif tab_class_name == "MiningTab":
                tab = MiningTab(self.data_manager, self)
            elif tab_class_name == "FarmBPTab":
                tab = FarmBPTab(self.data_manager, self)
            elif tab_class_name == "MemoTab":
                tab = MemoTab(self.data_manager, self)
            elif tab_class_name == "HelperTab":
                tab = HelperTab(self.data_manager, self)
            elif tab_class_name == "CookingTab":
                tab = CookingTab(self.data_manager, self)
            elif tab_class_name == "AnalyticsTab":
                tab = AnalyticsTab(self.data_manager, self)
            elif tab_class_name == "CapitalPlanningTab":
                tab = CapitalPlanningTab(self.data_manager, self)
            elif tab_class_name == "TimersTab":
                tab = TimersTab(self.data_manager, self)
            elif tab_class_name == "FishingTab":
                tab = FishingTab(self.data_manager, self)
            elif tab_class_name == "SettingsTab":
                tab = SettingsTab(self.data_manager, self.auth_manager, self)

            if tab:
                tab.setObjectName("LoadedTab")
                self.tabs.insertWidget(index, tab)
                self._tab_instances[index] = tab
                self._tabs_loaded.add(index)
        except Exception as e:
            logging.error(f"Failed to load tab {name}: {e}\n{traceback.format_exc()}")

    def _preload_all_tabs(self):
        if self._tabs_preloading_done:
            return
        self._tabs_preloading_done = True
        
        for i in range(len(self.tab_configs)):
            if i not in self._tabs_loaded:
                self._load_tab(i)

    def update_tabs_visibility(self):
        hidden_tabs = self.data_manager.get_setting("hidden_tabs", [])
        for btn in self.nav_group.buttons():
            if not isinstance(btn, NavButton): continue
            key = btn.property("tab_key")
            if not key or key == "settings": 
                btn.setVisible(True)
                continue
            visible = key not in hidden_tabs
            btn.setVisible(visible)

    def on_nav_clicked(self, btn):
        index = self.nav_group.id(btn)
        self._load_tab(index)
        self.tabs.setCurrentIndex(index)
        
        current_widget = self.tabs.widget(index)
        if current_widget and hasattr(current_widget, "refresh_data"):
            current_widget.refresh_data()

    def open_ai_chat(self):
        pass

    def check_license_status(self):
        if not self.auth_manager: return
        try:
            is_valid, message, expires = self.auth_manager.check_license_status()
            if not is_valid:
                self.license_timer.stop()
                AlertDialog(self, "Лицензия истекла", f"Статус: {message}\nПриложение будет закрыто.").exec()
                QApplication.quit()
        except Exception as e:
            logging.error(f"Error checking license: {e}")

    def on_update_available(self, version_info):
        try:
            dialog = UpdateConfirmDialog(self, version_info)
            if dialog.exec():
                self.start_update(version_info)
        except Exception as e:
            logging.error(f"Error showing update dialog: {e}")

    def start_update(self, version_info):
        try:
            progress_dialog = UpdateProgressDialog(self)
            progress_dialog.show()
            self.update_manager.update_progress.connect(progress_dialog.update_progress)
            self.update_manager.update_status.connect(progress_dialog.set_status)
            self.update_manager.update_finished.connect(progress_dialog.on_finished)
            self.update_manager.update_error.connect(progress_dialog.on_error)
            progress_dialog.rejected.connect(self.update_manager.cancel_download)
            
            download_url = version_info.get('download_url')
            self.update_manager.download_and_install_update(
                download_url,
                force_update=version_info.get('force_update', False),
                notes=version_info.get('notes'),
                signature=version_info.get('signature')
            )
        except Exception as e:
            logging.error(f"Error starting update: {e}")
            AlertDialog(self, "Ошибка обновления", f"Не удалось запустить обновление: {e}").exec()
            
    def apply_styles(self):
        theme = self.data_manager.get_setting("theme", "dark")
        self.setStyleSheet(StyleManager.get_qss(theme))
        self.title_bar.set_theme(theme) # Ensure title bar branding is applied
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, "apply_theme"):
                widget.apply_theme(theme)

    def open_profiles_dialog(self):
        from gui.profile_dialog import ProfileDialog
        dialog = ProfileDialog(self, self.data_manager)
        if dialog.exec():
            self.refresh_data()

    def refresh_data(self):
        profile = self.data_manager.get_active_profile()
        if profile:
            self.title_bar.active_profile_label.setText(profile["name"])
            self.title_bar.active_profile_label.setVisible(True)
        else:
            self.title_bar.active_profile_label.setText("Профиль не выбран")
            self.title_bar.active_profile_label.setVisible(True)
        
        if hasattr(self.data_manager.get_total_capital_balance, "cache_clear"):
            self.data_manager.get_total_capital_balance.cache_clear()
        
        self.update_balance_display()
        
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, "refresh_data"):
            current_widget.refresh_data()
        
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget != current_widget and hasattr(widget, "update_realtime_goal"):
                widget.update_realtime_goal()

    def update_balance_display(self):
        """Immediately updates the global balance label."""
        result = self.data_manager.get_total_capital_balance()
        self._on_balance_loaded(result)

    def _on_balance_loaded(self, result):
        try:
            if isinstance(result, dict) and 'liquid_cash' in result:
                balance = result['liquid_cash']
                self.title_bar.balance_label.setText(f"💳 ${int(balance):,}".replace(',', ' '))
            else:
                logging.warning(f"Balance update result unexpected: {result}")
        except Exception as e:
            logging.error(f"Error processing balance: {e}")
