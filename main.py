import sys
import os
import multiprocessing
import ctypes
import threading
import logging

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

from gui.main_window import MainWindow
from auth.login_window import LoginWindow
from gui.styles import StyleManager
from data_manager import DataManager
from utils import resource_path
from version import VERSION, APP_NAME, APP_ID

def setup_logging():
    app_data = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
    log_dir = os.path.join(app_data, "MoneyTracker", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "app.log")

    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    if sys.stdout:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Global Exception Hook
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Suppress traceback for KeyboardInterrupt (Ctrl+C)
            return
        logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


def cleanup_update_files():
    """Removes temporary update files (.bak) from previous updates."""
    try:
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
            bak_file = current_exe + ".bak"
            if os.path.exists(bak_file):
                logging.info(f"Found backup file {bak_file}, attempting to remove...")
                try:
                    os.remove(bak_file)
                    logging.info("Backup file removed successfully.")
                except Exception as e:
                    logging.warning(f"Failed to remove backup file: {e}")
    except Exception as e:
        logging.error(f"Error in cleanup: {e}")


def main():
    setup_logging()
    cleanup_update_files()

    # Set App User Model ID (Windows taskbar icon fix)
    try:
        # Changed ID to force icon cache refresh
        myappid = APP_ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        logging.warning(f"Failed to set AppUserModelID: {e}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Dargon")
    
    # Force taskbar icon refresh
    icon_resource = resource_path("icon.ico")
    logging.info(f"Attempting to load icon from resource_path: {icon_resource}")
    if os.path.exists(icon_resource):
        app.setWindowIcon(QIcon(icon_resource))
    else:
        logging.warning(f"Icon not found at resource_path: {icon_resource}")

    # -------------------------------
    # GLOBAL APPLICATION ICON (FIX)
    # -------------------------------
    app_icon = QIcon()
    
    # Try multiple paths for the icon
    possible_paths = [
        resource_path("icon.ico"),
        resource_path("icon_v2.ico"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon_v2.ico"),
        "icon.ico",
        "icon_v2.ico"
    ]
    
    icon_path = None
    for path in possible_paths:
        logging.info(f"Checking icon path: {path}")
        if os.path.exists(path):
            icon_path = path
            break
            
    if icon_path:
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
        logging.info(f"Icon loaded from: {icon_path}")
    else:
        logging.warning("Icon not found in any standard location")
        # Fallback: Create a colored pixmap as icon if file missing
        from PyQt6.QtGui import QPixmap, QColor
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#3498db"))
        app_icon = QIcon(pixmap)
        app.setWindowIcon(app_icon)

    # -------------------------------
    # GLOBAL STYLE
    # -------------------------------
    app.setStyleSheet(StyleManager.get_qss("dark"))

    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    # -------------------------------
    # PRELOAD DATA MANAGER
    # -------------------------------
    data_manager_container = {}

    def load_data():
        try:
            data_manager_container['instance'] = DataManager()
            logging.info("DataManager loaded")
        except Exception as e:
            logging.error(f"DataManager preload error: {e}")
            data_manager_container['instance'] = None

    loader_thread = threading.Thread(target=load_data, daemon=True)
    loader_thread.start()

    # -------------------------------
    # AUTH WINDOW
    # -------------------------------
    auth_window = LoginWindow()
    auth_window.setWindowIcon(app_icon)

    if auth_window.exec() == LoginWindow.DialogCode.Accepted:
        loader_thread.join()
        data_manager = data_manager_container.get('instance')

        # MAIN WINDOW
        window = MainWindow(
            auth_manager=auth_window.auth_manager,
            data_manager=data_manager
        )
        window.setWindowIcon(app_icon)
        window.show()

        # -------------------------------
        # SYSTEM TRAY ICON
        # -------------------------------
        tray_icon = QSystemTrayIcon(app_icon, app)
        tray_icon.setToolTip("MoneyTracker")
        
        tray_menu = QMenu()
        
        action_show = QAction("Развернуть", tray_menu)
        action_show.triggered.connect(window.showNormal)
        action_show.triggered.connect(window.activateWindow)
        
        action_exit = QAction("Выход", tray_menu)
        action_exit.triggered.connect(app.quit)
        
        tray_menu.addAction(action_show)
        tray_menu.addSeparator()
        tray_menu.addAction(action_exit)
        
        tray_icon.setContextMenu(tray_menu)
        tray_icon.show()
        
        # Optional: Minimize to tray behavior
        # window.closeEvent = lambda event: (event.ignore(), window.hide()) 
        # But user didn't explicitly ask for minimize-to-tray only, just "display in tray".

        # Re-apply AppID (Windows bug workaround)
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        try:
            sys.exit(app.exec())
        except KeyboardInterrupt:
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
