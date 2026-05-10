from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton, 
    QMessageBox, QFrame, QButtonGroup, QLabel, QApplication, QScrollArea,
    QSystemTrayIcon, QMenu, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, 
    QParallelAnimationGroup, QPoint, QThread, pyqtSignal, 
    pyqtProperty, QByteArray, QEvent
)
from PyQt6.QtGui import QGuiApplication, QIcon, QAction, QCloseEvent, QShortcut, QKeySequence, QPainter, QColor, QBrush, QLinearGradient, QPixmap, QCursor
from PyQt6.QtSvg import QSvgRenderer
import sys
import os
import logging
import traceback

# Ensure the root directory is in sys.path for imports from root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from event_bus import EventBus
from data_manager import DataManager
from database_manager import DatabaseManager
from plugin_manager import PluginManager
from gui.widgets.timeline_widget import TimelineWidget


class IconCache:
    """Robust icon caching and loading system."""
    _cache = {}
    _icon_cache = {}
    
    @classmethod
    def get_icon(cls, path, size=24):
        """Get icon from cache or load and cache it."""
        cache_key = f"{path}:{size}"
        
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]
        
        icon = cls._load_icon(path, size)
        cls._icon_cache[cache_key] = icon
        return icon
    
    @classmethod
    def _load_icon(cls, path, size=24):
        """Load icon with multiple fallback strategies."""
        try:
            # Strategy 1: Direct QIcon from file
            if path and os.path.exists(path):
                ext = os.path.splitext(path)[1].lower()
                
                if ext in ['.svg']:
                    # SVG: Render to pixmap
                    try:
                        renderer = QSvgRenderer(path)
                        if renderer.isValid():
                            pixmap = QPixmap(size, size)
                            pixmap.fill(Qt.GlobalColor.transparent)
                            painter = QPainter(pixmap)
                            renderer.render(painter)
                            painter.end()
                            icon = QIcon(pixmap)
                            if not icon.isNull():
                                logging.debug(f"Icon loaded successfully: {path}")
                                return icon
                    except Exception as e:
                        logging.warning(f"SVG rendering failed for {path}: {e}")
                
                # Try direct QIcon for PNG/ICO
                try:
                    icon = QIcon(path)
                    if not icon.isNull():
                        logging.debug(f"Icon loaded via QIcon: {path}")
                        return icon
                except Exception as e:
                    logging.warning(f"QIcon loading failed for {path}: {e}")
            
            logging.debug(f"Icon not found or invalid: {path}")
            
        except Exception as e:
            logging.warning(f"Icon loading failed for {path}: {e}")
        
        return QIcon()  # Return empty icon as fallback
from utils import resource_path
from gui.title_bar import CustomTitleBar
from gui.custom_dialogs import ResizeMixin, StyledDialogBase, AlertDialog, UpdateConfirmDialog, UpdateProgressDialog
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
        # Check if icon_char is a valid file path
        is_file = False
        icon_path = None
        if isinstance(self.icon_char, str):
            # Check for file extensions
            if self.icon_char.endswith('.svg') or self.icon_char.endswith('.png') or self.icon_char.endswith('.ico'):
                icon_path = self.icon_char
                is_file = os.path.exists(icon_path)
            # Also check if the path exists (might be full path)
            elif os.path.exists(self.icon_char):
                icon_path = self.icon_char
                is_file = True
        
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
            
            if is_file and icon_path:
                self.setText("")
                icon = IconCache.get_icon(icon_path, 24)
                self.setIcon(icon)
                self.setIconSize(QSize(24, 24))
            else:
                self.setIcon(QIcon())
                self.setText(self.icon_char)
            self.setToolTip(self.original_text)
        else:
            # Restore global styles
            self.setStyleSheet("")
            
            if is_file and icon_path:
                self.setText(f"   {self.original_text}")
                icon = IconCache.get_icon(icon_path, 24)
                self.setIcon(icon)
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

import sys
from async_data_manager import AsyncDataManager
from utils.hotkey_manager import HotkeyManager
from utils.notifications import NotificationManager
from gui.widgets.utility_widgets import InternalMemWorker, InternalTempWorker

class MainWindow(ResizeMixin, QMainWindow):
    def __init__(self, auth_manager=None, data_manager=None):
        super().__init__()
        
        # 1. Initialize Data Manager FIRST (required by other components)
        self.data_manager = data_manager if data_manager else DataManager()
        self.async_dm = AsyncDataManager(self.data_manager)
        
        # Enforce Minimum Size immediately (Requirement 1)
        self.setMinimumSize(900, 720)
        
        # 2. Setup resizing logic for frameless window
        self.setup_resizing()
        is_resizable = self.data_manager.get_setting("window_resizable", True)
        self.set_resizable(is_resizable)
        # Disable background dragging for main window (only title bar allowed)
        self.set_movable(False)
        
        # Enforce Minimum Size (Requirement 1)
        self.setMinimumSize(900, 720)
        
        self.auth_manager = auth_manager
        self._tabs_preloading_done = False
        
        # Initialize Notification Manager early
        self.notification_manager = NotificationManager()
        self.notification_manager.data_manager = self.data_manager # Link for settings access
        
        self.db_manager = DatabaseManager()
        self.event_bus = EventBus.get_instance()
        self.plugin_manager = PluginManager(app_context={"db": self.db_manager, "data": self.data_manager, "event_bus": self.event_bus})
        self.plugin_manager.discover_plugins()
        self.plugin_manager.initialize_plugins()
        self.perf_monitor = PerformanceMonitor(self)
        self.perf_monitor.start_timer()
        
        # 3. Setup Hotkeys (Requirement F7/F8)
        self.hotkey_manager = HotkeyManager()
        self.hotkey_manager.hotkey_triggered.connect(self._on_hotkey_triggered)
        
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
        # Added small margin (2px) to allow ResizeMixin to catch edge events
        self.container_layout.setContentsMargins(2, 2, 2, 2)
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
            "utensils": "🍳",
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
        self.sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
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
        self.sidebar_layout.setContentsMargins(10, 10, 10, 10)
        self.sidebar_layout.setSpacing(6)
        
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
        
        self.sidebar_layout.addSpacing(12)
        
        # Navigation Buttons Container
        self.nav_buttons_layout = QVBoxLayout()
        self.nav_buttons_layout.setSpacing(5)
        self.sidebar_layout.addLayout(self.nav_buttons_layout)
        
        self.sidebar_layout.addStretch() # Push buttons to top
        
        self.main_layout.addWidget(self.sidebar)

        # Main Content Area
        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        
        # Global hotkeys are now initialized earlier in __init__
        
        # Setup App-level Hotkeys (Requirement 2)
        self.setup_app_shortcuts()
        
        # Restore size and position (Requirement 1)
        self.restore_window_geometry()
        
        # Connect hang detection from performance monitor
        self.perf_monitor.hang_detected.connect(self._on_hang_detected)
        
        self.perf_monitor.end_startup()

    def _on_hang_detected(self):
        """Handle detected UI hangs by attempting to notify or log."""
        logging.critical("CRITICAL: UI Thread is hanging for more than 5 seconds!")
        # We can't show a dialog if the thread is hanging, but we can log it
        # for future recovery mechanisms.

    def setup_app_shortcuts(self):
        """Register application-level keyboard shortcuts."""
        # --- Variant A: Guaranteed Qt Shortcuts (Works when window is active) ---
        # F7: Cleaner Interface
        self.shortcut_f7 = QShortcut(QKeySequence("F7"), self)
        self.shortcut_f7.activated.connect(lambda: self.on_global_hotkey("mem_cleanup"))
        
        # F8: Instant Cleanup
        self.shortcut_f8 = QShortcut(QKeySequence("F8"), self)
        self.shortcut_f8.activated.connect(lambda: self.on_global_hotkey("temp_cleanup"))

        # Ctrl+S: Save current profile/data
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.on_save_shortcut)
        
        # Ctrl+R: Refresh data
        self.refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.refresh_shortcut.activated.connect(self.refresh_data)
        
        # Ctrl+Q: Force Quit
        self.quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.quit_shortcut.activated.connect(self.force_quit)
        
        # Ctrl+Tab: Next Tab
        self.next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        self.next_tab_shortcut.activated.connect(self.switch_to_next_tab)
        
        # Ctrl+Shift+Tab: Prev Tab
        self.prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        self.prev_tab_shortcut.activated.connect(self.switch_to_prev_tab)
        
        logging.info("App-level shortcuts registered")

    def on_save_shortcut(self):
        self.data_manager.save_data()
        self.notification_manager.notify("MoneyTracker", "Данные успешно сохранены (Ctrl+S)", level="success")

    def wheelEvent(self, event):
        """Allow tab switching with mouse wheel over the sidebar or main area."""
        # Only switch if Ctrl is pressed to prevent accidental switching while scrolling content
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.switch_to_prev_tab()
            elif delta < 0:
                self.switch_to_next_tab()
            event.accept()
        else:
            super().wheelEvent(event)

    def switch_to_next_tab(self):
        count = self.tabs.count()
        if count <= 1: return
        current = self.tabs.currentIndex()
        next_idx = (current + 1) % count
        # Find next visible tab
        while next_idx != current:
            btn = self.nav_group.button(next_idx)
            if btn and btn.isVisible():
                btn.click()
                break
            next_idx = (next_idx + 1) % count

    def switch_to_prev_tab(self):
        count = self.tabs.count()
        if count <= 1: return
        current = self.tabs.currentIndex()
        prev_idx = (current - 1 + count) % count
        # Find previous visible tab
        while prev_idx != current:
            btn = self.nav_group.button(prev_idx)
            if btn and btn.isVisible():
                btn.click()
                break
            prev_idx = (prev_idx - 1 + count) % count

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

    def closeEvent(self, event):
        """Cleanup before closing."""
        if hasattr(self, 'hotkey_manager'):
            self.hotkey_manager.stop()
        super().closeEvent(event)

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
        """
        Restores the window's size and position from settings.
        
        Enforces a minimum size of 900x720 to prevent interface distortion.
        If no saved geometry is found, applies a default size (90% of screen, max 1300x1000).
        """
        geometry = self.data_manager.get_setting("window_geometry")
        last_screen_index = self.data_manager.get_setting("last_screen_index")
        
        # Enforce Minimum Size immediately
        self.setMinimumSize(900, 720)
        
        screens = QGuiApplication.screens()
        
        if geometry:
            try:
                self.restoreGeometry(bytes.fromhex(geometry))
                
                # Check if we should move to a specific screen
                if last_screen_index is not None and isinstance(last_screen_index, int):
                    if 0 <= last_screen_index < len(screens):
                        target_screen = screens[last_screen_index]
                        if self.screen() != target_screen:
                            geo = self.frameGeometry()
                            geo.moveCenter(target_screen.availableGeometry().center())
                            self.move(geo.topLeft())
            except Exception as e:
                logging.warning(f"Could not restore geometry: {e}")
                self._apply_default_size()
        else:
            self._apply_default_size()

    def _apply_default_size(self):
        """Default size 900x720 as requested."""
        self.resize(900, 720)
        
        # Center on screen
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = self.frameGeometry()
            geo.moveCenter(screen.availableGeometry().center())
            self.move(geo.topLeft())

    def closeEvent(self, event: QCloseEvent):
        logging.info("Application closing...")
        
        try:
            geo = self.saveGeometry().toHex().data().decode()
            self.data_manager.set_setting("window_geometry", geo)
            
            screens = QGuiApplication.screens()
            try:
                current_index = screens.index(self.screen())
                self.data_manager.set_setting("last_screen_index", current_index)
            except Exception as e:
                logging.warning(f"Could not save screen index: {e}")
        except:
            pass

        # Cleanup components
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.hide()
                self.tray_icon.deleteLater()

            if hasattr(self, 'license_timer') and self.license_timer and self.license_timer.isActive():
                self.license_timer.stop()

            if hasattr(self, 'update_manager') and self.update_manager:
                self.update_manager.stop()
                
            if hasattr(self, 'hotkey_manager') and self.hotkey_manager:
                self.hotkey_manager.stop()

            if hasattr(self, 'tabs'):
                for i in range(self.tabs.count()):
                    widget = self.tabs.widget(i)
                    if widget and hasattr(widget, "stop"):
                        try:
                            widget.stop()
                        except:
                            pass
        except Exception as e:
            logging.error(f"Error during closeEvent cleanup: {e}")

        logging.info("Cleanup complete, accepting close event and forcing process exit")
        event.accept()
        # Force terminate process to ensure no background threads hang
        QTimer.singleShot(500, lambda: os._exit(0))

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        
        # Connect tray icon to notification manager
        self.notification_manager.set_tray_icon(self.tray_icon)
        
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
        # Stop everything
        if hasattr(self, 'update_manager') and self.update_manager:
            self.update_manager.stop()
        
        if hasattr(self, 'hotkey_manager') and self.hotkey_manager:
            self.hotkey_manager.stop()
            
        # Call stop on all tabs
        if hasattr(self, 'tabs'):
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                if widget and hasattr(widget, "stop"):
                    try:
                        widget.stop()
                    except:
                        pass

        # Use os._exit for a hard kill if regular quit doesn't work
        # But first try regular exit to allow clean shutdown
        QApplication.quit()
        # Fallback to force exit after a short delay if still running
        QTimer.singleShot(1000, lambda: os._exit(0))

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
        """
        Setup all tabs immediately.
        
        Note: We pre-populate the QStackedWidget with placeholders to maintain fixed indices
        corresponding to the tab_configs. This ensures that even if a tab is loaded later
        (e.g., via background preloading or user click), it appears at the correct index
        and matches the sidebar navigation button ID.
        """
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
        
        # Pre-populate QStackedWidget with placeholders to maintain fixed indices (Fix for Settings tab)
        for _ in range(len(self.tab_configs)):
            self.tabs.addWidget(QWidget())
        
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
        """
        Loads a tab instance by its index in tab_configs.
        
        Args:
            index (int): The index of the tab to load.
            
        This method creates the actual widget instance and replaces the placeholder 
        in the QStackedWidget at the specified index. This maintains a 1:1 mapping 
        between navigation buttons and tab widgets.
        """
        if index in self._tabs_loaded:
            return
        
        if index < 0 or index >= len(self.tab_configs):
            return
        
        tab_class_name, name, icon_name, key = self.tab_configs[index]
        try:
            # Show a brief loading indicator or just process events to keep UI alive
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
            
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
                
                # IMPORTANT: Save current index before replacement to avoid jump
                current_idx = self.tabs.currentIndex()
                
                # Replace the placeholder widget at the fixed index
                old_widget = self.tabs.widget(index)
                self.tabs.insertWidget(index, tab)
                if old_widget:
                    self.tabs.removeWidget(old_widget)
                    old_widget.deleteLater()
                
                # Restore current index if it was affected
                self.tabs.setCurrentIndex(current_idx)
                
                self._tab_instances[index] = tab
                self._tabs_loaded.add(index)
                
                # Apply current theme to new tab
                theme = self.data_manager.get_setting("theme", "dark")
                if hasattr(tab, "apply_theme"):
                    tab.apply_theme(theme)
        except Exception as e:
            logging.error(f"Failed to load tab {name}: {e}\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

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
        
        tab_name = self.tab_configs[index][1] if index < len(self.tab_configs) else "Unknown"
        logging.info(f"Navigation: Switched to tab {tab_name} (index {index})")
        
        current_widget = self.tabs.currentWidget()
        if current_widget and hasattr(current_widget, "refresh_data"):
            current_widget.refresh_data()

    def open_ai_chat(self):
        pass

    def check_license_status(self):
        """Check license status and ban status with the server."""
        if not self.auth_manager:
            return

        try:
            # Lightweight check using check_license_status (which calls validate_key)
            # We enhance this to check for 'banned' status specifically
            is_valid, message, expires_at = self.auth_manager.check_license_status()
            
            if not is_valid:
                # If banned message is in message, or if specifically 403 (needs check in validate_key)
                if "заблокирован" in message.lower() or "banned" in message.lower():
                    logging.critical(f"BANNED: {message}")
                    QMessageBox.critical(self, "Доступ заблокирован", 
                                        f"Ваш аккаунт был заблокирован администратором.\n\nПричина: {message}\n\nПриложение будет закрыто.")
                    QApplication.quit()
                    return

                logging.warning(f"License check failed: {message}")
                # We don't quit immediately for other failures (like offline), 
                # auth_manager handles grace periods.
        except Exception as e:
            logging.error(f"Error during periodic license check: {e}")

    def on_update_available(self, version_info):
        try:
            # Point 3 & 4: Handle Force Update and Optional Update Dialog
            is_forced = version_info.get('force_update', False)
            
            dialog = UpdateConfirmDialog(self, version_info)
            if is_forced:
                # Disable "Later" button for forced updates to block functionality
                if hasattr(dialog, 'btn_no'):
                    dialog.btn_no.setEnabled(False)
                    dialog.btn_no.setToolTip("Это обновление обязательно для продолжения работы.")
                
                # Block until update starts or app closes
                if dialog.exec():
                    self.start_update(version_info)
                else:
                    # If user closes dialog without updating a forced release, exit app
                    logging.info("Forced update rejected, closing application.")
                    self.force_quit()
            else:
                # Regular update - user can choose "Later"
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
        try:
            theme = self.data_manager.get_setting("theme", "dark")
            self.setStyleSheet(StyleManager.get_qss(theme))
            self.title_bar.set_theme(theme) # Ensure title bar branding is applied
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                if widget and hasattr(widget, "apply_theme"):
                    try:
                        widget.apply_theme(theme)
                    except Exception as e:
                        logging.error(f"Failed to apply theme to widget {i}: {e}")
        except Exception as e:
            logging.error(f"Failed to apply styles: {e}")
            # Fallback to default theme
            try:
                self.setStyleSheet(StyleManager.get_qss("dark"))
            except:
                pass

    def open_profiles_dialog(self):
        from gui.profile_dialog import ProfileDialog
        dialog = ProfileDialog(self, self.data_manager)
        if dialog.exec():
            self.refresh_data()

    def refresh_data(self):
        profile = self.data_manager.get_active_profile()
        if profile:
            name = profile.get("name", "Ter") # Default to Ter if name is missing
            self.title_bar.active_profile_label.setText(name)
            self.title_bar.active_profile_label.setVisible(True)
            logging.info(f"UI Refresh: Profile set to '{name}'")
        else:
            self.title_bar.active_profile_label.setText("Ter") # Default profile name
            self.title_bar.active_profile_label.setVisible(True)
            logging.info("UI Refresh: Default profile 'Ter' displayed")
        
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

    def _on_hotkey_triggered(self, action):
        """Handle global hotkey events (F7/F8)."""
        if action == "mem_cleanup": # F7: Instant Background Mem Cleanup
            self._start_background_mem_cleanup()
        elif action == "temp_cleanup": # F8: Instant Background Temp Clean
            self._start_deep_temp_cleanup()

    def _start_background_mem_cleanup(self):
        """F7: Launches Mem Reduct Pro.exe in background."""
        from utils.mem_reduct_launcher import launch_embedded_mem_reduct
        
        self.notification_manager.notify(
            "Mem Reduct Pro", 
            "Запуск Mem Reduct Pro в фоновом режиме...", 
            level="info",
            duration=2
        )
        
        success, msg = launch_embedded_mem_reduct()
        if not success:
            # Fallback to internal cleaner if exe is missing
            logging.warning(f"External Mem Reduct failed: {msg}. Falling back to internal worker.")
            self.mem_worker = InternalMemWorker()
            self.mem_worker.finished_data.connect(self._on_background_mem_finished)
            self.mem_worker.start()
        else:
            logging.info("Mem Reduct Pro.exe launched successfully via F7")

    def _on_background_mem_finished(self, data):
        """Show report after F7 cleanup."""
        if data.get("status") == "success":
            self.notification_manager.notify(
                "Mem Reduct Pro", 
                "Оптимизация памяти завершена успешно!", 
                level="success",
                duration=3
            )
        else:
            self.notification_manager.notify(
                "Mem Reduct Pro", 
                f"Ошибка: {data.get('msg', 'Неизвестно')}", 
                level="error"
            )

    def _activate_window_smart(self):
        """Activates window if hidden/minimized (Manual call)."""
        # Keep this for other uses if needed, but F7 is now background
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.activateWindow()
        self.raise_()

    def _start_deep_temp_cleanup(self):
        """F8: Starts deep cleanup with detailed reporting (Background)."""
        # Notification on start is optional but helpful for UX
        self.notification_manager.notify(
            "Очистка", 
            "Начало фоновой очистки TEMP...", 
            level="info",
            duration=2
        )
        
        # Reuse InternalTempWorker logic
        self.temp_worker = InternalTempWorker()
        self.temp_worker.finished_data.connect(self._on_deep_cleanup_finished)
        self.temp_worker.start()

    def _on_deep_cleanup_finished(self, data):
        """Show report after F8 cleanup."""
        if data.get("status") == "success":
            freed = data.get("freed_mb", 0)
            files = data.get("file_count", 0)
            
            # Format size (MB or GB)
            if freed > 1024:
                size_str = f"{freed/1024:.2f} ГБ"
            else:
                size_str = f"{freed:.2f} МБ"
                
            report = f"TEMP: освобождено {size_str}, файлов: {files}"
            self.notification_manager.notify(
                "Очистка завершена", 
                report, 
                level="success",
                duration=5
            )
        else:
            self.notification_manager.notify(
                "Ошибка очистки", 
                data.get("msg", "Неизвестная ошибка"), 
                level="error"
            )

    def run_instant_mem_cleanup(self):
        """Instant RAM cleanup (Requirement 2 & 3)."""
        self.mem_worker = InternalMemWorker()
        self.mem_worker.finished_data.connect(self._on_instant_mem_finished)
        self.mem_worker.start()

    def _on_instant_mem_finished(self, data):
        if data.get("status") == "success":
            count = data.get("count", 0)
            msg = f"Очистка ОЗУ завершена! Обработано процессов: {count}"
            self.notification_manager.notify("MoneyTracker", msg, level="success")
            logging.info(f"F7 Success: {msg}")
        else:
            err_msg = data.get("msg", "Неизвестная ошибка")
            logging.error(f"F7 Error: {err_msg}")
            self.notification_manager.notify("Ошибка", f"Очистка ОЗУ не удалась: {err_msg}", level="error")

    def run_embedded_mem_reduct(self):
        """Legacy launcher (kept for compatibility)."""
        from utils.mem_reduct_launcher import launch_embedded_mem_reduct
        launch_embedded_mem_reduct()

    def run_silent_temp_cleanup(self):
        """Run TEMP cleanup with feedback (Requirement 3)."""
        self.temp_worker = InternalTempWorker()
        self.temp_worker.finished_data.connect(self._on_silent_temp_finished)
        self.temp_worker.start()

    def _on_silent_temp_finished(self, data):
        if data.get("status") == "success":
            freed = data.get("freed_mb", 0)
            count = data.get("file_count", 0)
            msg = f"Очистка завершена! Удалено {count} файлов, освобождено {freed:.2f} МБ"
            self.notification_manager.notify("MoneyTracker", msg, level="success")
            logging.info(f"F8 Success: {msg}")
        else:
            err_msg = data.get("msg", "Неизвестная ошибка")
            logging.error(f"F8 Error: {err_msg}")
            self.notification_manager.notify("Ошибка", f"Очистка не удалась: {err_msg}", level="error")
