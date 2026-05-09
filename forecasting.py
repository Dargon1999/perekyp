from datetime import datetime, timedelta
import logging

class ForecastingSystem:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def calculate_average_daily_income(self, days=30):
        """Calculates average daily income over the last N days."""
        session = self.db_manager.get_session()
        try:
            from database_manager import Transaction
            from sqlalchemy import func
            
            since = datetime.utcnow() - timedelta(days=days)
            
            # Sum income transactions
            income_sum = session.query(func.sum(Transaction.amount)).filter(
                Transaction.timestamp >= since,
                Transaction.type == 'income',
                Transaction.is_cancelled == False
            ).scalar() or 0.0
            
            return income_sum / days
        except Exception as e:
            logging.error(f"Error calculating average income: {e}")
            return 0.0
        finally:
            session.close()

    def estimate_time_to_goal(self, target_amount, current_balance):
        """Estimates how many days to reach the target amount."""
        avg_income = self.calculate_average_daily_income()
        if avg_income <= 0:
            return float('inf')
        
        remaining = target_amount - current_balance
        if remaining <= 0:
            return 0
            
        return remaining / avg_income
