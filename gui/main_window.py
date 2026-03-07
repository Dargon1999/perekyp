from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton, 
    QMessageBox, QFrame, QButtonGroup, QLabel, QApplication, QScrollArea,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint
from PyQt6.QtGui import QGuiApplication, QIcon, QAction, QCloseEvent, QShortcut, QKeySequence
import os
from data_manager import DataManager
from utils import resource_path
from gui.title_bar import CustomTitleBar
from gui.custom_dialogs import StyledDialogBase, AlertDialog, UpdateConfirmDialog, UpdateProgressDialog
from gui.tabs.generic_tab import GenericTab
from gui.tabs.rent_car_tab import RentCarTab
from gui.tabs.buy_sell_tab import BuySellTab
from gui.tabs.settings_tab import SettingsTab
from gui.tabs.mining_tab import MiningTab
from gui.tabs.farm_bp_tab import FarmBPTab
from gui.tabs.memo_tab import MemoTab
from gui.tabs.helper_tab import HelperTab
from gui.tabs.cooking_tab import CookingTab
from gui.tabs.analytics_tab import AnalyticsTab
from gui.tabs.capital_planning_tab import CapitalPlanningTab
from gui.tabs.timers_tab import TimersTab
from gui.tabs.fishing_tab import FishingTab
from gui.styles import StyleManager
from gui.animations import AnimationManager
from gui.update_manager import UpdateManager

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

class MainWindow(QMainWindow):
    def __init__(self, auth_manager=None, data_manager=None):
        super().__init__()
        
        # Сохраняем auth_manager для использования в проверке лицензии
        self.auth_manager = auth_manager
        
        self.data_manager = data_manager if data_manager else DataManager()
        self.update_manager = UpdateManager(self.data_manager, auth_manager=self.auth_manager)
        self.update_manager.update_available.connect(self.on_update_available)

        self.setWindowTitle("MoneyTracker")
        
        # Frameless Window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Set Window Icon explicitly
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
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(10)
        
        # Sidebar Header (Toggle Button)
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
        
        self.main_layout.addWidget(self.content_area)

        # Navigation Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.buttonClicked.connect(self.on_nav_clicked)

        # Progressive Loading Setup
        self.loading_label = QLabel("Загрузка интерфейса...", self.content_area)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 16px; color: #aaa;")
        self.content_area_layout.addWidget(self.loading_label)
        self.tabs.setVisible(False)
        
        # Defer heavy initialization
        QTimer.singleShot(50, self.post_init_setup)

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
        """Handle application close event."""
        # 0. Save geometry
        geo = self.saveGeometry().toHex().data().decode()
        self.data_manager.set_setting("window_geometry", geo)
        
        # Save current screen index
        screens = QGuiApplication.screens()
        try:
            current_index = screens.index(self.screen())
            self.data_manager.set_setting("last_screen_index", current_index)
        except: pass

        # 1. Hide and cleanup Tray Icon
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()

        # 2. Stop License Timer
        if hasattr(self, 'license_timer') and self.license_timer.isActive():
            self.license_timer.stop()

        # 3. Stop Update Manager (Heartbeat & Downloads)
        if self.update_manager:
            self.update_manager.stop()

        # 4. Stop Timers Tab (internal timers)
        if hasattr(self, 'timers_tab') and self.timers_tab:
            self.timers_tab.stop()

        super().closeEvent(event)

        # 5. Force application quit to kill any lingering threads
        QApplication.quit()

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
        
        # Animate Width
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
        
        # Update Buttons
        for btn in self.nav_group.buttons():
            if isinstance(btn, NavButton):
                btn.update_display(self.is_sidebar_collapsed)


    def post_init_setup(self):
        """Deferred initialization of heavy UI components."""
        try:
            self.setup_tabs()
            self.apply_styles()
            self.refresh_data()
            
            # Switch to UI
            self.loading_label.deleteLater()
            self.tabs.setVisible(True)
            
            # Ensure icon is set on the window handle
            icon_path = resource_path("icon_v2.ico")
            if not os.path.exists(icon_path):
                icon_path = resource_path("icon.ico")
                
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                # Also set it on the application instance again to be sure
                QApplication.instance().setWindowIcon(QIcon(icon_path))
            
            # Check for updates and start heartbeat
            self.update_manager.start_heartbeat(interval_ms=30000) # Check every 30 seconds
            
            # License Check Timer — запускаем только если auth_manager передан
            if self.auth_manager:
                self.check_license_status()  # Initial check
                self.license_timer = QTimer(self)
                self.license_timer.timeout.connect(self.check_license_status)
                self.license_timer.start(300000)  # 5 minutes

            # Perform scheduled backup check
            self.data_manager.perform_scheduled_backup()

            # Setup System Tray
            self.setup_tray_icon()
            
        except Exception as e:
            import traceback
            error_msg = f"Critical error during interface loading:\n{str(e)}\n\n{traceback.format_exc()}"
            print(error_msg) # Print to console
            
            # Show Error Dialog
            try:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Ошибка запуска")
                msg.setText("Не удалось загрузить интерфейс.")
                msg.setInformativeText(str(e))
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
            except:
                pass # Fallback if QMessageBox fails
            
            # Force quit to avoid zombie process
            QApplication.quit()

    def setup_tabs(self):
        # Helper to safely add tabs
        def safe_add_tab(tab_class, name, index, icon_name, key):
            try:
                if tab_class == GenericTab:
                    tab = GenericTab(self.data_manager, key, self)
                elif tab_class == SettingsTab:
                    tab = SettingsTab(self.data_manager, self.auth_manager, self)
                else:
                    tab = tab_class(self.data_manager, self)
                
                self.tabs.addWidget(tab)
                self.add_nav_btn(name, index, icon_name, key)
                return tab
            except Exception as e:
                print(f"Failed to load tab {name} ({key}): {e}")
                # Add a placeholder error tab
                error_widget = QWidget()
                layout = QVBoxLayout(error_widget)
                lbl = QLabel(f"Ошибка загрузки вкладки: {name}\n{str(e)}")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("color: red; font-size: 14px;")
                layout.addWidget(lbl)
                self.tabs.addWidget(error_widget)
                self.add_nav_btn(name, index, icon_name, key)
                return None

        self.car_rental_tab = safe_add_tab(GenericTab, "Аренда авто", 0, "car", "car_rental")
        self.clothes_tab = safe_add_tab(BuySellTab, "Покупка / Продажа", 1, "tshirt", "clothes")
        self.mining_tab = safe_add_tab(MiningTab, "Добыча", 2, "hammer", "mining")
        self.farm_bp_tab = safe_add_tab(FarmBPTab, "Фарм BP", 3, "leaf", "farm_bp")
        self.memo_tab = safe_add_tab(MemoTab, "Блокнот", 4, "sticky-note", "memo")
        self.helper_tab = safe_add_tab(HelperTab, "Помощник", 5, "magic", "helper")
        self.cooking_tab = safe_add_tab(CookingTab, "Кулинария", 6, "utensils", "cooking")
        self.analytics_tab = safe_add_tab(AnalyticsTab, "Аналитика", 7, "chart-bar", "analytics")
        self.capital_planning_tab = safe_add_tab(CapitalPlanningTab, "Капитал", 8, "coins", "capital_planning")
        self.timers_tab = safe_add_tab(TimersTab, "Таймер", 9, "clock", "timers")
        self.fishing_tab = safe_add_tab(FishingTab, "Рыбалка", 10, "fish", "fishing")
        self.settings_tab = safe_add_tab(SettingsTab, "Настройки", 11, "cog", "settings")
        
        # Initial visibility update
        self.update_tabs_visibility()


    def add_nav_btn(self, text, index, icon_name, key=None):
        icon_char = self.icon_map.get(icon_name, "?")
        btn = NavButton(text, icon_char, index, self.sidebar)
        if key:
            btn.setProperty("tab_key", key)
        self.nav_buttons_layout.addWidget(btn)
        self.nav_group.addButton(btn, index)

    def update_tabs_visibility(self):
        hidden_tabs = self.data_manager.get_setting("hidden_tabs", [])
        
        for btn in self.nav_group.buttons():
            if not isinstance(btn, NavButton): continue
            key = btn.property("tab_key")
            
            # Settings tab is always visible
            if not key or key == "settings": 
                btn.setVisible(True)
                continue
            
            # Check if key is in hidden_tabs list
            visible = key not in hidden_tabs
            btn.setVisible(visible)
            
            # If current tab is hidden, switch to default
            if not visible and self.tabs.currentIndex() == btn.property("page_index"):
                 # Try to switch to settings
                 self.tabs.setCurrentIndex(10) # Settings

    def on_nav_clicked(self, btn):
        index = self.nav_group.id(btn)
        self.tabs.setCurrentIndex(index)
        
        # Refresh data for the tab
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, "refresh_data"):
            current_widget.refresh_data()

    def open_ai_chat(self):
        # AI Chat is removed as per requirement
        pass

    def check_license_status(self):
        """Check license status and handle expiration."""
        if not self.auth_manager:
            return
            
        try:
            # Assuming check_license returns (bool, str) or similar
            # If auth_manager.check_license() is a blocking network call, 
            # it might be better to run it in a thread, but for now we keep it simple
            # as it was called in __init__ in the original code.
            is_valid, message, expires = self.auth_manager.check_license_status()
            
            if not is_valid:
                self.license_timer.stop()
                dialog = AlertDialog(self, "Лицензия истекла", 
                                   f"Статус лицензии: {message}\nПриложение будет закрыто.")
                dialog.exec()
                QApplication.quit()
        except Exception as e:
            print(f"Error checking license: {e}")

    def on_update_available(self, version_info):
        """Handle update available signal."""
        try:
            dialog = UpdateConfirmDialog(self, version_info)
            if dialog.exec():
                self.start_update(version_info)
        except Exception as e:
            print(f"Error showing update dialog: {e}")

    def start_update(self, version_info):
        """Start the update download and installation."""
        try:
            progress_dialog = UpdateProgressDialog(self)
            progress_dialog.show()
            
            # Connect signals
            # Note: We need to be careful not to connect multiple times if this is called repeatedly
            # But normally update is done once.
            try:
                self.update_manager.update_progress.disconnect()
                self.update_manager.update_finished.disconnect()
                self.update_manager.update_error.disconnect()
            except:
                pass # Signals might not be connected yet
                
            self.update_manager.update_progress.connect(progress_dialog.update_progress)
            self.update_manager.update_status.connect(progress_dialog.set_status)
            self.update_manager.update_finished.connect(progress_dialog.on_finished)
            self.update_manager.update_error.connect(progress_dialog.on_error)
            
            # Connect cancellation
            progress_dialog.rejected.connect(self.update_manager.cancel_download)
            
            # Start download
            download_url = version_info.get('download_url')
            
            # Robust call with fallback
            if hasattr(self.update_manager, 'download_and_install_update'):
                self.update_manager.download_and_install_update(
                    download_url,
                    force_update=version_info.get('force_update', False),
                    notes=version_info.get('notes'),
                    signature=version_info.get('signature')
                )
            else:
                print("Warning: download_and_install_update not found, using perform_update fallback")
                info = {
                    "download_url": download_url,
                    "signature": version_info.get('signature'),
                    "force_update": version_info.get('force_update', False),
                    "notes": version_info.get('notes')
                }
                self.update_manager.perform_update(info)
                
        except Exception as e:
            print(f"Error starting update: {e}")
            AlertDialog(self, "Ошибка обновления", f"Не удалось запустить обновление: {e}").exec()
            
    def apply_styles(self):
        theme = self.data_manager.get_setting("theme", "dark")
        self.setStyleSheet(StyleManager.get_qss(theme))
        
        # Propagate to tabs
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
        # Update Profile Name in Title Bar
        profile = self.data_manager.get_active_profile()
        if profile:
            self.title_bar.active_profile_label.setText(profile["name"])
            self.title_bar.active_profile_label.setVisible(True)
        else:
            self.title_bar.active_profile_label.setText("Профиль не выбран")
            self.title_bar.active_profile_label.setVisible(True)
        
        # Refresh current tab
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, "refresh_data"):
            current_widget.refresh_data()
