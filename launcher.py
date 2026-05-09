#!/usr/bin/env python3
"""
MoneyTracker Desktop Launcher
Запускает веб-сервер и открывает приложение в браузере
"""
import sys
import os
import webbrowser
import threading
import time
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
if getattr(sys, 'frozen', False):
    # Если запущено как EXE
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Если запущено как скрипт
    BASE_DIR = Path(__file__).parent

sys.path.insert(0, str(BASE_DIR))

def setup_logging():
    """Настройка логирования"""
    log_dir = Path.home() / "MoneyTracker" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "desktop_app.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def check_and_open_url(url, logger, max_retries=30):
    """Проверяет доступность URL и открывает его"""
    import requests
    
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                logger.info(f"Server is ready, opening {url}")
                webbrowser.open(url)
                return True
        except:
            pass
        time.sleep(0.5)
    
    logger.error("Server failed to start")
    return False

def main():
    """Основная функция запуска"""
    logger = setup_logging()
    logger.info("Starting MoneyTracker Desktop Application")
    
    try:
        # Импортируем Flask приложение
        from web import create_app, socketio
        
        app = create_app()
        
        # Порт для веб-сервера
        PORT = 5100
        HOST = '127.0.0.1'
        url = f"http://{HOST}:{PORT}"
        
        logger.info(f"Starting web server on {url}")
        
        # Запускаем проверку и открытие браузера в отдельном потоке
        browser_thread = threading.Thread(
            target=check_and_open_url,
            args=(url, logger),
            daemon=True
        )
        browser_thread.start()
        
        # Запускаем Flask сервер
        # Используем socketio для поддержки WebSocket
        socketio.run(
            app, 
            host=HOST, 
            port=PORT, 
            debug=False,
            allow_unsafe_werkzeug=True,
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Показываем ошибку пользователю
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "MoneyTracker - Error",
                f"Failed to start application:\n\n{str(e)}\n\nCheck logs for details."
            )
            root.destroy()
        except:
            pass
        
        sys.exit(1)

if __name__ == '__main__':
    main()