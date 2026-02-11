from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame, QComboBox,
    QDateEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer
from PyQt6.QtGui import QColor
from datetime import datetime, timedelta
from gui.styles import StyleManager

class GenericTab(QWidget):
    def __init__(self, data_manager, category, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.category = category
        self.main_window = main_window # Reference to main window for dialogs
        self.current_theme = "dark"
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        self.setup_header()
        self.setup_stats()
        self.setup_table()
        self.setup_footer()
        
        # 4. Footer Add Button
        t = StyleManager.get_theme(self.current_theme)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['success']};
                border: 1px solid {t['success']};
                font-size: 18px;
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t['success']}1A;
            }}
        """)
        
        self.is_initialized = False

    def showEvent(self, event):
        if not self.is_initialized:
            self.refresh_data()
            self.is_initialized = True
        super().showEvent(event)

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        t = StyleManager.get_theme(theme_name)
        
        combo_bg = t["input_bg"]
        combo_border = t["border"]
        combo_text = t["text_main"]
        btn_border = t["border"]
        btn_text = t["text_main"]
        
        card_bg = t["bg_secondary"]
        card_title = t["text_secondary"]
        card_border = f"1px solid {t['border']}"
        
        table_bg = t["bg_secondary"]
        table_grid = t["border"]
        table_text = t["text_main"]
        header_bg = t["bg_tertiary"]
        header_text = t["text_main"]

        # 1. Header
        self.filter_combo.setStyleSheet(f"""
            padding: 8px;
            border-radius: 5px;
            border: 1px solid {combo_border};
            background-color: {combo_bg};
            color: {combo_text};
            min-width: 150px;
        """)
        
        self.stats_btn.setStyleSheet(f"""
            background-color: transparent; 
            border: 1px solid {btn_border}; 
            font-size: 14px;
            padding: 8px;
            color: {btn_text};
        """)
        self.export_btn.setStyleSheet(f"""
            background-color: transparent; 
            border: 1px solid {btn_border}; 
            font-size: 14px;
            padding: 8px;
            color: {btn_text};
        """)

        self.apply_filter_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['success']};
                border: 1px solid {t['success']};
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t['success']}1A;
            }}
        """)

        # 2. Stat Cards
        for card in [self.stat_start, self.stat_income, self.stat_expense, self.stat_profit, self.stat_balance]:
            card.setStyleSheet(f"""
                QFrame#StatCard {{
                    background-color: {card_bg};
                    border-radius: 10px;
                    padding: 15px;
                    border: {card_border};
                }}
            """)
            # Find title label (first child)
            card.layout().itemAt(0).widget().setStyleSheet(f"color: {card_title}; font-size: 12px;")

        # 3. Table
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {table_bg};
                gridline-color: {table_grid};
                border: none;
                font-size: 14px;
                color: {table_text};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_text};
                padding: 5px;
                border: none;
                font-weight: bold;
            }}
        """)

        # 4. Footer Add Button
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['success']};
                border: 1px solid {t['success']};
                font-size: 18px;
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t['success']}1A;
            }}
        """)
        
        # Deferred loading: data will be loaded in showEvent
        # self.refresh_data()

    def setup_header(self):
        self.header_layout = QHBoxLayout()
        
        # Filter ComboBox
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["За все время", "За сегодня", "За неделю", "За месяц", "Выбрать период"])
        # Styles applied in apply_theme
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)

        # Custom Date Range Widgets (Initially Hidden)
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("dd.MM.yyyy")
        self.date_start.setDate(QDate.currentDate().addDays(-7))
        self.date_start.setVisible(False)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("dd.MM.yyyy")
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setVisible(False)

        self.apply_filter_btn = QPushButton("Применить")
        self.apply_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_filter_btn.setVisible(False)
        self.apply_filter_btn.clicked.connect(self.apply_custom_filter)

        # Stats Button
        self.stats_btn = QPushButton("📊 Статистика по предметам")
        # Styles applied in apply_theme
        self.stats_btn.clicked.connect(self.open_item_stats_dialog)

        self.export_btn = QPushButton("📥 Excel")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setToolTip("Экспорт в Excel")
        self.export_btn.clicked.connect(self.export_data)

        self.header_layout.addWidget(self.filter_combo)
        self.header_layout.addWidget(self.date_start)
        self.header_layout.addWidget(self.date_end)
        self.header_layout.addWidget(self.apply_filter_btn)
        self.header_layout.addWidget(self.stats_btn)
        self.header_layout.addWidget(self.export_btn)
        self.header_layout.addStretch()
        
        self.layout.addLayout(self.header_layout)

    def on_filter_changed(self):
        is_custom = self.filter_combo.currentText() == "Выбрать период"
        self.date_start.setVisible(is_custom)
        self.date_end.setVisible(is_custom)
        self.apply_filter_btn.setVisible(is_custom)
        
        if not is_custom:
            self.refresh_data()
        else:
            # Load last used custom period if available
            history = self.data_manager.get_filter_history(self.category)
            if history:
                last = history[0]
                try:
                    # Try new format first
                    try:
                        s = datetime.strptime(last["start_date"], "%d.%m.%Y").date()
                        e = datetime.strptime(last["end_date"], "%d.%m.%Y").date()
                    except ValueError:
                        # Fallback to old format
                        s = datetime.strptime(last["start_date"], "%Y-%m-%d").date()
                        e = datetime.strptime(last["end_date"], "%Y-%m-%d").date()
                        
                    self.date_start.setDate(s)
                    self.date_end.setDate(e)
                except:
                    pass

    def apply_custom_filter(self):
        start_date = self.date_start.date().toPyDate()
        end_date = self.date_end.date().toPyDate()
        
        if end_date < start_date:
            QMessageBox.warning(self, "Ошибка", "Конечная дата не может быть раньше начальной!")
            return
            
        # Save to history
        self.data_manager.save_filter_history(
            self.category, 
            start_date.strftime("%d.%m.%Y"), 
            end_date.strftime("%d.%m.%Y")
        )
        
        # Visual feedback
        self.apply_filter_btn.setText("✓ Применено")
        QTimer.singleShot(2000, lambda: self.apply_filter_btn.setText("Применить"))
        
        self.refresh_data()

    def setup_stats(self):
        stats_layout = QHBoxLayout()
        
        self.stat_start = self.create_stat_card("Стартовый капитал", "$0")
        self.stat_income = self.create_stat_card("Доход (фильтр)", "$0", "#2ecc71")
        self.stat_expense = self.create_stat_card("Расход (фильтр)", "$0", "#e74c3c")
        self.stat_profit = self.create_stat_card("Прибыль (фильтр)", "$0", "#f1c40f")
        self.stat_balance = self.create_stat_card("Текущий баланс", "$0", "#3498db")

        stats_layout.addWidget(self.stat_start)
        stats_layout.addWidget(self.stat_income)
        stats_layout.addWidget(self.stat_expense)
        stats_layout.addWidget(self.stat_profit)
        stats_layout.addWidget(self.stat_balance)
        
        self.layout.addLayout(stats_layout)

    def create_stat_card(self, title, value, color="#ffffff"):
        frame = QFrame()
        frame.setObjectName("StatCard")
        # Styles applied in apply_theme
        
        layout = QVBoxLayout(frame)
        
        title_lbl = QLabel(title)
        # Styles applied in apply_theme
        
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold; margin-top: 5px;")
        
        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        
        frame.value_label = value_lbl
        return frame

    def setup_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Сумма", "Товар/Авто", "Примечание", "Дата", "Действия"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 120)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)
        
        # Styles applied in apply_theme

        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        self.layout.addWidget(self.table)

    def setup_footer(self):
        footer_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("+ Добавить операцию")
        # Styles applied in apply_theme
        self.add_btn.clicked.connect(self.open_add_transaction_dialog)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.add_btn)
        footer_layout.addStretch()
        
        self.layout.addLayout(footer_layout)

    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            
            success = self.data_manager.export_to_excel(self.category, file_path)
            if success:
                QMessageBox.information(self, "Успех", f"Данные успешно экспортированы в\n{file_path}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать данные")

    def refresh_data(self):
        t = StyleManager.get_theme(self.current_theme)
        stats = self.data_manager.get_category_stats(self.category)
        if not stats: return

        # Update Balance Stats
        self.stat_start.value_label.setText(f"${stats['starting_amount']:,.0f}")
        self.stat_balance.value_label.setText(f"${stats['current_balance']:,.0f}")

        # Filter Logic
        filter_mode = self.filter_combo.currentText()
        filtered_transactions = []
        transactions = self.data_manager.get_transactions(self.category)
        
        today = datetime.now().date()
        
        for t_trans in transactions:
            t_date = None
            date_str = t_trans.get("date", "")
            
            try:
                # Try new format first
                t_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            except ValueError:
                try:
                    # Try old format
                    t_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    # Date is missing or invalid
                    if filter_mode == "За все время":
                        filtered_transactions.append(t_trans)
                    continue
                
            include = False
            if filter_mode == "За все время":
                include = True
            elif filter_mode == "За сегодня":
                if t_date == today:
                    include = True
            elif filter_mode == "За неделю":
                start_week = today - timedelta(days=today.weekday())
                if start_week <= t_date <= today:
                    include = True
            elif filter_mode == "За месяц":
                if t_date.year == today.year and t_date.month == today.month:
                    include = True
            elif filter_mode == "Выбрать период":
                start_date = self.date_start.date().toPyDate()
                end_date = self.date_end.date().toPyDate()
                if start_date <= t_date <= end_date:
                    include = True
            
            if include:
                filtered_transactions.append(t_trans)

        # Calculate Filtered Stats
        income = sum(t_trans["amount"] for t_trans in filtered_transactions if t_trans["amount"] > 0)
        expenses = sum(abs(t_trans["amount"]) for t_trans in filtered_transactions if t_trans["amount"] < 0)
        profit = income - expenses
        
        self.stat_income.value_label.setText(f"+${income:,.0f}")
        self.stat_expense.value_label.setText(f"-${expenses:,.0f}")
        
        profit_color = t['success'] if profit >= 0 else t['danger']
        profit_sign = "+" if profit >= 0 else ""
        self.stat_profit.value_label.setText(f"{profit_sign}${profit:,.0f}")
        self.stat_profit.value_label.setStyleSheet(f"color: {profit_color}; font-size: 18px; font-weight: bold; margin-top: 5px;")

        # Update Table
        self.table.setRowCount(len(filtered_transactions))
        for row, t_trans in enumerate(filtered_transactions):
            amount_item = QTableWidgetItem(f"${t_trans['amount']:,.0f}")
            # Store ID for editing
            amount_item.setData(Qt.ItemDataRole.UserRole, t_trans["id"])
            
            if t_trans['amount'] > 0:
                amount_item.setForeground(QColor(t['success']))
            else:
                amount_item.setForeground(QColor(t['danger']))
            
            self.table.setItem(row, 0, amount_item)
            item_name = t_trans.get("item_name", "")
            if t_trans.get("image_path"):
                item_name += " 📷"
            self.table.setItem(row, 1, QTableWidgetItem(item_name))
            self.table.setItem(row, 2, QTableWidgetItem(t_trans.get("comment", "")))
            self.table.setItem(row, 3, QTableWidgetItem(t_trans.get("date", "")))
            
            # Edit Button
            edit_btn = QPushButton("✎")
            edit_btn.setToolTip("Редактировать")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {t['accent']};
                    border: none;
                    font-size: 18px;
                    padding: 4px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {t['accent']}1A;
                    color: {t['accent']};
                }}
                QPushButton:pressed {{
                    background-color: {t['accent']}33;
                    color: {t['accent']};
                }}
            """)
            edit_btn.clicked.connect(lambda checked, r=row: self.on_table_double_click(r, 0))

            # Delete Button
            del_btn = QPushButton("✕")
            del_btn.setToolTip("Удалить")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {t['danger']};
                    border: none;
                    font-size: 18px;
                    padding: 4px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {t['danger']}1A;
                    color: {t['danger']};
                }}
                QPushButton:pressed {{
                    background-color: {t['danger']}33;
                    color: {t['danger']};
                }}
            """)
            del_btn.clicked.connect(lambda checked, tid=t_trans["id"]: self.delete_transaction(tid))
            
            # Ensure background consistency for the cell
            self.table.setItem(row, 4, QTableWidgetItem(""))
            
            cell_widget = QWidget()
            cell_widget.setStyleSheet("background-color: transparent;")
            layout = QHBoxLayout(cell_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            layout.addWidget(edit_btn)
            layout.addWidget(del_btn)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 4, cell_widget)

    def delete_transaction(self, transaction_id):
        if self.data_manager.delete_transaction(self.category, transaction_id):
            self.refresh_data()

    def open_add_transaction_dialog(self):
        try:
            # We need to import TransactionDialog here or pass it in
            # Ideally, we reuse the existing TransactionDialog but update it to accept category
            from gui.transaction_dialog import TransactionDialog
            dialog = TransactionDialog(self.main_window, self.data_manager, self.category)
            if dialog.exec():
                self.refresh_data()
        except Exception as e:
            import traceback
            error_msg = f"Ошибка при открытии окна добавления операции:\n{str(e)}\n\n{traceback.format_exc()}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def on_table_double_click(self, row, column):
        # Get transaction ID from the first column item
        item = self.table.item(row, 0)
        if not item: return
        
        transaction_id = item.data(Qt.ItemDataRole.UserRole)
        if not transaction_id: return
        
        # Find transaction data
        transactions = self.data_manager.get_transactions(self.category)
        transaction = next((t for t in transactions if t["id"] == transaction_id), None)
        
        if transaction:
            from gui.transaction_dialog import TransactionDialog
            dialog = TransactionDialog(self.main_window, self.data_manager, self.category, transaction)
            if dialog.exec():
                self.refresh_data()

    def open_item_stats_dialog(self):
        from gui.item_stats_dialog import ItemStatsDialog
        dialog = ItemStatsDialog(self.main_window, self.data_manager, self.category)
        dialog.exec()

    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            
            success = self.data_manager.export_to_excel(self.category, file_path)
            if success:
                QMessageBox.information(self, "Успех", f"Данные успешно экспортированы в\n{file_path}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать данные")
