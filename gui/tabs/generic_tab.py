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
        
        # Connect to data_changed signal for instant updates
        self.data_manager.data_changed.connect(self.refresh_data)
        
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

        self.export_btn = QPushButton("📥 Экспорт")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setToolTip("Экспорт в Excel/CSV")
        
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        export_menu = QMenu(self)
        excel_act = QAction("Excel (.xlsx)", self)
        csv_act = QAction("CSV (.csv)", self)
        
        excel_act.triggered.connect(self.export_to_excel)
        csv_act.triggered.connect(self.export_to_csv)
        
        export_menu.addAction(excel_act)
        export_menu.addAction(csv_act)
        self.export_btn.setMenu(export_menu)

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
        
        # Connect Double Click for manual balance edit
        self.stat_balance.value_label.installEventFilter(self)

    def eventFilter(self, obj, event):
        if hasattr(self, 'stat_balance') and obj == self.stat_balance.value_label:
            if event.type() == event.Type.MouseButtonDblClick:
                allow_edit = self.data_manager.get_setting("allowManualBalanceEdit", False)
                if allow_edit:
                    self.start_inline_balance_edit()
                    return True
        return super().eventFilter(obj, event)

    def start_inline_balance_edit(self):
        # Create inline editor
        self.balance_editor = QLineEdit(self.stat_balance)
        
        # Validation: Number with 2 decimals, negative allowed
        from PyQt6.QtGui import QDoubleValidator
        validator = QDoubleValidator(-1000000000.0, 1000000000.0, 2, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.balance_editor.setValidator(validator)
        
        # Style
        t = StyleManager.get_theme(self.current_theme)
        self.balance_editor.setStyleSheet(f"""
            background-color: {t['input_bg']};
            color: {t['text_main']};
            border: 1px solid {t['accent']};
            border-radius: 4px;
            font-size: 18px;
            font-weight: bold;
        """)
        
        # Set current value
        current_val = self.data_manager.get_total_capital_balance()["liquid_cash"]
        self.balance_editor.setText(f"{current_val:.2f}")
        
        # Position and size - Ensure it's wide enough
        geo = self.stat_balance.value_label.geometry()
        geo.setWidth(max(geo.width(), 150))
        self.balance_editor.setGeometry(geo)
        self.balance_editor.show()
        self.balance_editor.setFocus()
        self.balance_editor.selectAll()
        
        # Accessibility
        self.balance_editor.setAccessibleName("Редактирование баланса")
        
        # Connect signals
        self.balance_editor.returnPressed.connect(self.finish_inline_balance_edit)
        self.balance_editor.editingFinished.connect(self.finish_inline_balance_edit)

    def finish_inline_balance_edit(self):
        if not hasattr(self, 'balance_editor') or not self.balance_editor:
            return
            
        try:
            new_val_str = self.balance_editor.text().replace(",", ".")
            if not new_val_str: return
            
            new_val = float(new_val_str)
            self.update_balance_via_api(new_val)
        except ValueError:
            pass
        finally:
            if hasattr(self, 'balance_editor') and self.balance_editor:
                self.balance_editor.deleteLater()
                self.balance_editor = None

    def update_balance_via_api(self, new_val):
        profile = self.data_manager.get_active_profile()
        if not profile: return
        
        # Logic to adjust starting_amount so that total liquid_cash equals new_val
        current_profits = 0.0
        for cat in ["car_rental", "mining", "farm_bp", "fishing", "clothes", "clothes_new", "cars_trade"]:
            stats = self.data_manager.get_category_stats(cat)
            if stats:
                current_profits += stats.get("pure_profit", 0.0)
        
        new_starting = new_val - current_profits
        profile["starting_amount"] = new_starting
        self.data_manager.save_data()
        
        self.data_manager.data_changed.emit()
        # No message box for inline edit, just refresh
        # QMessageBox.information(self, "Успех", f"Баланс обновлен до ${new_val:,.2f}")

    def create_stat_card(self, title, value, color=None):
        frame = QFrame()
        frame.setObjectName("StatCard")
        t = StyleManager.get_theme(self.current_theme)
        
        # Determine background color for special cards
        bg_color = t['bg_secondary']
        
        frame.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {bg_color};
                border: 1px solid {t['border']};
                border-radius: 12px;
                min-width: 220px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {t['text_secondary']}; font-size: 13px; font-weight: 600;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        val_color = color if color else t['text_main']
        value_label.setStyleSheet(f"color: {val_color}; font-size: 22px; font-weight: 800;")
        value_label.setWordWrap(False) # Prevent wrapping
        layout.addWidget(value_label)
        
        # Attach labels to frame for access
        frame.title_label = title_label
        frame.value_label = value_label
        
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

    def export_to_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            
            # Using data_manager's existing method if it has one, or implement here
            try:
                import pandas as pd
                txs = self.data_manager.get_transactions(self.category)
                df = pd.DataFrame(txs)
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "Успех", f"Данные успешно экспортированы в\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать данные: {e}")

    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в CSV", "", "CSV Files (*.csv)")
        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'
            
            try:
                import csv
                txs = self.data_manager.get_transactions(self.category)
                if not txs: return
                
                keys = txs[0].keys()
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    dict_writer = csv.DictWriter(f, fieldnames=keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(txs)
                
                QMessageBox.information(self, "Успех", f"Данные успешно экспортированы в\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать данные: {e}")

    def refresh_data(self):
        t = StyleManager.get_theme(self.current_theme)
        stats = self.data_manager.get_category_stats(self.category)
        if not stats: return

        # Update Balance Stats
        # self.stat_start.value_label.setText(f"${stats.get('starting_amount', 0):,.0f}") # Removed
        balances = self.data_manager.get_total_capital_balance()
        # Use 2 decimals for balance display as per requirements
        self.stat_balance.value_label.setText(f"${balances['liquid_cash']:,.2f}")

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

