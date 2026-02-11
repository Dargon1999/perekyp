from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import Qt
from gui.tabs.analytics_sub_tab import AnalyticsSubTab
from gui.tabs.achievements_tab import AchievementsTab
from datetime import datetime, timedelta
import logging

class AnalyticsTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Main Tab Widget
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # Create Sub-tabs
        self.tab_overview = AnalyticsSubTab("all", "Обзор", self.data_manager, self)
        self.tab_rent = AnalyticsSubTab("car_rental", "Аренда авто", self.data_manager, self)
        self.tab_clothes = AnalyticsSubTab("clothes", "Покупка / Продажа", self.data_manager, self)
        self.tab_mining = AnalyticsSubTab("mining", "Добыча", self.data_manager, self)
        self.tab_achievements = AchievementsTab(self.data_manager, self)
        
        self.tabs.addTab(self.tab_overview, "Обзор")
        self.tabs.addTab(self.tab_rent, "Аренда авто")
        self.tabs.addTab(self.tab_clothes, "Покупка / Продажа")
        self.tabs.addTab(self.tab_mining, "Добыча")
        self.tabs.addTab(self.tab_achievements, "Достижения")
        
        # Style the tab bar slightly if needed
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 150px;
                padding: 10px;
                font-size: 14px;
            }
        """)

    def get_global_weekly_balance(self):
        """Calculates total balance for the current week (Mon-Sun) across all categories."""
        # Use the logic from the overview tab to avoid duplication
        transactions = self.tab_overview._get_all_transactions()
        
        today = datetime.now()
        start_date = today - timedelta(days=today.weekday()) # Monday
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=6) # Sunday (was 4)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        total_balance = 0
        
        for t in transactions:
            try:
                fmt = t.get("raw_date_fmt", "%d.%m.%Y")
                if "-" in t['date']: fmt = "%Y-%m-%d"
                elif "." in t['date']: fmt = "%d.%m.%Y"
                
                t_date = datetime.strptime(t['date'], fmt)
                if start_date <= t_date <= end_date:
                    total_balance += t['amount']
            except: continue
            
        return total_balance

    def refresh_data(self):
        """Refreshes data in the current sub-tab and marks others for update."""
        current_index = self.tabs.currentIndex()
        for i in range(self.tabs.count()):
            page = self.tabs.widget(i)
            if i == current_index:
                if hasattr(page, 'refresh_data'):
                    page.refresh_data()
                if hasattr(page, 'is_initialized'):
                    page.is_initialized = True
            else:
                # Mark as needing update
                if hasattr(page, 'is_initialized'):
                    page.is_initialized = False
