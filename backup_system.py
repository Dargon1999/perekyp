import os
import shutil
import sqlite3
import logging
from datetime import datetime

class BackupSystem:
    def __init__(self, db_path="data.db", backup_dir="backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self):
        if not os.path.exists(self.db_path):
            logging.warning(f"Database file {self.db_path} not found for backup.")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        try:
            with sqlite3.connect(self.db_path) as src, sqlite3.connect(backup_path) as dst:
                src.backup(dst)
            
            logging.info(f"Database backup created: {backup_path}")
            self.cleanup_old_backups(keep=30)
            return backup_path
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            return None

    def cleanup_old_backups(self, keep=30):
        try:
            backups = sorted([
                os.path.join(self.backup_dir, f) 
                for f in os.listdir(self.backup_dir) 
                if f.endswith(".db") and os.path.isfile(os.path.join(self.backup_dir, f))
            ], key=os.path.getmtime)
            
            if len(backups) > keep:
                for b in backups[:-keep]:
                    try:
                        os.remove(b)
                        logging.info(f"Removed old backup: {b}")
                    except OSError as e:
                        logging.warning(f"Failed to remove backup {b}: {e}")
        except Exception as e:
            logging.error(f"Error cleaning up backups: {e}")
