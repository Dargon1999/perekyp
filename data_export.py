import csv
import json
import logging
import os
from datetime import datetime

class DataExportSystem:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def export_to_csv(self, file_path):
        """Exports all transactions to a CSV file."""
        from database_manager import Transaction
        session = self.db_manager.get_session()
        try:
            transactions = session.query(Transaction).all()
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Timestamp", "Type", "Module", "Amount", "Category", "Note", "Cancelled"])
                for tx in transactions:
                    writer.writerow([
                        tx.id, 
                        tx.timestamp.strftime("%Y-%m-%d %H:%M:%S"), 
                        tx.type, 
                        tx.module, 
                        tx.amount, 
                        tx.category, 
                        tx.note, 
                        tx.is_cancelled
                    ])
            return True
        except Exception as e:
            logging.error(f"Failed to export CSV: {e}")
            return False
        finally:
            session.close()

    def export_to_json(self, file_path):
        """Exports all transactions to a JSON file."""
        from database_manager import Transaction
        session = self.db_manager.get_session()
        try:
            transactions = session.query(Transaction).all()
            data = []
            for tx in transactions:
                data.append({
                    "id": tx.id,
                    "timestamp": tx.timestamp.isoformat(),
                    "type": tx.type,
                    "module": tx.module,
                    "amount": tx.amount,
                    "category": tx.category,
                    "note": tx.note,
                    "is_cancelled": tx.is_cancelled
                })
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Failed to export JSON: {e}")
            return False
        finally:
            session.close()

    def export_to_excel(self, file_path):
        """Exports all transactions to an Excel file (requires pandas and openpyxl)."""
        try:
            import pandas as pd
            from database_manager import Transaction
            session = self.db_manager.get_session()
            transactions = session.query(Transaction).all()
            df = pd.DataFrame([{
                "ID": tx.id,
                "Timestamp": tx.timestamp,
                "Type": tx.type,
                "Module": tx.module,
                "Amount": tx.amount,
                "Category": tx.category,
                "Note": tx.note,
                "Cancelled": tx.is_cancelled
            } for tx in transactions])
            df.to_excel(file_path, index=False)
            return True
        except ImportError:
            logging.error("pandas or openpyxl not installed for Excel export.")
            return False
        except Exception as e:
            logging.error(f"Failed to export Excel: {e}")
            return False
        finally:
            if 'session' in locals(): session.close()
