import os
import sys
import shutil
import tempfile
import subprocess
import logging
import time
from utils.core import resource_path

def launch_embedded_mem_reduct():
    """
    Extracts Mem Reduct Pro.exe from resources or runs mem_reduct_pro.py.
    Ensures no console window is shown.
    """
    try:
        # Priority paths
        current_dir = os.getcwd()
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        possible_sources = [
            os.path.join(root_dir, "Mem Reduct Pro.exe"),
            os.path.join(current_dir, "Mem Reduct Pro.exe"),
            resource_path("Mem Reduct Pro.exe"),
            os.path.join(root_dir, "mem_reduct_pro.py"), # Try the python version
        ]
        
        src_path = None
        for path in possible_sources:
            if os.path.exists(path):
                src_path = path
                break
        
        if not src_path:
            logging.error("Mem Reduct Pro source not found")
            return False, "Программа Mem Reduct Pro не найдена"

        # Determine launch command
        flags = 0
        if os.name == 'nt':
            flags = 0x08000000 | subprocess.CREATE_NEW_PROCESS_GROUP

        if src_path.endswith(".py"):
            # Launch python script
            logging.info(f"Launching Mem Reduct Script: {src_path}")
            # Use pythonw if possible to avoid console
            py_exe = sys.executable
            if py_exe.lower().endswith("python.exe"):
                pyw = py_exe.lower().replace("python.exe", "pythonw.exe")
                if os.path.exists(pyw):
                    py_exe = pyw
            
            subprocess.Popen([py_exe, src_path, "--silent"], 
                             shell=False, 
                             creationflags=flags,
                             cwd=root_dir)
            return True, "Скрипт запущен"
        else:
            # Determine launch path for EXE
            if not getattr(sys, 'frozen', False):
                dest_path = src_path
            else:
                temp_dir = os.path.join(tempfile.gettempdir(), "MoneyTracker_Resources")
                os.makedirs(temp_dir, exist_ok=True)
                dest_path = os.path.join(temp_dir, "Mem Reduct Pro.exe")
                try:
                    shutil.copy2(src_path, dest_path)
                except Exception as e:
                    logging.warning(f"Failed to copy to temp: {e}")
                    if not os.path.exists(dest_path):
                        return False, f"Не удалось извлечь программу: {e}"

            # Launch EXE
            logging.info(f"Launching Mem Reduct EXE: {dest_path}")
            subprocess.Popen([dest_path], 
                             shell=False, 
                             creationflags=flags)
            
            return True, "EXE запущен"

    except Exception as e:
        logging.error(f"Error launching embedded Mem Reduct: {e}")
        return False, str(e)
