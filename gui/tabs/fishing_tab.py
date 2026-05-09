from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QButtonGroup, QPushButton, 
    QStackedWidget, QLabel, QComboBox, QGridLayout, QScrollArea, QTableWidget, 
    QTableWidgetItem, QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, 
    QHeaderView, QMessageBox, QFileDialog, QToolTip, QCheckBox, QDialog, QAbstractItemView,
    QRadioButton, QGraphicsDropShadowEffect
)
import random
import traceback
import re
from PyQt6.QtCore import Qt, QTimer, QSize, QRect, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt6.QtGui import QColor, QPainter, QAction, QKeySequence, QIcon, QFontMetrics, QBrush, QPen, QMouseEvent, QFont
from gui.styles import StyleManager
from gui.animations import AnimationManager
from gui.tabs.generic_tab import GenericTab
from gui.widgets.calculator_widget import CalculatorWidget

class ComparisonOverlay(QDialog):
    def __init__(self, items, data_manager, theme, parent=None):
        super().__init__(parent)
        self.items = items
        self.data_manager = data_manager
        self.current_theme = theme
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # For dragging
        self._drag_pos = QPoint()
        
        self.setup_ui()
        self.refresh_comparison("score") # Default: Best by points

    def setup_ui(self):
        t = StyleManager.get_theme(self.current_theme)
        
        # Backdrop container
        self.backdrop = QFrame(self)
        self.backdrop.setObjectName("Backdrop")
        self.backdrop.setStyleSheet(f"background-color: rgba(0, 0, 0, 180);")
        
        # Main window container
        self.window_frame = QFrame(self)
        self.window_frame.setObjectName("ComparisonWindow")
        self.window_frame.setFixedSize(900, 650)
        self.window_frame.setStyleSheet(f"""
            QFrame#ComparisonWindow {{
                background-color: {t['bg_main']};
                border: 1px solid {t['border']};
                border-radius: 16px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.window_frame.setGraphicsEffect(shadow)
        
        self.inner_layout = QVBoxLayout(self.window_frame)
        self.inner_layout.setContentsMargins(20, 15, 20, 20)
        self.inner_layout.setSpacing(15)
        
        # Custom Title Bar
        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(45)
        self.title_bar_layout = QHBoxLayout(self.title_bar)
        self.title_bar_layout.setContentsMargins(5, 0, 5, 0)
        
        title_icon = QLabel("⚖️")
        title_icon.setStyleSheet("font-size: 22px;")
        self.title_bar_layout.addWidget(title_icon)
        
        title_text = QLabel("Сравнение снастей")
        title_text.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {t['text_main']};")
        self.title_bar_layout.addWidget(title_text)
        
        self.title_bar_layout.addStretch()
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(36, 36)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['bg_secondary']};
                color: {t['text_secondary']};
                font-size: 18px;
                font-weight: bold;
                border-radius: 18px;
                border: 1px solid {t['border']};
            }}
            QPushButton:hover {{ 
                background-color: #e74c3c; 
                color: white; 
                border: none;
            }}
        """)
        self.close_btn.clicked.connect(self.close)
        self.title_bar_layout.addWidget(self.close_btn)
        
        self.inner_layout.addWidget(self.title_bar)
        
        # Priority / Criteria Switcher (Point 2: Visible priority buttons)
        self.criteria_frame = QFrame()
        self.criteria_frame.setStyleSheet(f"background-color: {t['bg_secondary']}; border-radius: 10px; border: 1px solid {t['border']};")
        self.criteria_layout = QHBoxLayout(self.criteria_frame)
        self.criteria_layout.setContentsMargins(15, 8, 15, 8)
        self.criteria_layout.setSpacing(15)
        
        lbl = QLabel("Приоритет подбора:")
        lbl.setStyleSheet(f"color: {t['text_secondary']}; font-weight: 700; font-size: 12px;")
        self.criteria_layout.addWidget(lbl)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        priorities = [
            ("🏆 Эффективность", "score"),
            ("🛡️ Прочность", "durability"),
            ("⚡ Чувствительность", "sensitivity"),
            ("💰 Цена", "price")
        ]
        
        for i, (name, key) in enumerate(priorities):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t['bg_tertiary']};
                    color: {t['text_main']};
                    border: 1px solid {t['border']};
                    border-radius: 6px;
                    padding: 0 12px;
                    font-weight: 600;
                    font-size: 11px;
                }}
                QPushButton:checked {{
                    background-color: {t['accent']};
                    color: white;
                    border: none;
                }}
                QPushButton:hover:!checked {{
                    background-color: {t['border']};
                }}
            """)
            if i == 0: btn.setChecked(True)
            self.btn_group.addButton(btn)
            btn.clicked.connect(lambda checked, k=key: self.refresh_comparison(k))
            self.criteria_layout.addWidget(btn)
            
        self.criteria_layout.addStretch()
        self.inner_layout.addWidget(self.criteria_frame)
        
        # Table
        self.table = QTableWidget()
        self.table.setFont(QFont("Segoe UI", 12))
        self.table.setColumnCount(len(self.items) + 1)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {t['border']};
                border-right: 1px solid {t['border']};
                color: {t['text_main']};
                font-size: 13px;
            }}
            QTableWidget::item:last-column {{
                border-right: none;
            }}
        """)
        self.inner_layout.addWidget(self.table)
        
        # Animations setup
        # Deprecated window opacity animation
        
    def close_animated(self):
        AnimationManager.fade_out(self.window_frame, on_finished=self.close)

    def resizeEvent(self, event):
        self.backdrop.setGeometry(self.rect())
        super().resizeEvent(event)

    def showEvent(self, event):
        # Resize to parent size to cover with backdrop
        if self.parent():
            self.setGeometry(self.parent().rect())
        
        # Center the window_frame initially (since it's not in a layout)
        if not self.window_frame.pos().x() > 0: # Only if not moved yet
            self.window_frame.move(
                (self.width() - self.window_frame.width()) // 2,
                (self.height() - self.window_frame.height()) // 2
            )
        
        AnimationManager.fade_in(self.window_frame)
        super().showEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        # Check if clicked on backdrop (Point 2)
        if event.button() == Qt.MouseButton.LeftButton:
            # We must check against the absolute position of the frame
            frame_rect = self.window_frame.geometry()
            if not frame_rect.contains(event.pos()):
                self.close_animated()
                return
            
            # Start dragging if on title bar
            # Title bar geometry is relative to window_frame
            title_rect = self.title_bar.geometry().translated(self.window_frame.pos())
            if title_rect.contains(event.pos()):
                self._drag_pos = event.globalPosition().toPoint() - self.window_frame.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Dragging logic (Point 2)
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            # Boundary check: don't let the window go completely off-screen
            new_pos.setX(max(-self.window_frame.width() + 50, min(new_pos.x(), self.width() - 50)))
            new_pos.setY(max(0, min(new_pos.y(), self.height() - 50)))
            self.window_frame.move(new_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = QPoint()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        # Escape to close (Point 2)
        if event.key() == Qt.Key.Key_Escape:
            self.close_animated()
        super().keyPressEvent(event)

    def calculate_score(self, item, priority="score"):
        score = 0
        kind = item.get("kind")
        stats = item.get("stats", item.get("stats_lvl5", {}))
        
        # Weights Configuration
        weights = {
            "weight": 2.0,
            "durability": 0.5,
            "sensitivity": 0.5,
            "speed": 0.4,
            "visibility": 0.3,
            "abrasion": 0.2
        }
        
        if priority == "durability":
            weights["durability"] = 5.0
            weights["weight"] = 1.0
        elif priority == "sensitivity":
            weights["sensitivity"] = 5.0
            weights["weight"] = 1.0
        
        if kind == "rod":
            score += float(stats.get("max_weight", 0)) * weights["weight"]
            score += float(stats.get("sensitivity", 0)) * weights["sensitivity"]
            score += float(stats.get("durability", 0)) * weights["durability"]
        elif kind == "reel":
            score += float(stats.get("max_weight", 0)) * weights["weight"]
            score += float(stats.get("speed", 0)) * weights["speed"]
            score += float(stats.get("durability", 0)) * weights["durability"]
        elif kind == "line":
            score += float(stats.get("max_weight", 0)) * weights["weight"]
            vis = float(stats.get("visibility", 0))
            score += (100 - vis) * weights["visibility"]
            score += float(stats.get("abrasion", 0)) * weights["abrasion"]
            score += float(stats.get("durability", 0)) * weights["durability"]
        elif kind == "bait":
            score += float(stats.get("durability", 0)) * weights["durability"]
            score += float(stats.get("max_weight", 0)) * weights["weight"]
            
        return score

    def refresh_comparison(self, criteria):
        t = StyleManager.get_theme(self.current_theme)
        kind = self.items[0].get("kind")
        params = ["Название", "Цена"]
        
        if kind == "rod":
            params += ["Уровень", "Макс. Вес (кг)", "Чувствительность (%)", "Управляемость (%)", "Прочность (%)"]
        elif kind == "reel":
            params += ["Уровень", "Макс. Вес (кг)", "Скорость (%)", "Прочность (%)"]
        elif kind == "line":
            params += ["Уровень", "Макс. Вес (кг)", "Видимость (%)", "Растяжимость (%)", "Устойчивость (%)", "Прочность (%)"]
        elif kind == "bait":
            params += ["Целевая среда", "Целевая рыба", "Прочность (%)"]
            
        params.append("Общий балл")
        self.table.setRowCount(len(params))
        
        # Build comparison data
        for col, item in enumerate(self.items, 1):
            stats = item.get("stats", item.get("stats_lvl5", {}))
            score = self.calculate_score(item, criteria)
            price = item.get("price", 0)
            
            row_data = {
                "Название": item.get("name"),
                "Цена": f"${int(price):,}".replace(",", " "),
                "Уровень": item.get("tier", "-"),
                "Макс. Вес (кг)": float(stats.get("max_weight", 0)),
                "Чувствительность (%)": float(stats.get("sensitivity", 0)),
                "Управляемость (%)": float(stats.get("control", 0)),
                "Скорость (%)": float(stats.get("speed", 0)),
                "Прочность (%)": float(stats.get("durability", 0)),
                "Видимость (%)": float(stats.get("visibility", 0)),
                "Растяжимость (%)": float(stats.get("stretch", 0)),
                "Устойчивость (%)": float(stats.get("abrasion", 0)),
                "Целевая среда": item.get("region", "Любой"),
                "Целевая рыба": item.get("fish_type", "Любая"),
                "Общий балл": round(score, 1)
            }
            
            for row_idx, p_name in enumerate(params):
                val = row_data.get(p_name, "-")
                table_item = QTableWidgetItem(str(val))
                table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                if row_idx == 0:
                    font = self.table.font()
                    font.setBold(True)
                    table_item.setFont(font)
                
                self.table.setItem(row_idx, col, table_item)

        # Labels column
        for row_idx, p_name in enumerate(params):
            lbl_item = QTableWidgetItem(p_name)
            lbl_item.setForeground(QBrush(QColor(t['text_secondary'])))
            font = lbl_item.font()
            font.setBold(True)
            lbl_item.setFont(font)
            self.table.setItem(row_idx, 0, lbl_item)

        # Highlight Best
        for row_idx, p_name in enumerate(params):
            if p_name in ["Название", "Уровень", "Целевая среда", "Целевая рыба"]:
                continue
            
            vals = []
            for col in range(1, self.table.columnCount()):
                txt = self.table.item(row_idx, col).text().replace("$", "").replace(" ", "")
                try: vals.append(float(txt))
                except: vals.append(None)
            
            valid_vals = [v for v in vals if v is not None]
            if valid_vals:
                compare_func = min if p_name in ["Цена", "Видимость (%)"] else max
                best_val = compare_func(valid_vals)
                for col_idx, v in enumerate(vals, 1):
                    if v == best_val:
                        it = self.table.item(row_idx, col_idx)
                        it.setForeground(QBrush(QColor(t['success'])))
                        font = it.font()
                        font.setBold(True)
                        it.setFont(font)
                        if row_idx == self.table.rowCount() - 1:
                            it.setBackground(QBrush(QColor(t['success'] + "1A")))

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

class FishingTab(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_theme = "dark"
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 10)
        self.layout.setSpacing(0)
        self.header = QFrame()
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(0, 0, 0, 5)
        self.title_lbl = QLabel("🧭 Рыбалка")
        self.title_lbl.setObjectName("Header")
        self.desc_lbl = QLabel("Подбор снастей, регионы, сборки и калькулятор прибыли")
        self.desc_lbl.setStyleSheet("font-size: 14px; color: #95a5a6;")
        self.header_layout.addWidget(self.title_lbl)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.desc_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.header)
        self.nav_bar = QFrame()
        self.nav_layout = QHBoxLayout(self.nav_bar)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(10)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.tabs_def = [
            (0, "🔧 Снасти / Рыба"),
            (1, "📍 Регионы и рыба"),
            (2, "💬 Вопрос / Сборка"),
            (3, "💰 Калькулятор прибыли"),
            (4, "🏆 Сборки от игроков")
        ]
        self.nav_buttons = {}
        for idx, name in self.tabs_def:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_group.addButton(btn, idx)
            self.nav_layout.addWidget(btn)
            self.nav_buttons[idx] = btn
        self.nav_layout.addStretch()
        self.layout.addWidget(self.nav_bar)
        self.stack = QStackedWidget()
        self.widgets = {}
        
        # Initialize Floating Calculator
        self.calculator = CalculatorWidget(self, self.data_manager)
        self.calculator.result_ready.connect(self.on_calculator_result)
        
        self.widgets[0] = EquipmentPickerWidget(self.data_manager, self)
        self.widgets[1] = RegionsFishWidget(self.data_manager, self)
        self.widgets[2] = AskBuildWidget(self.data_manager, self)
        self.widgets[3] = FishingFinancialWidget(self.data_manager, "fishing", self)
        self.widgets[4] = CommunityBuildsWidget(self.data_manager, self)
        
        for i in range(5):
            self.stack.addWidget(self.widgets[i])
        
        self.layout.addWidget(self.stack)
        self.btn_group.idClicked.connect(self.switch_tab)
        self.nav_buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)
        self.apply_theme(self.current_theme)

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        self.widgets[index].refresh()

    def apply_theme(self, theme_name):
        t = StyleManager.get_theme(theme_name)
        self.current_theme = theme_name
        self.nav_bar.setStyleSheet(f"background-color: {t['bg_secondary']}; border-bottom: 1px solid {t['border']};")
        for i in range(self.stack.count()):
            if i in self.widgets:
                self.widgets[i].apply_theme(theme_name)

    def on_calculator_result(self, result):
        current_widget = self.stack.currentWidget()
        if hasattr(current_widget, "on_calculator_result"):
            current_widget.on_calculator_result(result)

class FishingFinancialWidget(GenericTab):
    def __init__(self, data_manager, category="fishing", parent=None):
        super().__init__(data_manager, category, parent)
        self.main_tab = parent # FishingTab
        self.current_gear_filter = "Все Снасти"
        
        # Override margins and spacing
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(14)
        
    def setup_header(self):
        super().setup_header()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setFixedWidth(150)
        self.search_input.textChanged.connect(self.refresh_data)
        
        # Gear Category Filter
        self.gear_filter_combo = QComboBox()
        self.gear_filter_combo.addItems(["Все Снасти", "Удочка", "Катушка", "Леска", "Наживка", "Рыба"])
        self.gear_filter_combo.currentTextChanged.connect(self.on_gear_filter_changed)
        
        # Add Export to Excel button
        self.btn_export_excel = QPushButton("📊 Экспорт Excel")
        self.btn_export_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_excel.clicked.connect(self.export_to_excel)
        
        self.header_layout.insertWidget(0, self.search_input)
        self.header_layout.insertWidget(1, self.gear_filter_combo)
        self.header_layout.addWidget(self.btn_export_excel)

    def export_to_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт истории расчётов", "", "Excel Files (*.xlsx)")
        if not file_path: return
        if not file_path.endswith('.xlsx'): file_path += '.xlsx'
        
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Рыбалка_История"
            ws.append(["Дата", "Ресурс/Рыба", "Сумма ($)", "Тип", "Примечание"])
            
            transactions = self.data_manager.get_transactions(self.category)
            for t in transactions:
                ws.append([
                    t.get('date'),
                    t.get('item_name'),
                    t.get('amount'),
                    "Доход" if t.get('amount', 0) > 0 else "Расход",
                    t.get('comment')
                ])
            wb.save(file_path)
            QMessageBox.information(self, "Успех", "Данные успешно экспортированы!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте: {e}")

    def on_gear_filter_changed(self, text):
        self.current_gear_filter = text
        self.refresh_data()

    def open_add_transaction_dialog(self):
        try:
            from gui.transaction_dialog import TransactionDialog
            dialog = TransactionDialog(self.main_window, self.data_manager, self.category)
            self.current_dialog = dialog
            
            if dialog.exec():
                self.refresh_data()
                
            self.current_dialog = None
        except Exception as e:
            import traceback
            error_msg = f"Ошибка при открытии окна добавления операции:\n{str(e)}\n\n{traceback.format_exc()}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def apply_theme(self, theme_name):
        super().apply_theme(theme_name)
        t = StyleManager.get_theme(theme_name)
        
        # Table styling (High contrast, larger font)
        self.table.setStyleSheet(self.table.styleSheet() + f"""
            QTableWidget {{
                font-size: 17px;
                background-color: {t['bg_main']};
                gridline-color: {t['border']};
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {t['border']};
            }}
        """)
        
        # Stat cards (Increased visibility)
        for card in [self.stat_start, self.stat_income, self.stat_expense, self.stat_balance, self.stat_profit]:
            card.value_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {t['text_main']};")
            card.title_label.setStyleSheet(f"font-size: 13px; color: {t['text_secondary']};")
            card.setContentsMargins(12, 12, 12, 12)
            card.layout().setSpacing(6)
        
        self.stat_profit.value_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {t['success']};")

    def on_calculator_result(self, result):
        pass # Handled by custom dialog

    def setup_stats(self):
        super().setup_stats()
        self.stat_start.hide()
        self.stat_income.title_label.setText("Доход (фильтр)")
        self.stat_expense.title_label.setText("Расход (фильтр)")
        self.stat_profit.title_label.setText("Прибыль (фильтр)")
        self.stat_balance.title_label.setText("Общий баланс")

    def refresh_data(self):
        # Ensure transactions are sorted newest first
        transactions = self.data_manager.get_transactions(self.category)
        try:
            transactions.sort(
                key=lambda x: (datetime.strptime(x.get("date", "01.01.2000"), "%d.%m.%Y"), x.get("timestamp", 0)), 
                reverse=True
            )
        except:
            pass
            
        super().refresh_data()
        t = StyleManager.get_theme(self.current_theme)
        if hasattr(self, 'stat_profit') and self.stat_profit.value_label:
            self.stat_profit.value_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {t['success']};")

        search_text = self.search_input.text().lower()
        gear_filter = self.current_gear_filter
            
        for row in range(self.table.rowCount()):
            match_search = not search_text
            if not match_search:
                for col in range(self.table.columnCount() - 1):
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        match_search = True
                        break
            
            match_gear = gear_filter == "Все Снасти"
            if not match_gear:
                item_name_col = 1
                item = self.table.item(row, item_name_col)
                if item:
                    text = item.text().lower()
                    if gear_filter.lower() in text:
                        match_gear = True
            
            self.table.setRowHidden(row, not (match_search and match_gear))

    def show_item_stats(self):
        from gui.item_stats_dialog import ItemStatsDialog
        dialog = ItemStatsDialog(self.main_window, self.data_manager, self.category)
        dialog.exec()

    def refresh(self):
        self.refresh_data()

class FishingProfitCalculatorDialog(QDialog):
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle("Калькулятор прибыли: Ресурсы/Рыба")
        self.setMinimumWidth(450)
        self.theme = StyleManager.get_theme("dark")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form
        form = QGridLayout()
        form.setSpacing(10)
        
        # 1. Fish type
        form.addWidget(QLabel("Вид рыбы/ресурса:"), 0, 0)
        self.fish_type = QComboBox()
        self.fish_type.setEditable(True)
        self.fish_type.addItems(["Окунь", "Щука", "Судак", "Карп", "Форель", "Лосось"])
        form.addWidget(self.fish_type, 0, 1)
        
        # 2. Price per kg
        form.addWidget(QLabel("Средняя цена за 1 кг ($):"), 1, 0)
        self.price_per_kg = QDoubleSpinBox()
        self.price_per_kg.setRange(0, 100000)
        self.price_per_kg.setValue(150.0)
        self.price_per_kg.valueChanged.connect(self.calculate)
        form.addWidget(self.price_per_kg, 1, 1)
        
        # 3. Volume
        form.addWidget(QLabel("Объём вылова (кг):"), 2, 0)
        self.volume = QDoubleSpinBox()
        self.volume.setRange(0, 10000)
        self.volume.setValue(10.0)
        self.volume.valueChanged.connect(self.calculate)
        form.addWidget(self.volume, 2, 1)
        
        # 4. Transport
        form.addWidget(QLabel("Транспортные расходы ($):"), 3, 0)
        self.transport_costs = QDoubleSpinBox()
        self.transport_costs.setRange(0, 100000)
        self.transport_costs.setValue(500.0)
        self.transport_costs.valueChanged.connect(self.calculate)
        form.addWidget(self.transport_costs, 3, 1)
        
        # 5. Resource costs (Bait, etc)
        form.addWidget(QLabel("Себестоимость ресурсов ($):"), 4, 0)
        self.resource_costs = QDoubleSpinBox()
        self.resource_costs.setRange(0, 100000)
        self.resource_costs.setValue(200.0)
        self.resource_costs.valueChanged.connect(self.calculate)
        form.addWidget(self.resource_costs, 4, 1)
        
        # 6. Ad Cost
        form.addWidget(QLabel("Стоимость объявления ($):"), 5, 0)
        self.ad_cost = QDoubleSpinBox()
        self.ad_cost.setRange(0, 100000)
        self.ad_cost.setValue(0.0)
        self.ad_cost.valueChanged.connect(self.calculate)
        form.addWidget(self.ad_cost, 5, 1)
        
        layout.addLayout(form)
        
        # Result
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet("background-color: rgba(0,0,0,0.2); border-radius: 8px;")
        res_layout = QVBoxLayout(self.result_frame)
        self.pure_profit_lbl = QLabel("Чистая прибыль: $0.00")
        self.pure_profit_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #2ecc71;")
        self.pure_profit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        res_layout.addWidget(self.pure_profit_lbl)
        layout.addWidget(self.result_frame)
        
        # Buttons
        btns = QHBoxLayout()
        self.save_btn = QPushButton("💾 Сохранить в историю")
        self.save_btn.clicked.connect(self.save_to_history)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)
        
        self.calculate()

    def calculate(self):
        revenue = self.price_per_kg.value() * self.volume.value()
        costs = self.transport_costs.value() + self.resource_costs.value()
        # Ad cost is subtracted from revenue to get current_profit
        # but will be saved as separate operation too.
        profit = revenue - costs - self.ad_cost.value()
        self.pure_profit_lbl.setText(f"Чистая прибыль: ${profit:,.2f}")
        self.current_profit = profit

    def save_to_history(self):
        if self.data_manager:
            item_name = self.fish_type.currentText()
            # We add revenue as the main transaction, and ad_cost as the ad_cost parameter.
            # DataManager will create a separate transaction for it.
            revenue = self.price_per_kg.value() * self.volume.value()
            costs = self.transport_costs.value() + self.resource_costs.value()
            
            # The main transaction amount should be the profit WITHOUT ad_cost, 
            # so that when ad_cost is subtracted as a separate transaction, 
            # the total profit is correct.
            # Wait, if I save revenue-costs as the main amount, and ad_cost separately, 
            # total will be revenue-costs-ad_cost.
            main_amount = revenue - costs
            
            self.data_manager.add_transaction(
                "fishing", 
                main_amount, 
                f"Расчёт прибыли: {item_name} ({self.volume.value()}кг)", 
                item_name=item_name,
                ad_cost=self.ad_cost.value()
            )
        self.accept()

class EquipmentPickerWidget(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_theme = "dark"
        self.columns = 2
        self.main_tab = parent # FishingTab
        
        # Filter states
        self.search_text = ""
        self.selected_items = {
            "rod": None,
            "reel": None,
            "line": None,
            "bait": None
        }
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        
        # --- Search and Category Header ---
        self.filters_frame = QFrame()
        self.filters_vlayout = QVBoxLayout(self.filters_frame)
        self.filters_vlayout.setContentsMargins(12, 12, 12, 12)
        self.filters_vlayout.setSpacing(10)
        
        # Search Row (modernized)
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск снастей по названию, серии или характеристикам...")
        self.search_input.setFixedHeight(42)
        self.search_input.setStyleSheet("""
            QLineEdit {
                font-size: 14px; 
                padding-left: 12px;
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        search_row.addWidget(self.search_input, 1)
        
        self.filters_vlayout.addLayout(search_row)
        
        # Category Buttons (Horizontal, compact)
        self.category_layout = QHBoxLayout()
        self.category_layout.setSpacing(10)
        self.category_buttons = []
        
        categories = [
            ("🎣 Удочки", 0),
            ("⚙️ Катушки", 1),
            ("🧵 Леска", 2),
            ("🪱 Наживка", 3)
        ]
        
        self.category_group = QButtonGroup(self)
        self.category_group.setExclusive(True)
        
        for i, (name, idx) in enumerate(categories):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(36)
            if i == 0: btn.setChecked(True)
            self.category_group.addButton(btn, idx)
            self.category_layout.addWidget(btn, 1)
            self.category_buttons.append(btn)
            
        self.category_group.idClicked.connect(self.on_category_changed)
        self.filters_vlayout.addLayout(self.category_layout)
        
        self.layout.addWidget(self.filters_frame)
        
        # Main content scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(15)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)
        
        # --- Bottom Selection Bar (Sticky) ---
        self.selection_bar = QFrame()
        self.selection_bar.setFixedHeight(60)
        self.selection_bar.setObjectName("SelectionBar")
        self.selection_bar_layout = QHBoxLayout(self.selection_bar)
        self.selection_bar_layout.setContentsMargins(10, 5, 10, 5)
        self.selection_bar_layout.setSpacing(0)
        self.selection_bar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Compare Button (Compact design)
        self.compare_btn = QPushButton("⚖️ СРАВНИТЬ ВЫБОР (0/3)")
        self.compare_btn.setObjectName("CompareBtn")
        self.compare_btn.setFixedSize(240, 40)
        self.compare_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compare_btn.setEnabled(False)
        self.compare_btn.clicked.connect(self.show_comparison)
        self.selection_bar_layout.addWidget(self.compare_btn)
        
        self.layout.addWidget(self.selection_bar)
        
        # Animation for selection bar (slide up)
        self.selection_bar_anim = QPropertyAnimation(self.selection_bar, b"pos")
        self.selection_bar_anim.setDuration(300)
        self.selection_bar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Selection state: list of selected items of the current category
        self.current_selection = []
        
        self.catalog_rods = build_rod_catalog()
        self.catalog_reels = build_reel_catalog()
        self.catalog_lines = build_line_catalog()
        self.catalog_baits = build_bait_catalog()
        
        # Timer for instant search (300ms delay)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.render_cards)
        
        self.render_cards()

    def on_category_changed(self, idx):
        # Clear selection when switching categories to ensure "same type" comparison
        self.current_selection = []
        self.update_compare_button()
        self.render_cards()

    def update_compare_button(self):
        count = len(self.current_selection)
        self.compare_btn.setText(f"⚖️ СРАВНИТЬ ВЫБОР ({count}/3)")
        self.compare_btn.setEnabled(count >= 2)

    def toggle_item_selection(self, item, checked):
        if checked:
            if len(self.current_selection) >= 3:
                QMessageBox.warning(self, "Лимит", "Можно выбрать не более 3-х позиций для сравнения.")
                return
            if item not in self.current_selection:
                self.current_selection.append(item)
        else:
            if item in self.current_selection:
                self.current_selection.remove(item)
        
        # Update UI
        self.update_compare_button()
        self.render_cards()

    def remove_selection(self, kind):
        # Legacy method if needed, but we're moving to multi-select
        pass

    def select_item(self, item):
        # Legacy method if needed, but we're moving to multi-select
        pass

    def update_notification(self, count):
        pass

    def show_comparison(self):
        if len(self.current_selection) < 2: return
        
        from gui.tabs.fishing_tab import ComparisonOverlay
        overlay = ComparisonOverlay(self.current_selection, self.data_manager, self.current_theme, self.window())
        overlay.show()

    def on_search_changed(self):
        self.search_text = self.search_input.text().lower()
        self.search_timer.start(300)

    def compute_columns(self):
        try:
            vw = self.scroll_area.viewport().width()
        except Exception:
            vw = self.width()
        if vw < 520:
            return 1
        if vw < 900:
            return 2
        return 3

    def resizeEvent(self, event):
        new_cols = self.compute_columns()
        if new_cols != self.columns:
            self.columns = new_cols
            self.render_cards()
        super().resizeEvent(event)

    def showEvent(self, event):
        self.columns = self.compute_columns()
        self.render_cards()
        super().showEvent(event)

    def create_item_card(self, item):
        t = StyleManager.get_theme(self.current_theme)
        is_selected = item in self.current_selection
        
        frame = QFrame()
        frame.setObjectName("ItemCard")
        
        # Base style with selection highlight
        border_color = t['accent'] if is_selected else t['border']
        bg_color = f"rgba({QColor(t['accent']).red()}, {QColor(t['accent']).green()}, {QColor(t['accent']).blue()}, 0.05)" if is_selected else t['bg_secondary']
        
        frame.setStyleSheet(f"""
            QFrame#ItemCard {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 12px;
            }}
            QFrame#ItemCard:hover {{
                border-color: {t['accent']};
                background-color: rgba({QColor(t['accent']).red()}, {QColor(t['accent']).green()}, {QColor(t['accent']).blue()}, 0.08);
            }}
        """)
        
        l = QVBoxLayout(frame)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)
        
        kind = item.get("kind", "rod")
        icon = "🎣" if kind == "rod" else ("⚙️" if kind == "reel" else ("🧵" if kind == "line" else "🪱"))
        
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        # Indicator icon
        indicator = QLabel("✅" if is_selected else "⭕")
        indicator.setStyleSheet(f"font-size: 16px; color: {t['accent'] if is_selected else t['text_secondary']};")
        title_row.addWidget(indicator)
        
        title = QLabel(f"{icon} {item['name']}")
        title.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {t['text_main']};")
        title.setWordWrap(True)
        title_row.addWidget(title, 1)
        
        l.addLayout(title_row)
        
        # Stats Grid (2 columns for compactness)
        stats_widget = QWidget()
        stats_grid = QGridLayout(stats_widget)
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setSpacing(4)
        
        def add_stat_grid(label, value, row, col):
            lbl = QLabel(f"{label}: {value}")
            lbl.setStyleSheet(f"color: {t['text_secondary']}; font-size: 11px;")
            stats_grid.addWidget(lbl, row, col)

        if kind == "rod":
            s = item.get("stats", {})
            tier_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
            lvl = tier_map.get(item.get("tier","I"), 1)
            add_stat_grid("Ур.", lvl, 0, 0)
            add_stat_grid("Вес", f"{s.get('max_weight','?')}кг", 0, 1)
            add_stat_grid("Чувст.", f"{s.get('sensitivity','?')}%", 1, 0)
            add_stat_grid("Проч.", f"{s.get('durability','?')}%", 1, 1)
        elif kind == "reel":
            s = item.get("stats", {})
            add_stat_grid("Тип", item['class'], 0, 0)
            add_stat_grid("Вес", f"{s.get('max_weight','?')}кг", 0, 1)
            add_stat_grid("Скор.", f"{s.get('speed','?')}%", 1, 0)
            add_stat_grid("Проч.", f"{s.get('durability','?')}%", 1, 1)
        elif kind == "line":
            s = item.get("stats", {})
            add_stat_grid("Мат.", item['class'], 0, 0)
            add_stat_grid("Вес", f"{s.get('max_weight','?')}кг", 0, 1)
            add_stat_grid("Вид.", f"{s.get('visibility','?')}%", 1, 0)
            add_stat_grid("Проч.", f"{s.get('durability','?')}%", 1, 1)
        else:
            s = item.get("stats_lvl5", {})
            add_stat_grid("Тип", item['class'], 0, 0)
            add_stat_grid("Вес", f"{s.get('max_weight','?')}кг", 0, 1)
            add_stat_grid("Проч.", f"{s.get('durability','?')}", 1, 0)
            
        l.addWidget(stats_widget)
        
        # Bottom price and select button (Horizontal for more space)
        bottom_row = QHBoxLayout()
        price_lbl = QLabel(f"${int(item['price']):,}".replace(",", " "))
        price_lbl.setStyleSheet(f"color: {t['accent']}; font-weight: 800; font-size: 15px;")
        bottom_row.addWidget(price_lbl)
        
        bottom_row.addStretch()
        
        select_btn = QPushButton("ОТМЕНИТЬ" if is_selected else "ВЫБРАТЬ")
        select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        select_btn.setFixedSize(85, 26)
        
        btn_color = t['danger'] if is_selected else t['accent']
        select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_color};
                color: #FFFFFF;
                border-radius: 6px;
                font-weight: 700;
                font-size: 11px;
                padding: 0px 5px;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            QPushButton:hover {{
                background-color: {QColor(btn_color).lighter(115).name()};
                border: 1px solid white;
            }}
        """)
        select_btn.clicked.connect(lambda: self.toggle_item_selection(item, not is_selected))
        bottom_row.addWidget(select_btn)
        
        l.addLayout(bottom_row)
        
        return frame

    def render_cards(self):
        # Save scroll position
        vbar = self.scroll_area.verticalScrollBar()
        scroll_pos = vbar.value()
        
        self.columns = self.compute_columns()
        
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        
        filtered = []
        
        checked_id = self.category_group.checkedId()
        source = (
            self.catalog_rods if checked_id == 0
            else self.catalog_reels if checked_id == 1
            else self.catalog_lines if checked_id == 2
            else self.catalog_baits
        )
        
        for it in source:
            if self.search_text:
                fields = [
                    str(it.get('name', it.get('name_ru', ''))),
                    str(it.get('series', '')),
                    str(it.get('tier', '')),
                    str(it.get('class', '')),
                    str(it.get('purpose', ''))
                ]
                searchable = " ".join(fields).lower()
                if not all(word in searchable for word in self.search_text.split()):
                    continue
            filtered.append(it)
            
        r = 0
        c = 0
        for it in filtered:
            card = self.create_item_card(it)
            self.grid.addWidget(card, r, c)
            c += 1
            if c >= self.columns:
                c = 0
                r += 1
        
        # Restore scroll position after a short delay to allow layout update
        QTimer.singleShot(10, lambda: vbar.setValue(scroll_pos))

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        t = StyleManager.get_theme(theme_name)
        
        # Style filters frame
        self.filters_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t['bg_secondary']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
        """)
        
        # Style Selection Bar
        self.selection_bar.setStyleSheet(f"""
            QFrame#SelectionBar {{
                background-color: {t['bg_secondary']};
                border-top: 2px solid {t['accent']};
            }}
        """)
        
        # Style Compare Button (Compact design)
        self.compare_btn.setStyleSheet(f"""
            QPushButton#CompareBtn {{
                background-color: {t['accent']};
                color: white;
                border-radius: 8px;
                font-weight: 800;
                font-size: 11px;
                border: 1px solid white;
                text-transform: uppercase;
                padding: 0 5px;
            }}
            QPushButton#CompareBtn:disabled {{
                background-color: {t['bg_tertiary']};
                color: {t['text_secondary']};
                border: 1px solid {t['border']};
                font-size: 10px;
            }}
            QPushButton#CompareBtn:hover:enabled {{
                background-color: {t['accent_hover']};
                border-color: {t['success']};
            }}
        """)
        
        # Category buttons styling
        btn_qss = f"""
            QPushButton {{ 
                background-color: {t['bg_tertiary']}; 
                border: 1px solid {t['border']}; 
                color: {t['text_main']}; 
                border-radius: 8px; 
                font-weight: bold;
                font-size: 12px;
            }} 
            QPushButton:checked {{ 
                background-color: {t['accent']}; 
                color: white; 
                border: none; 
            }} 
            QPushButton:hover {{ 
                background-color: {t['border']}; 
            }}
        """
        for btn in self.category_buttons: btn.setStyleSheet(btn_qss)
        self.render_cards()
        self.update_compare_button()

    def refresh(self):
        pass

class FishCard(QFrame):
    def __init__(self, fish_data, data_manager, theme, parent=None):
        super().__init__(parent)
        self.fish_data = fish_data
        self.data_manager = data_manager
        self.current_theme = theme
        self.setup_ui()

    def setup_ui(self):
        t = StyleManager.get_theme(self.current_theme)
        self.setFixedSize(180, 260)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {t['bg_secondary']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Image
        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(164, 110)
        self.img_lbl.setScaledContents(True)
        self.img_lbl.setStyleSheet(f"background-color: {t['bg_tertiary']}; border-radius: 5px;")
        
        # Lazy load image placeholder or real image if already available
        self.update_image()
        layout.addWidget(self.img_lbl)
        
        # Russian Name
        self.name_ru = QLabel(self.fish_data.get("name_ru", "Рыба"))
        self.name_ru.setStyleSheet("font-weight: bold; font-size: 13px; color: #3498db;")
        self.name_ru.setWordWrap(True)
        layout.addWidget(self.name_ru)
        
        # Latin Name
        self.name_lat = QLabel(self.fish_data.get("name_lat", "Species"))
        self.name_lat.setStyleSheet(f"font-style: italic; font-size: 11px; color: {t['text_secondary']};")
        layout.addWidget(self.name_lat)
        
        # Region/Season info
        info = f"{self.fish_data.get('region', 'Любой')} • {self.fish_data.get('season', 'Все')}"
        self.info_lbl = QLabel(info)
        self.info_lbl.setStyleSheet(f"font-size: 10px; color: {t['text_secondary']};")
        layout.addWidget(self.info_lbl)
        
        layout.addStretch()
        
        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(5)
        
        # Collection Button (Point 4: Redesign with animations/hover)
        self.collect_btn = QPushButton()
        self.collect_btn.setCheckable(True)
        is_collected = self.data_manager.get_setting(f"fish_collected_{self.fish_data['id']}", False)
        self.collect_btn.setChecked(is_collected)
        self.collect_btn.setFixedSize(164, 32)
        self.collect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_collect_btn_style()
        self.collect_btn.toggled.connect(self.on_collection_toggled)
        layout.addWidget(self.collect_btn)
        
        # Action Buttons Row
        actions = QHBoxLayout()
        actions.setSpacing(5)
        
        # Add to catch button
        self.add_btn = QPushButton("➕ В улов")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setFixedHeight(28)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['accent']};
                color: white;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {t['accent_hover']}; }}
        """)
        self.add_btn.clicked.connect(self.on_add_clicked)
        actions.addWidget(self.add_btn, 2)
        
        # Remove from catch button (Point 4)
        self.remove_btn = QPushButton("🗑️")
        self.remove_btn.setToolTip("Убрать последний улов этой рыбы")
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['bg_tertiary']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {t['danger']}33; border-color: {t['danger']}; }}
        """)
        self.remove_btn.clicked.connect(self.on_remove_clicked)
        actions.addWidget(self.remove_btn, 0)
        
        layout.addLayout(actions)

    def update_collect_btn_style(self):
        t = StyleManager.get_theme(self.current_theme)
        is_collected = self.collect_btn.isChecked()
        
        icon = "⭐" if is_collected else "📁"
        text = " В КОЛЛЕКЦИИ" if is_collected else " В КОЛЛЕКЦИЮ"
        self.collect_btn.setText(f"{icon}{text}")
        
        if is_collected:
            bg = t['success']
            border = t['success']
        else:
            bg = "transparent"
            border = t['border']
            
        self.collect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {"white" if is_collected else t['text_secondary']};
                border: 2px solid {border};
                border-radius: 8px;
                font-size: 10px;
                font-weight: 900;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {t['success'] if is_collected else t['bg_tertiary']};
                border-color: {t['success']};
                color: white;
            }}
        """)

    def update_image(self):
        # In a real app, we'd load from path. Here we use placeholders or resource paths.
        path = self.fish_data.get("photo_path")
        if path:
            pix = self.data_manager.load_pixmap(path, (164, 110))
            if not pix.isNull():
                self.img_lbl.setPixmap(pix)
                return
        self.img_lbl.setText("🖼")
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def on_collection_toggled(self, checked):
        self.data_manager.set_setting(f"fish_collected_{self.fish_data['id']}", checked)
        self.update_collect_btn_style()
        
        # Notify RegionsFishWidget to update global counter
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, RegionsFishWidget):
            parent_widget = parent_widget.parent()
        if parent_widget:
            parent_widget.update_stats()

    def on_remove_clicked(self):
        fish_name = self.fish_data.get("name_ru", "Рыба")
        ans = QMessageBox.question(
            self, "Подтверждение",
            f"Вы действительно хотите удалить последнюю операцию с рыбой '{fish_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            # Find and remove the latest transaction for this fish
            transactions = self.data_manager.get_transactions("fishing")
            target_id = None
            for t in reversed(transactions):
                if fish_name in t.get("comment", ""):
                    target_id = t["id"]
                    break
            
            if target_id:
                self.data_manager.delete_transaction("fishing", target_id)
                QMessageBox.information(self, "Успех", f"Последний улов '{fish_name}' удален.")
                
                # Refresh UI
                parent_tab = self.window().findChild(FishingTab)
                if parent_tab:
                    parent_tab.widgets[3].refresh_data()
            else:
                QMessageBox.warning(self, "Инфо", f"Операции с рыбой '{fish_name}' не найдены.")

    def on_add_clicked(self):
        # Find the parent FishingTab
        parent_tab = self.window().findChild(FishingTab)
        if parent_tab:
            # The Financial widget is at index 3
            financial_widget = parent_tab.widgets.get(3)
            if financial_widget:
                # Store the selected fish name to use in the dialog
                fish_name = self.fish_data.get("name_ru", "Рыба")
                
                # We need a way to pass the prefilled name to the dialog.
                # Let's modify the financial_widget slightly to accept a prefilled name or just handle it here.
                
                # Instead of direct add, let's open the dialog with pre-filled name
                from gui.transaction_dialog import TransactionDialog
                
                # Show calculator as requested
                if not parent_tab.calculator.isVisible():
                    parent_tab.calculator.show()
                    parent_tab.calculator.raise_()
                
                dialog = TransactionDialog(financial_widget.main_window, financial_widget.data_manager, financial_widget.category)
                
                # Set the prefilled name
                # In Fishing, the item_name_input is a QComboBox with ["Удочка", "Катушка", "Леска", "Наживка", "Все Снасти"]
                # However, the user might want to add the specific fish name.
                # For now, let's just add it to the custom part or select "Все Снасти" and add fish name to comment.
                # Actually, the user asked to replace label with "Снасти" and use dropdown.
                # If it's a catch, maybe we should add "Улов" to the dropdown or just use "Все Снасти".
                
                dialog.comment_input.setText(f"Улов: {fish_name}")
                financial_widget.current_dialog = dialog
                
                if dialog.exec():
                    parent_tab.calculator.hide()
                    financial_widget.refresh_data()
                else:
                    parent_tab.calculator.hide()
                
                financial_widget.current_dialog = None

class RegionsFishWidget(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_theme = "dark"
        self.fish_list = self.generate_mock_fish_data() # 194 types
        self.filtered_fish = list(self.fish_list)
        self.loaded_count = 0
        self.batch_size = 20
        
        self.setup_ui()

    def generate_mock_fish_data(self):
        # Generate 194 types of fish for the gallery
        regions = ["Океан", "Озеро", "Река", "Кайо-Перико", "Остров"]
        seasons = ["Лето", "Осень", "Зима", "Весна", "Все"]
        data = []
        for i in range(1, 195):
            data.append({
                "id": f"fish_{i}",
                "name_ru": f"Рыба {i}",
                "name_lat": f"Species Latinus {i}",
                "region": random.choice(regions),
                "season": random.choice(seasons),
                "photo_path": None # Placeholder
            })
        return data

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 10, 0, 0)
        self.layout.setSpacing(10)
        
        # Header: Search and Filters
        header = QFrame()
        hl = QHBoxLayout(header)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск рыбы (название рус/лат)...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        hl.addWidget(self.search_input, 3)
        
        self.region_filter = QComboBox()
        self.region_filter.addItems(["Все регионы", "Океан", "Озеро", "Река", "Кайо-Перико", "Остров"])
        self.region_filter.currentTextChanged.connect(self.on_filter_changed)
        hl.addWidget(self.region_filter, 1)
        
        self.season_filter = QComboBox()
        self.season_filter.addItems(["Все сезоны", "Лето", "Осень", "Зима", "Весна", "Все"])
        self.season_filter.currentTextChanged.connect(self.on_filter_changed)
        hl.addWidget(self.season_filter, 1)
        
        # Collection Stats (analog Farm BP)
        self.stats_lbl = QLabel("Собрано: 0/194")
        self.stats_lbl.setStyleSheet("font-weight: bold; color: #2ecc71; margin-left: 10px;")
        hl.addWidget(self.stats_lbl)
        
        self.layout.addWidget(header)
        
        # Scroll Area for Gallery
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(15)
        self.grid.setContentsMargins(10, 10, 10, 10)
        
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
        
        # Connect scroll event for lazy loading
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        
        self.refresh_gallery()
        self.update_stats()

    def update_stats(self):
        collected = 0
        for f in self.fish_list:
            if self.data_manager.get_setting(f"fish_collected_{f['id']}", False):
                collected += 1
        self.stats_lbl.setText(f"Собрано: {collected}/194")

    def on_filter_changed(self):
        search = self.search_input.text().lower()
        region = self.region_filter.currentText()
        season = self.season_filter.currentText()
        
        self.filtered_fish = []
        for f in self.fish_list:
            if search and (search not in f["name_ru"].lower() and search not in f["name_lat"].lower()):
                continue
            if region != "Все регионы" and f["region"] != region:
                continue
            if season != "Все сезоны" and f["season"] != season:
                continue
            self.filtered_fish.append(f)
            
        self.refresh_gallery()

    def refresh_gallery(self):
        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.loaded_count = 0
        self.load_next_batch()

    def load_next_batch(self):
        if self.loaded_count >= len(self.filtered_fish):
            return
            
        end = min(self.loaded_count + self.batch_size, len(self.filtered_fish))
        batch = self.filtered_fish[self.loaded_count:end]
        
        # Fixed 4 columns as requested (Point 4)
        cols = 4
        
        for i, fish in enumerate(batch):
            idx = self.loaded_count + i
            card = FishCard(fish, self.data_manager, self.current_theme)
            # Re-connect toggle to update stats
            card.collect_btn.toggled.connect(self.update_stats)
            self.grid.addWidget(card, idx // cols, idx % cols)
            
        self.loaded_count = end

    def on_scroll(self, value):
        # Check if near bottom
        vbar = self.scroll.verticalScrollBar()
        if value > vbar.maximum() - 100:
            self.load_next_batch()

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        # In a real implementation, we'd tell all cards to update their style
        self.refresh_gallery()

    def refresh(self):
        pass

class AskBuildWidget(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_theme = "dark"
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        # Header
        header = QLabel("Конфигуратор оптимальной сборки")
        header.setObjectName("Header")
        self.layout.addWidget(header)
        
        # Main Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)
        
        form = QFrame()
        form.setStyleSheet("QFrame { background-color: rgba(0,0,0,0.1); border-radius: 12px; padding: 10px; }")
        fl = QGridLayout(form)
        fl.setContentsMargins(20, 20, 20, 20)
        fl.setSpacing(15)
        
        # Labels style
        lbl_style = "font-size: 15px; font-weight: 600; color: #ccc;"
        
        # 1. Gear Type
        fl.addWidget(QLabel("Тип снасти:", styleSheet=lbl_style), 0, 0)
        self.gear_type = QComboBox()
        self.gear_type.addItems(["Спиннинг", "Кастинговое", "Фидер", "Поплавочное"])
        self.gear_type.setToolTip("Выберите основной тип удилища (Спиннинг, Фидер и т.д.)")
        fl.addWidget(self.gear_type, 0, 1)
        self.gear_type_valid = QLabel("✅")
        fl.addWidget(self.gear_type_valid, 0, 2)
        
        # 2. Region
        fl.addWidget(QLabel("Регион ловли:", styleSheet=lbl_style), 1, 0)
        self.region = QComboBox()
        self.region.addItems(["Океан", "Озеро", "Река", "Кайо-Перико", "Остров"])
        self.region.setToolTip("Выберите водоем, где планируете рыбачить")
        fl.addWidget(self.region, 1, 1)
        fl.addWidget(QLabel("✅"), 1, 2)
        
        # 3. Fish needed
        fl.addWidget(QLabel("Целевая рыба:", styleSheet=lbl_style), 2, 0)
        self.fish_needed = QLineEdit()
        self.fish_needed.setPlaceholderText("Например: Щука, Окунь...")
        self.fish_needed.setToolTip("Введите название рыбы, на которую ориентирована сборка")
        self.fish_needed.textChanged.connect(self.validate_form)
        fl.addWidget(self.fish_needed, 2, 1)
        self.fish_valid = QLabel("❌")
        fl.addWidget(self.fish_valid, 2, 2)
        
        # 4. Fishing Time
        fl.addWidget(QLabel("Время ловли:", styleSheet=lbl_style), 3, 0)
        self.fishing_time = QComboBox()
        self.fishing_time.addItems(["Утро", "День", "Вечер", "Ночь", "Любое"])
        self.fishing_time.setToolTip("Выберите время суток для ловли")
        fl.addWidget(self.fishing_time, 3, 1)
        fl.addWidget(QLabel("✅"), 3, 2)
        
        # 5. Catch Vol (Weight)
        fl.addWidget(QLabel("Улов, кг (ожидаемый):", styleSheet=lbl_style), 4, 0)
        self.catch_weight = QDoubleSpinBox()
        self.catch_weight.setRange(0.1, 500.0)
        self.catch_weight.setValue(5.0)
        self.catch_weight.setToolTip("Укажите средний вес одной рыбы или желаемый общий вес")
        fl.addWidget(self.catch_weight, 4, 1)
        fl.addWidget(QLabel("✅"), 4, 2)
        
        # 6. Budget
        fl.addWidget(QLabel("Бюджет ($):", styleSheet=lbl_style), 5, 0)
        self.budget = QSpinBox()
        self.budget.setRange(0, 10000000)
        self.budget.setSingleStep(1000)
        self.budget.setToolTip("Максимальная сумма на покупку снастей")
        fl.addWidget(self.budget, 5, 1)
        fl.addWidget(QLabel("✅"), 5, 2)
        
        self.submit_btn = QPushButton("Сгенерировать сборку")
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.setFixedHeight(45)
        self.submit_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.submit_btn.clicked.connect(self.generate_build)
        fl.addWidget(self.submit_btn, 6, 0, 1, 3)
        
        scroll_layout.addWidget(form)
        
        # Result Area
        self.result_frame = QFrame()
        self.result_frame.setMinimumHeight(150)
        rl = QVBoxLayout(self.result_frame)
        rl.setContentsMargins(20, 20, 20, 20)
        self.result_lbl = QLabel("Заполните параметры для получения рекомендации...")
        self.result_lbl.setWordWrap(True)
        self.result_lbl.setStyleSheet("font-size: 16px; line-height: 1.6; padding: 5px;")
        rl.addWidget(self.result_lbl)
        scroll_layout.addWidget(self.result_frame)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        self.layout.addWidget(scroll)
        
        self.apply_theme(self.current_theme)
        self.validate_form()

    def validate_form(self):
        fish = self.fish_needed.text().strip()
        if len(fish) >= 2:
            self.fish_valid.setText("✅")
            self.submit_btn.setEnabled(True)
        else:
            self.fish_valid.setText("❌")
            self.submit_btn.setEnabled(False)

    def generate_build(self):
        # Dynamic build suggestion logic based on previous user stats if available
        # For now, enhanced static logic
        region = self.region.currentText()
        fish = self.fish_needed.text().strip()
        weight = self.catch_weight.value()
        budget = self.budget.value()
        
        # Task 3: Fetch equipment names from data_manager
        equipment = self.data_manager.get_fishing_equipment()
        line_name = equipment.get("line_name", "–")
        line_durability = equipment.get("line_durability", "–")
        bait_name = equipment.get("bait_name", "–")
        bait_durability = equipment.get("bait_durability", "–")
        
        # Logic for Rod/Reel recommendation (keep existing for now but ensure fallback)
        if weight > 50:
            rod = "Охотник за Трофеем V"
            reel = "Трофейный Драг V"
            income = "~150k/час"
        elif region == "Океан":
            rod = "Глубинный Троллинг IV"
            reel = "Глубинный Ход IV"
            income = "~120k/час"
        elif weight < 2:
            rod = "Тихий Спиннинг III"
            reel = "Тихий Драг III"
            income = "~40k/час"
        else:
            rod = "Речной Хищник V"
            reel = "Речной Тягач V"
            income = "~90k/час"
            
        text = f"<b>Рекомендуемая сборка для ловли '{fish}':</b><br><br>"
        text += f"🎣 <b>Удочка:</b> {rod}<br>"
        text += f"⚙️ <b>Катушка:</b> {reel}<br>"
        text += f"🧵 <b>Леска:</b> {line_name} ({line_durability if line_durability != '–' else '?'})<br>"
        text += f"🪱 <b>Наживка:</b> {bait_name} ({bait_durability if bait_durability != '–' else '?'})<br>"
        text += f"💰 <b>Ожидаемый доход:</b> {income}<br><br>"
        text += f"<i>Совет: Для {region} в это время года лучше использовать флюорокарбоновую леску.</i>"
        
        self.result_lbl.setText(text)

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        t = StyleManager.get_theme(theme_name)
        self.result_frame.setStyleSheet(f"background-color: {t['bg_secondary']}; border: 1px solid {t['border']}; border-radius: 12px;")
        self.result_lbl.setStyleSheet(f"color: {t['text_main']}; font-size: 16px;")

    def refresh(self):
        pass

class CommunityBuildsWidget(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_theme = "dark"
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 20, 0, 0)
        self.layout.setSpacing(10)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.grid.setSpacing(15)
        self.scroll.setWidget(self.content)
        self.layout.addWidget(self.scroll)
        self.builds = [
            {"title": "🔥 Самая выгодная сборка (фарм)", "rod": "Плуг Лещ V", "reel": "Лайт Фидер", "line": "Фидерная 5", "line_durability": "100%", "bait": "Фидерная наживка", "bait_durability": "100%", "region": "Река", "income": "~100k/час"},
            {"title": "🏆 Турнирная сборка", "rod": "Охотник за Трофеем V", "reel": "Трофи Драг 5", "line": "Монолит 5", "line_durability": "100%", "bait": "Трофейная наживка", "bait_durability": "100%", "region": "Океан", "income": "~110k/час"},
            {"title": "🚀 Универсал мид", "rod": "Речной Хищник V", "reel": "Хищник Драг 5", "line": "Щит 5", "line_durability": "100%", "bait": "Джиг речной", "bait_durability": "100%", "region": "Река", "income": "~80k/час"},
            {"title": "🪱 Поплавочный комфорт", "rod": "Верхова Ель IV", "reel": "Поплавок 4", "line": "Тонкая 4", "line_durability": "100%", "bait": "Червь/мотыли", "bait_durability": "100%", "region": "Озеро", "income": "~60k/час"},
        ]
        self.render()

    def build_card(self, b):
        t = StyleManager.get_theme(self.current_theme)
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {t['bg_secondary']}; border: 1px solid {t['border']}; border-radius: 8px;")
        l = QVBoxLayout(frame)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(8) # Increased spacing for better readability
        
        title = QLabel(b["title"])
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        title.setWordWrap(True)
        l.addWidget(title)
        
        # Grid for stats to avoid overlapping
        grid = QGridLayout()
        grid.setSpacing(5)
        
        def add_stat(icon, label, value, row):
            icon_lbl = QLabel(icon)
            icon_lbl.setFixedWidth(20)
            grid.addWidget(icon_lbl, row, 0)
            
            val_lbl = QLabel(f"{label}: {value}")
            val_lbl.setWordWrap(True)
            grid.addWidget(val_lbl, row, 1)

        add_stat("🎣", "Удочка", b.get('rod', '–'), 0)
        add_stat("⚙️", "Катушка", b.get('reel', '–'), 1)
        
        line_val = f"{b.get('line', b.get('line_name', '–'))} ({b.get('line_durability', '–')})"
        add_stat("🧵", "Леска", line_val, 2)
        
        bait_val = f"{b.get('bait', b.get('bait_name', '–'))} ({b.get('bait_durability', '–')})"
        add_stat("🪱", "Наживка", bait_val, 3)
        
        add_stat("📍", "Регион", b.get('region', '–'), 4)
        
        l.addLayout(grid)
        
        income_lbl = QLabel(f"💰 Доход: {b.get('income', '–')}")
        income_lbl.setStyleSheet(f"color: {t['success']}; font-weight: bold; margin-top: 5px;")
        l.addWidget(income_lbl)
        
        return frame

    def render(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        r = 0
        c = 0
        for b in self.builds:
            card = self.build_card(b)
            self.grid.addWidget(card, r, c)
            c += 1
            if c >= 3:
                c = 0
                r += 1

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        self.render()

    def refresh(self):
        pass

def build_rod_catalog():
    data = []
    def add_series(series, prices, cls, test, region, fish_type, goal, purpose):
        tiers = ["I", "II", "III", "IV", "V"]
        for i, price in enumerate(prices):
            item = {
                "series": series,
                "tier": tiers[i],
                "name": f"{series} {tiers[i]}",
                "class": cls,
                "test": test,
                "region": region,
                "fish_type": fish_type,
                "goal": goal,
                "purpose": purpose,
                "price": float(str(price).replace("~", "")),
                "kind": "rod",
            }
            data.append(item)
    add_series("Тихий Спиннинг", [5600, 7400, 9600, 12300, 15400], "UL", "0.5–10 г", "Река", "Хищник", "Универсально", "Форель, окунь, хариус")
    add_series("Речной Хищник", [6200, 8700, 12100, 16400, 21600], "M/H", "10–60 г", "Река", "Хищник", "Фарм", "Щука, жерех, голавль")
    add_series("Донный Тактик", [6900, 9900, 14200, 19700, 26400], "Фидер", "50–350 г", "Река", "Универсальная", "Фарм", "Лещ, карп, плотва")
    add_series("Рифовый Легкий", [5900, 8100, 10800, 14200, 18200], "Лайт", "10–40 г", "Остров", "Универсальная", "Универсально", "Риф, лёгкие приманки")
    add_series("Тропический Хищник", [7600, 11200, 16100, 22400, 30000], "M/H", "10–60 г", "Остров", "Хищник", "Прибыль", "Тропический джиг")
    add_series("Береговой Бриз", [6600, 9100, 12300, 16200, 20700], "L/M", "10–50 г", "Океан", "Универсальная", "Универсально", "Береговая ловля")
    add_series("Сёрф-Тяжеловес", [8100, 12500, 18500, 26300, 35700], "Heavy", "100–500 г", "Океан", "Трофейная", "Турнир", "Сёрф, тяжёлые приманки")
    add_series("Глубинный Троллинг", [8900, 14000, 21200, 30400, 41700], "Super H", "200–600 г", "Океан", "Глубинная", "Прибыль", "Троллинг лодка")
    add_series("Охотник за Трофеем", [9700, 15900, 24800, 36300, 50500], "Трофеи", "80–600+ г", "Океан", "Трофейная", "Турнир", "Рекорды, щука/сом")
    add_series("Путник", [6600, 9400, 13200, 18100, 23900], "Travel M/H", "20–200 г", "Остров", "Универсальная", "Универсально", "Походы, универсал")
    # Attach level-specific stats from provided technical specs
    attach_rod_level_stats(data)
    return data

def rod_stats_by_tier():
    # Level-specific stats per series (tiers I..V)
    return {
        "Тихий Спиннинг": [
            {"max_weight": 1.5, "sensitivity": 50, "control": 12, "durability": 0},
            {"max_weight": 2.4, "sensitivity": 56, "control": 20, "durability": 5},
            {"max_weight": 3.4, "sensitivity": 61, "control": 28, "durability": 11},
            {"max_weight": 4.3, "sensitivity": 67, "control": 36, "durability": 17},
            {"max_weight": 5.3, "sensitivity": 72, "control": 44, "durability": 22},
        ],
        "Речной Хищник": [
            {"max_weight": 3.0, "sensitivity": 30, "control": 0, "durability": 4},
            {"max_weight": 5.1, "sensitivity": 35, "control": 9, "durability": 10},
            {"max_weight": 7.2, "sensitivity": 40, "control": 17, "durability": 16},
            {"max_weight": 9.3, "sensitivity": 45, "control": 25, "durability": 22},
            {"max_weight": 11.4, "sensitivity": 50, "control": 34, "durability": 28},
        ],
        "Донный Тактик": [
            {"max_weight": 4.0, "sensitivity": 10, "control": 29, "durability": 10},
            {"max_weight": 6.9, "sensitivity": 14, "control": 36, "durability": 17},
            {"max_weight": 9.8, "sensitivity": 19, "control": 43, "durability": 23},
            {"max_weight": 12.7, "sensitivity": 23, "control": 51, "durability": 29},
            {"max_weight": 15.6, "sensitivity": 28, "control": 58, "durability": 35},
        ],
        "Береговой Бриз": [
            {"max_weight": 4.0, "sensitivity": 30, "control": 12, "durability": 6},
            {"max_weight": 5.6, "sensitivity": 36, "control": 19, "durability": 12},
            {"max_weight": 7.1, "sensitivity": 41, "control": 26, "durability": 18},
            {"max_weight": 8.7, "sensitivity": 47, "control": 33, "durability": 24},
            {"max_weight": 10.2, "sensitivity": 52, "control": 40, "durability": 30},
        ],
        "Сёрф-Тяжеловес": [
            {"max_weight": 8.0, "sensitivity": 0, "control": 24, "durability": 17},
            {"max_weight": 12.1, "sensitivity": 5, "control": 31, "durability": 24},
            {"max_weight": 16.2, "sensitivity": 10, "control": 39, "durability": 30},
            {"max_weight": 20.3, "sensitivity": 15, "control": 46, "durability": 38},
            {"max_weight": 24.4, "sensitivity": 20, "control": 53, "durability": 45},
        ],
        "Глубинный Троллинг": [
            {"max_weight": 10.0, "sensitivity": 4, "control": 19, "durability": 21},
            {"max_weight": 15.0, "sensitivity": 8, "control": 26, "durability": 28},
            {"max_weight": 20.0, "sensitivity": 12, "control": 34, "durability": 35},
            {"max_weight": 25.0, "sensitivity": 16, "control": 41, "durability": 43},
            {"max_weight": 30.0, "sensitivity": 20, "control": 49, "durability": 50},
        ],
        "Рифовый Легкий": [
            {"max_weight": 2.5, "sensitivity": 40, "control": 0, "durability": 2},
            {"max_weight": 3.9, "sensitivity": 46, "control": 7, "durability": 8},
            {"max_weight": 5.3, "sensitivity": 51, "control": 15, "durability": 14},
            {"max_weight": 6.7, "sensitivity": 57, "control": 22, "durability": 20},
            {"max_weight": 8.1, "sensitivity": 62, "control": 30, "durability": 25},
        ],
        "Тропический Хищник": [
            {"max_weight": 6.0, "sensitivity": 20, "control": 5, "durability": 15},
            {"max_weight": 9.2, "sensitivity": 25, "control": 12, "durability": 21},
            {"max_weight": 12.4, "sensitivity": 30, "control": 20, "durability": 28},
            {"max_weight": 15.7, "sensitivity": 35, "control": 27, "durability": 35},
            {"max_weight": 18.9, "sensitivity": 40, "control": 34, "durability": 41},
        ],
        "Охотник за Трофеем": [
            {"max_weight": 12.0, "sensitivity": 10, "control": 36, "durability": 25},
            {"max_weight": 18.4, "sensitivity": 15, "control": 43, "durability": 33},
            {"max_weight": 24.9, "sensitivity": 20, "control": 50, "durability": 42},
            {"max_weight": 31.3, "sensitivity": 25, "control": 57, "durability": 50},
            {"max_weight": 37.8, "sensitivity": 30, "control": 64, "durability": 58},
        ],
        "Путник": [
            {"max_weight": 3.5, "sensitivity": 30, "control": 14, "durability": 8},
            {"max_weight": 5.9, "sensitivity": 36, "control": 22, "durability": 15},
            {"max_weight": 8.3, "sensitivity": 41, "control": 29, "durability": 21},
            {"max_weight": 10.7, "sensitivity": 47, "control": 36, "durability": 28},
            {"max_weight": 13.1, "sensitivity": 52, "control": 44, "durability": 34},
        ],
    }

def attach_rod_level_stats(items):
    levels = rod_stats_by_tier()
    for it in items:
        series = it.get("series")
        tier = it.get("tier")
        lst = levels.get(series) or levels.get(series.replace("Серф","Сёрф"))
        if lst:
            idx = ["I","II","III","IV","V"].index(tier) if tier in ["I","II","III","IV","V"] else 0
            it["stats"] = lst[idx]

def build_reel_catalog():
    data = []
    def add_series(series, prices, cls, region, fish_type, goal, purpose, stats_list):
        tiers = ["I", "II", "III", "IV", "V"]
        for i, price in enumerate(prices):
            item = {
                "series": series,
                "tier": tiers[i],
                "name": f"{series} {tiers[i]}",
                "class": cls,
                "region": region,
                "fish_type": fish_type,
                "goal": goal,
                "purpose": purpose,
                "price": float(str(price).replace("~", "").replace(" ", "")),
                "kind": "reel",
                "stats": stats_list[i], # Detailed stats for current tier
                "stats_lvl5": stats_list[-1], # Backward compatibility
            }
            data.append(item)
    
    add_series("Тихий Драг", [7500, 9500, 12100, 15400, 19200], "spin L", "Озеро", "Универсальная", "Универсально", "Тихая ловля", [
        {"max_weight": 2.2, "speed": 46, "durability": 0},
        {"max_weight": 3.0, "speed": 52, "durability": 5},
        {"max_weight": 3.7, "speed": 58, "durability": 10},
        {"max_weight": 4.5, "speed": 64, "durability": 15},
        {"max_weight": 5.2, "speed": 70, "durability": 20},
    ])
    add_series("Речной Тягач", [8900, 11800, 15800, 20800, 26900], "multi F", "Река", "Универсальная", "Фарм", "Силовая тяга", [
        {"max_weight": 3.8, "speed": 7, "durability": 29},
        {"max_weight": 5.0, "speed": 12, "durability": 34},
        {"max_weight": 6.3, "speed": 17, "durability": 39},
        {"max_weight": 7.5, "speed": 23, "durability": 44},
        {"max_weight": 8.8, "speed": 28, "durability": 49},
    ])
    add_series("Быстрый Байт", [8300, 10800, 14200, 18400, 23400], "bait M", "Река", "Хищник", "Фарм", "Быстрая подмотка", [
        {"max_weight": 3.0, "speed": 0, "durability": 21},
        {"max_weight": 4.0, "speed": 5, "durability": 26},
        {"max_weight": 5.1, "speed": 10, "durability": 31},
        {"max_weight": 6.2, "speed": 15, "durability": 36},
        {"max_weight": 7.2, "speed": 20, "durability": 41},
    ])
    add_series("Береговой Редуктор", [9800, 13500, 18500, 24900, 32500], "spin MH", "Океан", "Хищник", "Универсально", "Береговой джиг", [
        {"max_weight": 5.0, "speed": 13, "durability": 43},
        {"max_weight": 6.6, "speed": 18, "durability": 48},
        {"max_weight": 8.2, "speed": 23, "durability": 53},
        {"max_weight": 9.8, "speed": 28, "durability": 58},
        {"max_weight": 11.4, "speed": 33, "durability": 63},
    ])
    add_series("Солёная Гильза", [10000, 13400, 18100, 23900, 31000], "multi H", "Океан", "Трофейная", "Турнир", "Морская силовая", [
        {"max_weight": 4.6, "speed": 20, "durability": 57},
        {"max_weight": 6.0, "speed": 25, "durability": 62},
        {"max_weight": 7.5, "speed": 30, "durability": 67},
        {"max_weight": 8.9, "speed": 36, "durability": 72},
        {"max_weight": 10.4, "speed": 41, "durability": 77},
    ])
    add_series("Глубинный Ход", [10800, 15200, 21100, 28600, 37600], "bait H", "Океан", "Трофейная", "Прибыль", "Глубинная ловля", [
        {"max_weight": 6.0, "speed": 23, "durability": 64},
        {"max_weight": 7.9, "speed": 28, "durability": 69},
        {"max_weight": 9.8, "speed": 32, "durability": 74},
        {"max_weight": 11.7, "speed": 37, "durability": 79},
        {"max_weight": 13.6, "speed": 42, "durability": 84},
    ])
    add_series("Рифовый Вихрь", [9500, 12600, 16800, 22000, 28300], "spin M", "Остров", "Универсальная", "Универсально", "Рифовая ловля", [
        {"max_weight": 4.0, "speed": 7, "durability": 50},
        {"max_weight": 5.3, "speed": 12, "durability": 55},
        {"max_weight": 6.6, "speed": 17, "durability": 60},
        {"max_weight": 7.9, "speed": 23, "durability": 65},
        {"max_weight": 9.2, "speed": 28, "durability": 70},
    ])
    add_series("Тропик Драг", [11200, 15800, 22100, 30000, 39500], "multi SH", "Остров", "Хищник", "Прибыль", "Тропический джиг", [
        {"max_weight": 6.5, "speed": 17, "durability": 71},
        {"max_weight": 8.5, "speed": 21, "durability": 76},
        {"max_weight": 10.5, "speed": 26, "durability": 81},
        {"max_weight": 12.5, "speed": 30, "durability": 86},
        {"max_weight": 14.5, "speed": 35, "durability": 91},
    ])
    add_series("Трофейный Драг", [12100, 17700, 25200, 34700, 46000], "bait trophy", "Океан", "Трофейная", "Турнир", "Рекорды", [
        {"max_weight": 8.0, "speed": 26, "durability": 82},
        {"max_weight": 10.4, "speed": 31, "durability": 87},
        {"max_weight": 12.8, "speed": 35, "durability": 92},
        {"max_weight": 15.2, "speed": 39, "durability": 97},
        {"max_weight": 17.6, "speed": 44, "durability": 100},
    ])
    add_series("Компакт Про", [9400, 12700, 17000, 22300, 28900], "spin pro", "Остров", "Универсальная", "Универсально", "Профессионал", [
        {"max_weight": 4.2, "speed": 13, "durability": 43},
        {"max_weight": 5.6, "speed": 19, "durability": 48},
        {"max_weight": 6.9, "speed": 24, "durability": 53},
        {"max_weight": 8.2, "speed": 29, "durability": 58},
        {"max_weight": 9.6, "speed": 34, "durability": 63},
    ])
    return data

def build_line_catalog():
    data = []
    def add_series(series, material, region, fish_type, goal, purpose, stats_list, prices):
        tiers = ["I", "II", "III", "IV", "V"]
        for i, price in enumerate(prices):
            item = {
                "series": series,
                "tier": tiers[i],
                "name": f"{series} {tiers[i]}",
                "class": material,
                "region": region,
                "fish_type": fish_type,
                "goal": goal,
                "purpose": purpose,
                "price": float(price),
                "kind": "line",
                "stats": stats_list[i],
                "stats_lvl5": stats_list[-1],
            }
            data.append(item)
    
    add_series("Речной Шелк (Тень)", "Монофил (тёмный)", "Река", "Универсальная", "Универсально", "Маскировка", [
        {"max_weight": 3.5, "visibility": 48, "stretch": 100, "abrasion": 5, "durability": 4},
        {"max_weight": 5.2, "visibility": 46, "stretch": 99, "abrasion": 7, "durability": 12},
        {"max_weight": 7.0, "visibility": 44, "stretch": 98, "abrasion": 10, "durability": 21},
        {"max_weight": 10.4, "visibility": 43, "stretch": 97, "abrasion": 12, "durability": 30},
        {"max_weight": 13.9, "visibility": 41, "stretch": 97, "abrasion": 15, "durability": 38},
    ], [400, 900, 1600, 2800, 4500])
    add_series("Речной Шелк (Броня)", "Монофил усиленный", "Река", "Универсальная", "Фарм", "Прочность", [
        {"max_weight": 3.5, "visibility": 81, "stretch": 86, "abrasion": 54, "durability": 11},
        {"max_weight": 5.2, "visibility": 80, "stretch": 85, "abrasion": 56, "durability": 20},
        {"max_weight": 7.0, "visibility": 78, "stretch": 84, "abrasion": 59, "durability": 28},
        {"max_weight": 10.4, "visibility": 76, "stretch": 83, "abrasion": 61, "durability": 37},
        {"max_weight": 13.9, "visibility": 74, "stretch": 83, "abrasion": 63, "durability": 46},
    ], [400, 1000, 1900, 3200, 5000])
    add_series("Призрак (Тень)", "Флюорокарбон", "Озеро", "Универсальная", "Универсально", "Маскировка", [
        {"max_weight": 3.5, "visibility": 17, "stretch": 57, "abrasion": 17, "durability": 11},
        {"max_weight": 5.2, "visibility": 15, "stretch": 56, "abrasion": 20, "durability": 20},
        {"max_weight": 7.0, "visibility": 13, "stretch": 55, "abrasion": 22, "durability": 28},
        {"max_weight": 10.4, "visibility": 11, "stretch": 54, "abrasion": 24, "durability": 37},
        {"max_weight": 13.9, "visibility": 9, "stretch": 53, "abrasion": 27, "durability": 46},
    ], [400, 900, 1600, 2800, 4500])
    add_series("Призрак (Броня)", "Флюорокарбон усил.", "Река", "Трофейная", "Турнир", "Устойчивость", [
        {"max_weight": 3.5, "visibility": 50, "stretch": 43, "abrasion": 66, "durability": 18},
        {"max_weight": 5.2, "visibility": 48, "stretch": 42, "abrasion": 68, "durability": 27},
        {"max_weight": 7.0, "visibility": 46, "stretch": 41, "abrasion": 71, "durability": 36},
        {"max_weight": 10.4, "visibility": 44, "stretch": 40, "abrasion": 73, "durability": 44},
        {"max_weight": 13.9, "visibility": 43, "stretch": 39, "abrasion": 76, "durability": 53},
    ], [400, 1000, 1800, 3200, 5000])
    add_series("Стальной Канат (Тень)", "Плетёнка", "Река", "Хищник", "Прибыль", "Чувствительность", [
        {"max_weight": 3.5, "visibility": 67, "stretch": 22, "abrasion": 0, "durability": 0},
        {"max_weight": 5.2, "visibility": 65, "stretch": 21, "abrasion": 2, "durability": 9},
        {"max_weight": 7.0, "visibility": 63, "stretch": 20, "abrasion": 5, "durability": 17},
        {"max_weight": 10.4, "visibility": 61, "stretch": 19, "abrasion": 7, "durability": 26},
        {"max_weight": 13.9, "visibility": 59, "stretch": 18, "abrasion": 10, "durability": 35},
    ], [300, 800, 1500, 2600, 4200])
    add_series("Стальной Канат (Броня)", "Плетёнка усиленная", "Река", "Трофейная", "Турнир", "Сила", [
        {"max_weight": 3.5, "visibility": 100, "stretch": 8, "abrasion": 49, "durability": 7},
        {"max_weight": 5.2, "visibility": 98, "stretch": 7, "abrasion": 51, "durability": 16},
        {"max_weight": 7.0, "visibility": 96, "stretch": 6, "abrasion": 54, "durability": 25},
        {"max_weight": 10.4, "visibility": 94, "stretch": 5, "abrasion": 56, "durability": 33},
        {"max_weight": 13.9, "visibility": 93, "stretch": 4, "abrasion": 59, "durability": 42},
    ], [400, 900, 1700, 3000, 4700])
    add_series("Гибрид (Тень)", "Гибрид", "Река", "Универсальная", "Универсально", "Баланс", [
        {"max_weight": 3.5, "visibility": 39, "stretch": 74, "abrasion": 10, "durability": 7},
        {"max_weight": 5.2, "visibility": 37, "stretch": 73, "abrasion": 12, "durability": 16},
        {"max_weight": 7.0, "visibility": 35, "stretch": 72, "abrasion": 15, "durability": 25},
        {"max_weight": 10.4, "visibility": 33, "stretch": 71, "abrasion": 17, "durability": 33},
        {"max_weight": 13.9, "visibility": 31, "stretch": 70, "abrasion": 20, "durability": 42},
    ], [400, 900, 1600, 2800, 4600])
    add_series("Гибрид (Броня)", "Гибрид усиленный", "Океан", "Трофейная", "Турнир", "Баланс", [
        {"max_weight": 3.5, "visibility": 72, "stretch": 60, "abrasion": 59, "durability": 14},
        {"max_weight": 5.2, "visibility": 70, "stretch": 59, "abrasion": 61, "durability": 23},
        {"max_weight": 7.0, "visibility": 69, "stretch": 58, "abrasion": 63, "durability": 32},
        {"max_weight": 10.4, "visibility": 67, "stretch": 57, "abrasion": 66, "durability": 41},
        {"max_weight": 13.9, "visibility": 65, "stretch": 57, "abrasion": 68, "durability": 49},
    ], [400, 1000, 1900, 3200, 5100])
    add_series("Солёный Щит (Тень)", "Монофил морской", "Океан", "Универсальная", "Универсально", "Защита", [
        {"max_weight": 3.5, "visibility": 43, "stretch": 65, "abrasion": 29, "durability": 14},
        {"max_weight": 5.2, "visibility": 41, "stretch": 64, "abrasion": 32, "durability": 23},
        {"max_weight": 7.0, "visibility": 39, "stretch": 63, "abrasion": 34, "durability": 32},
        {"max_weight": 10.4, "visibility": 37, "stretch": 63, "abrasion": 37, "durability": 41},
        {"max_weight": 13.9, "visibility": 35, "stretch": 62, "abrasion": 39, "durability": 49},
    ], [500, 1100, 1900, 3300, 5200])
    add_series("Солёный Щит (Броня)", "Монофил морской усил.", "Океан", "Трофейная", "Турнир", "Защита+", [
        {"max_weight": 3.5, "visibility": 76, "stretch": 51, "abrasion": 78, "durability": 22},
        {"max_weight": 5.2, "visibility": 74, "stretch": 50, "abrasion": 80, "durability": 30},
        {"max_weight": 7.0, "visibility": 72, "stretch": 50, "abrasion": 83, "durability": 39},
        {"max_weight": 10.4, "visibility": 70, "stretch": 49, "abrasion": 85, "durability": 48},
        {"max_weight": 13.9, "visibility": 69, "stretch": 48, "abrasion": 88, "durability": 57},
    ], [500, 1200, 2200, 3700, 5700])
    return data

def build_bait_catalog():
    data = []
    def add_b(series, tier, btype, env, fish_type, goal, durability, max_weight=0, price=0):
        item = {
            "series": series,
            "tier": tier,
            "name": f"{series}{(' ' + tier) if tier else ''}",
            "class": btype,
            "region": env,
            "fish_type": fish_type,
            "goal": goal,
            "purpose": "Наживка",
            "price": float(price),
            "kind": "bait",
            "stats_lvl5": {"durability": durability, "max_weight": max_weight},
        }
        data.append(item)
    
    add_b("Черви", "", "Натуральная", "Пресные водоемы", "Любая", "Универсально", 0, 0, 200)
    add_b("Мотыль", "", "Натуральная", "Пресные водоемы", "Нехищная", "Универсально", 0, 0, 200)
    add_b("Опарыш", "", "Натуральная", "Пресные водоемы", "Нехищная", "Универсально", 0, 0, 200)
    add_b("Кузнечик", "", "Натуральная", "Пресные водоемы", "Любая", "Универсально", 0, 0, 200)
    add_b("Наживка ростительная S", "", "Растительная", "Пресные водоемы", "Нехищная", "Универсально", 0, 0, 200)
    add_b("Ростительная М", "", "Растительная", "Пресные водоемы", "Нехищная", "Универсально", 0, 0, 200)
    add_b("Растительная L", "", "Растительная", "Пресные водоемы", "Нехищная", "Универсально", 0, 0, 200)
    add_b("Мясная S", "", "Мясная", "Любые водоемы", "Хищная", "Универсально", 0, 0, 400)
    add_b("Мясная М", "", "Мясная", "Любые водоемы", "Хищная", "Универсально", 0, 0, 400)
    add_b("Мясная L", "", "Мясная", "Любые водоемы", "Хищная", "Универсально", 0, 0, 400)
    add_b("Наживка Рыбная S", "", "Рыбная", "Открытый океан", "Хищная", "Универсально", 0, 0, 200)
    add_b("Наживка Рыбная М", "", "Рыбная", "Открытый океан", "Хищная", "Универсально", 0, 0, 200)
    add_b("Наживка Рыбная L", "", "Рыбная", "Открытый океан", "Хищная", "Универсально", 0, 0, 200)
    add_b("Наживка ракообразная S", "", "Ракообразная", "Любые водоемы", "Любая", "Универсально", 0, 0, 500)
    add_b("Наживка ракообразная M", "", "Ракообразная", "Любые водоемы", "Любая", "Универсально", 0, 0, 500)
    add_b("Наживка ракообразная L", "", "Ракообразная", "Любые водоемы", "Любая", "Универсально", 0, 0, 500)
    add_b("Наживка нейтральный S", "", "Нейтральная", "Любые водоемы", "Любая", "Универсально", 0, 0, 500)
    add_b("Наживка нейтральный M", "", "Нейтральная", "Любые водоемы", "Любая", "Универсально", 0, 0, 500)
    add_b("Наживка нейтральный L", "", "Нейтральная", "Любые водоемы", "Любая", "Универсально", 0, 0, 500)
    
    add_b("Наживка Блесна береговая", "", "Блесна", "Открытый океан", "Хищная", "Универсально", 90, 0, 4500)
    add_b("Наживка пилькер глубиный", "", "Пилькер", "Открытый океан", "Хищная", "Прибыль", 75, 0, 3800)
    add_b("Наживка воблер рифовый", "", "Воблер", "Тропический риф", "Любая", "Универсально", 95, 0, 8400)
    add_b("Наживка джигер тропический", "", "Джиггер", "Тропический риф", "Хищная", "Прибыль", 80, 0, 6000)
    add_b("Наживка муха стелс", "", "Муха", "Любые водоемы", "Нехищная", "Турнир", 120, 0, 11300)
    add_b("Наживка силикон универсальный", "", "Силикон", "Любые водоемы", "Хищная", "Прибыль", 110, 0, 11000)
    add_b("Наживка кренк стелс", "", "Крэнк", "Любые водоемы", "Любая", "Турнир", 90, 0, 10200)
    add_b("Наживка Колебалка Силовая", "", "Колебалка", "Любые водоемы", "Хищники", "Прибыль", 70, 0, 7000)
    return data
