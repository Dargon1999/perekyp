
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDateEdit, QPushButton, QFrame, QGridLayout, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
import openpyxl

from gui.styles import StyleManager

class AnalyticsSubTab(QWidget):
    def __init__(self, category_key, category_name, data_manager, parent_analytics_tab=None):
        super().__init__()
        self.category_key = category_key
        self.category_name = category_name
        self.data_manager = data_manager
        self.parent_analytics_tab = parent_analytics_tab # Access to siblings for global total
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        
        self.init_ui()
        # Deferred loading: self.refresh_data() removed from here

    def showEvent(self, event):
        if not self.is_initialized:
            self.refresh_data()
            self.is_initialized = True
        super().showEvent(event)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # --- Controls Area ---
        controls_layout = QHBoxLayout()
        
        # Period Selector
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Недельный вид", "Месячный вид", "Произвольный период"])
        self.period_combo.currentIndexChanged.connect(self.on_period_changed)
        controls_layout.addWidget(self.period_combo)
        
        # Custom Date Range (Hidden by default)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setVisible(False)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setVisible(False)
        
        self.apply_btn = QPushButton("Применить")
        self.apply_btn.setVisible(False)
        self.apply_btn.clicked.connect(self.refresh_data)
        
        controls_layout.addWidget(self.date_from)
        controls_layout.addWidget(self.date_to)
        controls_layout.addWidget(self.apply_btn)
        
        controls_layout.addStretch()
        
        # Export Buttons
        self.btn_export_excel = QPushButton("Excel")
        self.btn_export_excel.clicked.connect(self.export_to_excel)
        controls_layout.addWidget(self.btn_export_excel)
        
        self.btn_export_pdf = QPushButton("PDF") # Placeholder or simple implementation
        self.btn_export_pdf.clicked.connect(self.export_to_pdf)
        controls_layout.addWidget(self.btn_export_pdf)
        
        self.layout.addLayout(controls_layout)

        # --- Scroll Area for Content ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(20)
        scroll.setWidget(self.content_widget)
        self.layout.addWidget(scroll)

        # --- KPI Cards ---
        self.kpi_layout = QHBoxLayout()
        self.content_layout.addLayout(self.kpi_layout)
        
        # --- Charts ---
        self.chart_frame = QFrame()
        self.chart_frame.setMinimumHeight(300)
        self.chart_layout = QVBoxLayout(self.chart_frame)
        self.content_layout.addWidget(self.chart_frame)
        
        # --- Data Table ---
        self.table_label = QLabel("Детализация операций")
        self.table_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.content_layout.addWidget(self.table_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Дата", "Описание", "Сумма", "Тип"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(200)
        self.content_layout.addWidget(self.table)

    def on_period_changed(self):
        mode = self.period_combo.currentText()
        is_custom = mode == "Произвольный период"
        self.date_from.setVisible(is_custom)
        self.date_to.setVisible(is_custom)
        self.apply_btn.setVisible(is_custom)
        
        if not is_custom:
            self.refresh_data()

    def get_date_range(self):
        mode = self.period_combo.currentText()
        today = datetime.now()
        
        if mode == "Недельный вид":
            # Current week Mon-Sun
            start = today - timedelta(days=today.weekday()) # Monday
            end = start + timedelta(days=6) # Sunday (was 4 for Friday)
            return start, end
            
        elif mode == "Месячный вид":
            # Current month
            start = today.replace(day=1)
            # Last day of month
            next_month = today.replace(day=28) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)
            return start, end
            
        else: # Custom
            start = self.date_from.date().toPyDate()
            end = self.date_to.date().toPyDate()
            # Convert to datetime
            return datetime.combine(start, datetime.min.time()), datetime.combine(end, datetime.max.time())

    def _get_all_transactions(self):
        if self.category_key == "all":
            transactions = []
            # 1. Clothes
            inventory = self.data_manager.get_clothes_inventory()
            sold = self.data_manager.get_clothes_sold()
            for item in inventory:
                transactions.append({
                    "date": item.get("date", ""), 
                    "amount": -float(item.get("buy_price", 0)),
                    "description": f"[Покупка / Продажа] Покупка: {item.get('name')}",
                    "raw_date_fmt": "%Y-%m-%d"
                })
            for item in sold:
                transactions.append({
                    "date": item.get("date", ""), 
                    "amount": -float(item.get("buy_price", 0)),
                    "description": f"[Покупка / Продажа] Покупка: {item.get('name')} (Продано)",
                    "raw_date_fmt": "%Y-%m-%d"
                })
                transactions.append({
                    "date": item.get("sell_date", ""), 
                    "amount": float(item.get("sell_price", 0)),
                    "description": f"[Покупка / Продажа] Продажа: {item.get('name')}",
                    "raw_date_fmt": "%Y-%m-%d"
                })
            
            # 2. Other Categories
            for cat in ["car_rental", "mining"]:
                raw_tx = self.data_manager.get_transactions(cat)
                cat_name = "Аренда" if cat == "car_rental" else "Добыча"
                for t in raw_tx:
                    transactions.append({
                        "date": t.get("date", ""),
                        "amount": float(t.get("amount", 0)),
                        "description": f"[{cat_name}] " + (t.get("comment", "") or t.get("description", "")),
                        "raw_date_fmt": "%d.%m.%Y"
                    })
            return transactions

        transactions = []
        if self.category_key == "clothes":
            # Special handling for clothes
            inventory = self.data_manager.get_clothes_inventory()
            sold = self.data_manager.get_clothes_sold()
            
            # Inventory: Only expenses (buy_price)
            for item in inventory:
                transactions.append({
                    "date": item.get("date", ""), # YYYY-MM-DD
                    "amount": -float(item.get("buy_price", 0)),
                    "description": f"Покупка: {item.get('name')}",
                    "raw_date_fmt": "%Y-%m-%d"
                })
                
            # Sold: Expense (buy_price) AND Income (sell_price)
            for item in sold:
                # Buy event
                transactions.append({
                    "date": item.get("date", ""), # YYYY-MM-DD
                    "amount": -float(item.get("buy_price", 0)),
                    "description": f"Покупка: {item.get('name')} (Продано)",
                    "raw_date_fmt": "%Y-%m-%d"
                })
                # Sell event
                transactions.append({
                    "date": item.get("sell_date", ""), # YYYY-MM-DD
                    "amount": float(item.get("sell_price", 0)),
                    "description": f"Продажа: {item.get('name')}",
                    "raw_date_fmt": "%Y-%m-%d"
                })
        else:
            # Standard categories
            raw_tx = self.data_manager.get_transactions(self.category_key)
            for t in raw_tx:
                transactions.append({
                    "date": t.get("date", ""), # DD.MM.YYYY usually
                    "amount": float(t.get("amount", 0)),
                    "description": t.get("comment", "") or t.get("description", ""),
                    "raw_date_fmt": "%d.%m.%Y"
                })
        return transactions

    def refresh_data(self):
        start_date, end_date = self.get_date_range()
        
        all_transactions = self._get_all_transactions()
        
        # Filter by date
        filtered_tx = []
        for t in all_transactions:
            try:
                # Handle formats
                fmt = t.get("raw_date_fmt", "%d.%m.%Y")
                # Fallback check
                if "-" in t['date']: fmt = "%Y-%m-%d"
                elif "." in t['date']: fmt = "%d.%m.%Y"
                
                t_date = datetime.strptime(t['date'], fmt)
                if start_date <= t_date <= end_date:
                    # Normalize date for display
                    t['display_date'] = t_date.strftime("%d.%m.%Y")
                    filtered_tx.append(t)
            except ValueError:
                continue

        # 2. Calculate Stats
        income = sum(t['amount'] for t in filtered_tx if t['amount'] > 0)
        expense = sum(abs(t['amount']) for t in filtered_tx if t['amount'] < 0)
        balance = income - expense
        
        # Previous Period Stats (for comparison)
        delta = end_date - start_date
        prev_start = start_date - delta
        prev_end = start_date - timedelta(days=1)
        
        prev_tx = []
        for t in all_transactions:
             try:
                fmt = t.get("raw_date_fmt", "%d.%m.%Y")
                if "-" in t['date']: fmt = "%Y-%m-%d"
                elif "." in t['date']: fmt = "%d.%m.%Y"
                
                t_date = datetime.strptime(t['date'], fmt)
                if prev_start <= t_date <= prev_end:
                    prev_tx.append(t)
             except: pass
             
        prev_income = sum(t['amount'] for t in prev_tx if t['amount'] > 0)
        prev_expense = sum(abs(t['amount']) for t in prev_tx if t['amount'] < 0)
        
        income_growth = ((income - prev_income) / prev_income * 100) if prev_income else 0
        expense_growth = ((expense - prev_expense) / prev_expense * 100) if prev_expense else 0

        # 3. Update KPI Cards
        self.update_kpi(income, expense, balance, income_growth, expense_growth)
        
        # 4. Update Charts
        self.update_charts(filtered_tx, start_date, end_date)
        
        # 5. Update Table
        self.update_table(filtered_tx)

    def update_kpi(self, income, expense, balance, inc_growth, exp_growth):
        # Clear existing KPIs
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        def create_card(title, value, growth, is_positive_good=True):
            card = QFrame()
            card.setStyleSheet("background-color: #2b2b2b; border-radius: 8px; border: 1px solid #444;")
            l = QVBoxLayout(card)
            
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("color: #aaa; font-size: 12px;")
            l.addWidget(lbl_title)
            
            lbl_val = QLabel(f"${value:,.0f}")
            lbl_val.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
            l.addWidget(lbl_val)
            
            # Growth indicator
            color = "#2ecc71" if (growth >= 0 and is_positive_good) or (growth < 0 and not is_positive_good) else "#e74c3c"
            arrow = "▲" if growth >= 0 else "▼"
            lbl_growth = QLabel(f"{arrow} {abs(growth):.1f}%")
            lbl_growth.setStyleSheet(f"color: {color}; font-size: 11px;")
            l.addWidget(lbl_growth)
            
            return card

        self.kpi_layout.addWidget(create_card("Доход", income, inc_growth, True))
        self.kpi_layout.addWidget(create_card("Расход", expense, exp_growth, False))
        self.kpi_layout.addWidget(create_card("Чистая прибыль", balance, 0, True))
        
        # Global Total (only if Weekly View)
        if self.period_combo.currentText().startswith("Недельный") and self.category_key != "all":
             # Mock global total or calculate if parent available
             
             # If we want GLOBAL total (across all tabs), we need data from other tabs
             if self.parent_analytics_tab:
                 global_bal = self.parent_analytics_tab.get_global_weekly_balance()
                 card = QFrame()
                 card.setStyleSheet("background-color: #3e3e3e; border-radius: 8px; border: 1px solid #666;")
                 l = QVBoxLayout(card)
                 l.addWidget(QLabel("ОБЩИЙ ИТОГ (Все вкладки)"))
                 lbl = QLabel(f"${global_bal:,.0f}")
                 lbl.setStyleSheet("color: #ffd700; font-size: 22px; font-weight: bold;")
                 l.addWidget(lbl)
                 self.kpi_layout.addWidget(card)

    def update_charts(self, transactions, start_date, end_date):
        # Clear previous chart
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        fig = Figure(figsize=(5, 3), dpi=100)
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background-color: transparent;")
        ax = fig.add_subplot(111)
        fig.patch.set_facecolor('#2b2b2b') # Dark bg
        ax.set_facecolor('#2b2b2b')
        
        # Group by date
        dates = []
        incomes = []
        expenses = []
        
        # Create a dict of dates in range
        data_map = {}
        curr = start_date
        while curr <= end_date:
            d_str = curr.strftime("%d.%m")
            data_map[d_str] = {"inc": 0, "exp": 0}
            curr += timedelta(days=1)
            
        for t in transactions:
            try:
                d = datetime.strptime(t['date'], "%d.%m.%Y").strftime("%d.%m")
                if d in data_map:
                    if t['amount'] > 0:
                        data_map[d]["inc"] += t['amount']
                    else:
                        data_map[d]["exp"] += abs(t['amount'])
            except: pass
            
        keys = sorted(data_map.keys())
        inc_vals = [data_map[k]["inc"] for k in keys]
        exp_vals = [data_map[k]["exp"] for k in keys]
        
        x = range(len(keys))
        ax.bar(x, inc_vals, width=0.4, label='Доход', color='#2ecc71', align='center')
        ax.bar(x, exp_vals, width=0.4, label='Расход', color='#e74c3c', align='center', bottom=inc_vals) # Stacked? Or side-by-side? Let's do side by side for clarity
        
        # Side by side
        # ax.clear()
        # width = 0.35
        # ax.bar([i - width/2 for i in x], inc_vals, width, label='Доход', color='#2ecc71')
        # ax.bar([i + width/2 for i in x], exp_vals, width, label='Расход', color='#e74c3c')
        
        ax.set_xticks(x)
        ax.set_xticklabels(keys, rotation=45, color='white')
        ax.tick_params(axis='y', colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('none') 
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('none')
        
        ax.legend(facecolor='#2b2b2b', labelcolor='white')
        fig.tight_layout()
        
        self.chart_layout.addWidget(canvas)

    def update_table(self, transactions):
        self.table.setRowCount(0)
        # Sort by date desc
        try:
            sorted_tx = sorted(transactions, key=lambda x: datetime.strptime(x['date'], "%d.%m.%Y"), reverse=True)
        except:
            sorted_tx = transactions
            
        self.table.setRowCount(len(sorted_tx))
        for i, t in enumerate(sorted_tx):
            self.table.setItem(i, 0, QTableWidgetItem(t.get('date', '')))
            self.table.setItem(i, 1, QTableWidgetItem(t.get('description', '')))
            
            amt = t.get('amount', 0)
            item_amt = QTableWidgetItem(f"${amt:,.0f}")
            if amt > 0:
                item_amt.setForeground(QColor("#2ecc71"))
            else:
                item_amt.setForeground(QColor("#e74c3c"))
            self.table.setItem(i, 2, item_amt)
            
            typ = "Доход" if amt > 0 else "Расход"
            self.table.setItem(i, 3, QTableWidgetItem(typ))

    def export_to_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в Excel", "", "Excel Files (*.xlsx)")
        if not file_path:
            return
            
        if not file_path.endswith('.xlsx'):
            file_path += '.xlsx'
            
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = self.category_name
            
            # Headers
            headers = ["Дата", "Описание", "Сумма", "Тип"]
            ws.append(headers)
            
            start_date, end_date = self.get_date_range()
            transactions = self.data_manager.get_transactions(self.category_key)
            
            for t in transactions:
                try:
                    t_date = datetime.strptime(t['date'], "%d.%m.%Y")
                    if start_date <= t_date <= end_date:
                        row = [
                            t['date'],
                            t['description'],
                            t['amount'],
                            "Доход" if t['amount'] > 0 else "Расход"
                        ]
                        ws.append(row)
                except: continue
                
            wb.save(file_path)
            QMessageBox.information(self, "Успех", "Файл успешно сохранен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {e}")

    def export_to_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в PDF", "", "PDF Files (*.pdf)")
        if not file_path:
            return
            
        if not file_path.endswith('.pdf'):
            file_path += '.pdf'
            
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QTextDocument, QTextCursor, QTextBlockFormat, QTextTableFormat, QTextCharFormat, QColor
            
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            
            doc = QTextDocument()
            cursor = QTextCursor(doc)
            
            # Title
            title_fmt = QTextCharFormat()
            title_fmt.setFontPointSize(20)
            title_fmt.setFontWeight(700) # Bold
            cursor.insertText(f"Отчет: {self.category_name}\n", title_fmt)
            
            start_date, end_date = self.get_date_range()
            cursor.insertText(f"Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n")
            
            # Table
            all_transactions = self._get_all_transactions()
            # Filter again (code duplication, but safer than storing state)
            filtered_tx = []
            for t in all_transactions:
                try:
                    fmt = t.get("raw_date_fmt", "%d.%m.%Y")
                    if "-" in t['date']: fmt = "%Y-%m-%d"
                    elif "." in t['date']: fmt = "%d.%m.%Y"
                    t_date = datetime.strptime(t['date'], fmt)
                    if start_date <= t_date <= end_date:
                        t['display_date'] = t_date.strftime("%d.%m.%Y")
                        filtered_tx.append(t)
                except: continue
                
            sorted_tx = sorted(filtered_tx, key=lambda x: datetime.strptime(x['display_date'], "%d.%m.%Y"), reverse=True)

            table_fmt = QTextTableFormat()
            table_fmt.setHeaderRowCount(1)
            table_fmt.setBorder(1)
            table_fmt.setCellPadding(4)
            table_fmt.setCellSpacing(0)
            table_fmt.setWidth(printer.pageRect(QPrinter.Unit.Point).width())
            
            table = cursor.insertTable(len(sorted_tx) + 1, 4, table_fmt)
            
            # Headers
            headers = ["Дата", "Описание", "Сумма", "Тип"]
            for i, h in enumerate(headers):
                cell = table.cellAt(0, i)
                cursor_cell = cell.firstCursorPosition()
                fmt = QTextCharFormat()
                fmt.setFontWeight(700)
                cursor_cell.insertText(h, fmt)
            
            # Rows
            for row, t in enumerate(sorted_tx):
                # Date
                table.cellAt(row+1, 0).firstCursorPosition().insertText(t.get('display_date', ''))
                # Desc
                table.cellAt(row+1, 1).firstCursorPosition().insertText(t.get('description', ''))
                # Amount
                amt = t.get('amount', 0)
                amt_str = f"${amt:,.0f}"
                cell_amt = table.cellAt(row+1, 2)
                cursor_amt = cell_amt.firstCursorPosition()
                fmt_amt = QTextCharFormat()
                if amt > 0: fmt_amt.setForeground(QColor("#2ecc71")) # Green
                else: fmt_amt.setForeground(QColor("#e74c3c")) # Red
                cursor_amt.insertText(amt_str, fmt_amt)
                # Type
                typ = "Доход" if amt > 0 else "Расход"
                table.cellAt(row+1, 3).firstCursorPosition().insertText(typ)
            
            doc.print(printer)
            QMessageBox.information(self, "Успех", f"PDF успешно сохранен:\n{file_path}")
            
        except ImportError:
            QMessageBox.warning(self, "Ошибка", "Модуль QtPrintSupport не найден. PDF экспорт недоступен.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить PDF: {e}")

