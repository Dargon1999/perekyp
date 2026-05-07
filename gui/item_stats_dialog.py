from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QLabel, QAbstractItemView, QFrame, QWidget,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from gui.title_bar import CustomTitleBar
from gui.custom_dialogs import StyledDialogBase
from gui.styles import StyleManager

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value, display_text=None):
        if display_text is None:
            display_text = str(value)
        super().__init__(display_text)
        self.numeric_value = value
        
    def __lt__(self, other):
        if hasattr(other, 'numeric_value'):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)

class ItemStatsDialog(QDialog):
    def __init__(self, parent, data_manager, category="legacy"):
        super().__init__(parent)
        self.data_manager = data_manager
        self.category = category
        
        # Determine theme colors
        self.theme = StyledDialogBase._theme
        t = StyleManager.get_theme(self.theme)
        
        self.bg_color = t['bg_secondary']
        self.border_color = t['border']
        self.table_bg = t['bg_secondary']
        self.table_grid = t['border']
        self.text_color = t['text_main']
        self.header_bg = t['bg_tertiary']
        self.header_text = t['text_main']
        self.input_bg = t['input_bg']
        self.input_border = t['border']
        self.shadow_color = QColor(0, 0, 0, 100) if self.theme == "dark" else QColor(0, 0, 0, 30)
        self.secondary_text = t['text_secondary']
        self.success_color = t['success']
        self.danger_color = t['danger']
        self.neutral_color = t['text_secondary']
        
        # Frameless Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(800, 600)
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Container
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {self.bg_color};
                border-radius: 10px;
                border: 1px solid {self.border_color};
            }}
        """)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(self.shadow_color)
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)
        
        self.layout.addWidget(self.container)
        
        # Container Layout
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        # Title Bar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.title_label.setText("Статистика по предметам/авто")
        self.title_bar.set_theme(self.theme)
        self.title_bar.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        self.container_layout.addWidget(self.title_bar)
        
        # Content
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.container_layout.addWidget(self.content_widget)
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        # Styles
        title_color = "#e67e22" if self.theme == "light" else "#f1c40f"
        
        self.content_widget.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.table_bg};
                gridline-color: {self.table_grid};
                border: none;
                font-size: 14px;
                color: {self.text_color};
                border-radius: 5px;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QLineEdit {{
                background-color: {self.input_bg};
                color: {self.text_color};
                border: 1px solid {self.input_border};
                border-radius: 2px;
            }}
            QHeaderView::section {{
                background-color: {self.header_bg};
                color: {self.header_text};
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }}
            QLabel {{
                font-size: 18px;
                font-weight: bold;
                color: {title_color};
                margin-bottom: 10px;
            }}
        """)

        title = QLabel("Финансовая статистика по предметам")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Название", "Кол-во сделок", "Доход", "Расход", "Чистая прибыль"])
        
        # Resize modes: Name stretches, others fit content
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            # Expand "Кол-во сделок" (index 1) more
            width = 160 if i == 1 else 130
            self.table.setColumnWidth(i, width)
            
        self.table.setSortingEnabled(True)
        # Enable editing for Count column only
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        
        self.table.itemChanged.connect(self.on_item_changed)
        
        self.content_layout.addWidget(self.table)

    def on_item_changed(self, item):
        if item.column() == 1: # Count column
            row = item.row()
            name_item = self.table.item(row, 0)
            if not name_item: return
            name = name_item.text()
            
            try:
                new_count = int(item.text())
                # We need to calculate the offset: offset = new_count - calculated_count_from_transactions
                # But here we don't have the base calculated count handy easily without reloading.
                # However, DataManager.get_item_stats applies the offset.
                # So if we load data, we get (base + old_offset).
                # The user inputs `new_total`.
                # We need `new_offset = new_total - base`.
                # To get `base`, we can subtract `old_offset`.
                
                # Let's get current stats from DM again to find base
                # This is slightly inefficient but safe.
                stats = self.data_manager.get_item_stats(self.category)
                if name in stats:
                    current_total_with_offset = stats[name]["count"]
                    # But we need the offset that was applied to get this.
                    profile = self.data_manager.get_active_profile()
                    old_offset = profile.get("item_stats_offsets", {}).get(self.category, {}).get(name, {}).get("count", 0)
                    
                    base_count = current_total_with_offset - old_offset
                    new_offset = new_count - base_count
                    
                    # Update DM
                    self.data_manager.set_item_stat_offset(self.category, name, new_offset)
                    
                    # Update item data to keep sorting working properly
                    item.setData(Qt.ItemDataRole.DisplayRole, new_count)
            except ValueError:
                # Revert if invalid
                self.load_data()

    def load_data(self):
        self.table.blockSignals(True) # Prevent triggering itemChanged while loading
        stats = self.data_manager.get_item_stats(self.category)
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False) # Disable sorting while inserting to avoid jumps
        
        for name, data in stats.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Name
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Name not editable
            self.table.setItem(row, 0, name_item)
            
            # Count (Editable)
            count_val = data["count"]
            count_item = NumericTableWidgetItem(count_val, str(count_val))
            count_item.setData(Qt.ItemDataRole.DisplayRole, count_val) 
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Make editable
            count_item.setFlags(count_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, count_item)
            
            # Income
            income_val = data["income"]
            income_str = f"{income_val:,.2f}".replace(",", " ")
            income_item = NumericTableWidgetItem(income_val, income_str)
            income_item.setForeground(QColor(self.success_color))
            income_item.setFlags(income_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, income_item)
            
            # Expenses
            expenses_val = data["expenses"]
            expenses_str = f"{expenses_val:,.2f}".replace(",", " ")
            expense_item = NumericTableWidgetItem(expenses_val, expenses_str)
            expense_item.setForeground(QColor(self.danger_color))
            expense_item.setFlags(expense_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, expense_item)
            
            # Profit
            profit_val = data["profit"]
            profit_str = f"{profit_val:,.2f}".replace(",", " ")
            profit_item = NumericTableWidgetItem(profit_val, profit_str)
            profit_item.setFlags(profit_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            if profit_val > 0:
                profit_item.setForeground(QColor(self.success_color))
            elif profit_val < 0:
                profit_item.setForeground(QColor(self.danger_color))
            else:
                profit_item.setForeground(QColor(self.neutral_color))
            
            self.table.setItem(row, 4, profit_item)
            
        self.table.setSortingEnabled(True)
        self.table.blockSignals(False)
