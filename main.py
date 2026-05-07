import sys
import os
import subprocess
import multiprocessing
import ctypes
import threading
import logging
import traceback

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

from gui.main_window import MainWindow
from auth.login_window import LoginWindow
from gui.styles import StyleManager
from data_manager import DataManager
from utils import resource_path
from version import VERSION, APP_NAME, APP_ID
from startup_manager import StartupManager

def is_admin():
    """Проверка наличия прав администратора."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    """Перезапуск приложения с правами администратора, если их нет."""
    if not is_admin():
        # Вариант B: Глобальный перезапуск через ShellExecuteW
        logging.info("Запрос прав администратора...")
        try:
            # "runas" вызывает диалог UAC
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            if int(ret) > 32:
                sys.exit(0)
        except Exception as e:
            logging.error(f"Ошибка при запросе прав: {e}")

def setup_logging():
    # Production Logging: Only errors and critical info
    log_level = logging.ERROR if not os.environ.get('DEBUG_MODE') else logging.INFO
    
    app_data = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
    log_dir = os.path.join(app_data, "MoneyTracker", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Date-based logging (Requirement 4)
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"app-{date_str}.log")

    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    
    # In production, we might want to skip stdout if it's a windowed app
    if sys.stdout and os.environ.get('DEBUG_MODE'):
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=log_level,
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


def hide_console():
    """Hides the console window if it's visible (Windows only)."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32')
            user32 = ctypes.WinDLL('user32')
            hWnd = kernel32.GetConsoleWindow()
            if hWnd:
                user32.ShowWindow(hWnd, 0) # 0 = SW_HIDE
        except:
            pass

def main():
    # Hide console immediately
    hide_console()
    
    # Setup logging early for debugging
    setup_logging()
    cleanup_update_files()

    # Set App User Model ID (Windows taskbar icon fix)
    try:
        myappid = APP_ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        logging.warning(f"Failed to set AppUserModelID: {e}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Dargon")
    
    # -------------------------------
    # DATA MANAGER (Initialize early for startup checks)
    # -------------------------------
    try:
        data_manager = DataManager()
        logging.info("DataManager initialized early for startup checks")
    except Exception as e:
        logging.error(f"DataManager early initialization error: {e}")
        data_manager = None

    # --- STARTUP CHECKS ---
    startup_mgr = StartupManager(APP_ID)
    
    # 1. Force Admin Check (UAC Request)
    if not startup_mgr.is_running_as_admin():
        logging.info("Requesting admin privileges...")
        if startup_mgr.request_admin_restart():
            sys.exit(0)
        else:
            logging.critical("Failed to acquire admin privileges. Exiting.")
            sys.exit(1)

    # 2. Single Instance Check (MUST be before other operations)
    if not startup_mgr.check_single_instance():
        logging.warning("Another instance is already running. Exiting.")
        # Requirement 2: Explicit error message
        startup_mgr._show_error("Ошибка запуска", "Приложение уже запущено.\nПожалуйста, закройте другие копии программы.")
        sys.exit(0)

    # 3. Register F7 global hotkey for Mem Reduct Pro
    _f7_listener_started = threading.Event()
    def _f7_hotkey_thread():
        try:
            user32 = ctypes.windll.user32
            VK_F7 = 0x76
            WM_HOTKEY = 0x0312
            if user32.RegisterHotKey(None, 1, 0, VK_F7):
                _f7_listener_started.set()
                msg = ctypes.wintypes.MSG()
                while True:
                    if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                        if msg.message == WM_HOTKEY and msg.wParam == 1:
                            import subprocess
                            if getattr(sys, 'frozen', False):
                                # In EXE mode, call bundled mem_reduct.exe
                                exe_path = os.path.join(sys._MEIPASS, "mem_reduct.exe")
                                if os.path.exists(exe_path):
                                    subprocess.Popen(
                                        [exe_path, "--show"],
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL
                                    )
                            else:
                                # In development mode, call .py script
                                hotkey_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mem_reduct_hotkeys.py")
                                if os.path.exists(hotkey_script):
                                    subprocess.Popen(
                                        [sys.executable, hotkey_script, "--show"],
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL
                                    )
                        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
            else:
                _f7_listener_started.set()
        except:
            _f7_listener_started.set()
    
    t = threading.Thread(target=_f7_hotkey_thread, daemon=True)
    t.start()
    _f7_listener_started.wait(timeout=2)

    # 4. Permissions Check
    app_data = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
    money_tracker_dir = os.path.join(app_data, "MoneyTracker")
    logs_dir = os.path.join(money_tracker_dir, "logs")
    
    is_portable = False
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    if os.path.exists(os.path.join(base_dir, "data.json")):
        is_portable = True
        check_dirs = [base_dir]
    else:
        check_dirs = [money_tracker_dir, logs_dir]

    if not startup_mgr.check_write_permissions(check_dirs):
        sys.exit(1)
        
    # 5. Version Integrity
    startup_mgr.validate_version_integrity()
    # ----------------------

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
    font.setPointSize(max(10, font.pointSize()))
    app.setFont(font)

    # -------------------------------
    # DATA MANAGER CHECK
    # -------------------------------
    if not data_manager:
        try:
            data_manager = DataManager()
            logging.info("DataManager initialized (fallback)")
        except Exception as e:
            logging.error(f"DataManager fallback initialization error: {e}")
            data_manager = None

    if data_manager:
        # Check if data exists, if not, offer to load from source
        if not data_manager.data or not data_manager.data.get("profiles"):
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            reply = QMessageBox.question(None, "Данные не найдены", 
                                        "Файл данных не найден или пуст. Хотите указать путь к файлу данных или загрузить из URL?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # Simple interactive choice
                source, ok = QFileDialog.getOpenFileName(None, "Выберите файл data.json", "", "JSON Files (*.json)")
                if ok and source:
                    data_manager.data = data_manager.loader.load_resource("data", source=source)
                    data_manager.filename = source # Update to new path
                    logging.info(f"Data loaded from user-specified source: {source}")

    # -------------------------------
    # AUTH WINDOW
    # -------------------------------
    auth_window = LoginWindow()
    auth_window.setWindowIcon(app_icon)

    result = auth_window.exec()
    if result == LoginWindow.DialogCode.Accepted:
        # -------------------------------
        # MAIN WINDOW (Tray icon is handled inside MainWindow)
        # -------------------------------
        logging.info("Login successful, initializing main window...")
        try:
            # MAIN WINDOW
            window = MainWindow(
                auth_manager=auth_window.auth_manager,
                data_manager=data_manager
            )
            window.setWindowIcon(app_icon)
            window.show()
            logging.info("Main window displayed successfully")
        except Exception as e:
            logging.critical(f"Failed to initialize main window: {e}")
            logging.critical(traceback.format_exc())
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Ошибка запуска", 
                                f"Произошла критическая ошибка при инициализации интерфейса:\n{str(e)}\n\n"
                                "Подробности записаны в app.log")
            sys.exit(1)

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
