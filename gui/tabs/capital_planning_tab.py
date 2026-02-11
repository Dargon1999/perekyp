import math
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QFrame, QGridLayout, QScrollArea, QLineEdit,
    QSlider, QGraphicsDropShadowEffect, QFileDialog, QDialog,
    QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QIcon

from gui.custom_dialogs import StyledDialogBase

class AchievementsDialog(StyledDialogBase):
    def __init__(self, parent, achievements, unlocked_ids):
        super().__init__(parent, "🏆 Достижения", width=600)
        self.resize(600, 700)
        self.setMinimumSize(500, 600)
        self.achievements = achievements
        self.unlocked_ids = unlocked_ids
        self.setup_ui()
        
    def setup_ui(self):
        # Progress
        lbl_progress = QLabel(f"Прогресс: {len(self.unlocked_ids)} / {len(self.achievements)}")
        lbl_progress.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.success_color}; margin-bottom: 10px;")
        self.content_layout.addWidget(lbl_progress)

        # List Container (Scroll Area instead of QListWidget for variable height)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container.setStyleSheet(f"background-color: {self.input_bg}; border-radius: 8px;")
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(1) # Divider lines
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        for i, ach in enumerate(self.achievements):
            is_unlocked = ach["id"] in self.unlocked_ids
            
            # Item Widget
            item_widget = QWidget()
            item_widget.setStyleSheet(f"background-color: transparent; border-bottom: 1px solid {self.input_border};")
            
            h = QHBoxLayout(item_widget)
            h.setContentsMargins(15, 15, 15, 15)
            h.setSpacing(15)
            
            # Icon
            icon_lbl = QLabel(ach["icon"])
            icon_lbl.setStyleSheet("font-size: 32px; border: none;")
            if not is_unlocked:
                icon_lbl.setStyleSheet(f"font-size: 32px; color: #7f8c8d; border: none;") 
            
            # Text
            text_layout = QVBoxLayout()
            title = QLabel(ach["title"])
            title_color = self.success_color if is_unlocked else self.text_color
            title.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {title_color}; border: none;")
            
            desc = QLabel(ach["desc"])
            desc.setStyleSheet(f"color: {self.secondary_text_color}; font-size: 12px; border: none;")
            desc.setWordWrap(True)
            desc.setToolTip(ach["desc"]) # Tooltip for full info
            
            text_layout.addWidget(title)
            text_layout.addWidget(desc)
            
            h.addWidget(icon_lbl)
            h.addLayout(text_layout)
            h.addStretch()
            
            # Status Icon
            if is_unlocked:
                check = QLabel("✅")
                check.setStyleSheet("border: none;")
                h.addWidget(check)
            else:
                lock = QLabel("🔒")
                lock.setStyleSheet("opacity: 0.5; border: none;")
                h.addWidget(lock)
            
            container_layout.addWidget(item_widget)
            
        container_layout.addStretch()
        scroll.setWidget(container)
        self.content_layout.addWidget(scroll)
        
        # Close button
        btn_close = self.create_button("Закрыть", "primary", self.accept)
        self.content_layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignCenter)

class DNADetailsDialog(StyledDialogBase):
    def __init__(self, parent, dna_type, dna_desc, roi, frozen, eff_score):
        super().__init__(parent, "🧬 DNA Профиль: Подробности", width=550)
        self.resize(550, 600)
        
        # Scroll Area for small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        self.inner_layout = QVBoxLayout(content)
        self.inner_layout.setSpacing(15)
        
        # Header
        lbl_title = QLabel(dna_type)
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: #9b59b6; margin-bottom: 10px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setWordWrap(True)
        self.inner_layout.addWidget(lbl_title)
        
        # Desc
        lbl_desc = QLabel(dna_desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"font-size: 14px; color: {self.secondary_text_color}; margin-bottom: 20px;")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inner_layout.addWidget(lbl_desc)
        
        # Stats Breakdown
        stats_group = QFrame()
        stats_group.setStyleSheet(f"background-color: {self.input_bg}; border-radius: 8px; padding: 10px;")
        stats_layout = QVBoxLayout(stats_group)
        
        stats_layout.addWidget(QLabel("📊 Параметры ДНК:"))
        stats_layout.addWidget(QLabel(f"• {roi}"))
        stats_layout.addWidget(QLabel(f"• {frozen}"))
        stats_layout.addWidget(QLabel(f"• Индекс Эффективности: {eff_score}"))
        
        self.inner_layout.addWidget(stats_group)
        
        # Inheritance Preview
        self.inner_layout.addSpacing(10)
        lbl_inh = QLabel("🧬 Наследование (В разработке)")
        lbl_inh.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.success_color};")
        self.inner_layout.addWidget(lbl_inh)
        
        inh_group = QFrame()
        inh_group.setStyleSheet(f"background-color: {self.input_bg}; border-radius: 8px; padding: 10px;")
        inh_layout = QVBoxLayout(inh_group)
        
        inh_layout.addWidget(QLabel("При создании нового персонажа вы получите:"))
        inh_layout.addWidget(QLabel("✅ Бонус к стартовому капиталу: +$5,000"))
        inh_layout.addWidget(QLabel("✅ Репутация торговца: Уровень 2"))
        inh_layout.addWidget(QLabel("✅ Скидка на аренду: 5%"))
        
        self.inner_layout.addWidget(inh_group)
        self.inner_layout.addStretch()
        
        scroll.setWidget(content)
        self.content_layout.addWidget(scroll)
        
        # Close Button
        btn = self.create_button("Закрыть", "primary", self.accept)
        self.content_layout.addWidget(btn)

class ROIDetailsDialog(StyledDialogBase):
    def __init__(self, parent):
        super().__init__(parent, "📊 Индекс ROI: Справка", width=550)
        self.resize(550, 500)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        
        # Title
        lbl_title = QLabel("Что такое ROI?")
        lbl_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {self.accent_color};")
        layout.addWidget(lbl_title)
        
        # Definition
        lbl_def = QLabel("ROI (Return on Investment) — это коэффициент окупаемости инвестиций. Он показывает, насколько выгодной была сделка.")
        lbl_def.setWordWrap(True)
        lbl_def.setStyleSheet(f"font-size: 14px; color: {self.secondary_text_color}; margin-bottom: 10px;")
        layout.addWidget(lbl_def)
        
        # Formula
        formula_frame = QFrame()
        formula_frame.setStyleSheet(f"background-color: {self.input_bg}; border-radius: 8px; padding: 15px;")
        f_layout = QVBoxLayout(formula_frame)
        
        # Improved Formula Display
        f_lbl = QLabel("ROI = (Прибыль / Вложения) × 100%")
        f_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_lbl.setWordWrap(True)
        f_lbl.setStyleSheet("font-size: 18px; font-weight: bold; font-family: monospace; color: #f1c40f;")
        f_layout.addWidget(f_lbl)
        
        layout.addWidget(formula_frame)
        
        # Example
        lbl_ex = QLabel("Пример:\nКупили за $100, продали за $150.\nПрибыль = $50.\nROI = ($50 / $100) × 100% = 50%")
        lbl_ex.setStyleSheet(f"color: {self.text_color}; margin-top: 10px; font-family: monospace;")
        lbl_ex.setWordWrap(True)
        layout.addWidget(lbl_ex)
        
        layout.addStretch()
        scroll.setWidget(content)
        self.content_layout.addWidget(scroll)
        
        # Close Button
        btn = self.create_button("Понятно", "primary", self.accept)
        self.content_layout.addWidget(btn)

class CapitalPlanningTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        
        self.init_ui()
        self.is_initialized = False
        # self.refresh_data() # Deferred loading

    def showEvent(self, event):
        if not self.is_initialized:
            self.refresh_data()
            self.is_initialized = True
        super().showEvent(event)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)

        # Top Toolbar
        self.create_toolbar()

        # Scroll Area for the content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(25)
        
        scroll.setWidget(self.content_widget)
        self.layout.addWidget(scroll)

        # 1. Goal Section
        self.create_goal_section()
        
        # 2. DNA Profile & Efficiency Index (Side by Side)
        self.create_stats_row()
        
        # 3. Smart Advisor
        self.create_advisor_section()
        
        # 4. Simulator
        self.create_simulator_section()

    def create_card(self, title, add_shadow=True):
        """Creates a modern card-style container with optional shadow."""
        card = QFrame()
        card.setObjectName("Card")
        # Modern Card Style
        card.setStyleSheet("""
            #Card {
                background-color: #2b2b2b;
                border-radius: 12px;
                border: 1px solid #3d3d3d;
            }
        """)
        
        if add_shadow:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 4)
            card.setGraphicsEffect(shadow)
            
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        if title:
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
            layout.addWidget(lbl_title)
            layout.addSpacing(10)
            
        return card, layout

    def create_goal_section(self):
        self.goal_card, layout = self.create_card("🎯 Финансовая цель")
        
        # Top row: Goal Input and Current Status
        top_layout = QHBoxLayout()
        
        # Goal Input
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText("Введите цель ($)")
        self.goal_input.setFixedWidth(150)
        self.goal_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
                font-size: 16px;
                color: #fff;
            }
            QLineEdit:focus { border: 1px solid #3498db; }
        """)
        
        self.btn_save_goal = QPushButton("Сохранить")
        self.btn_save_goal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_goal.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_save_goal.clicked.connect(self.save_goal)
        
        top_layout.addWidget(QLabel("Цель:"))
        top_layout.addWidget(self.goal_input)
        top_layout.addWidget(self.btn_save_goal)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # Progress Info
        self.lbl_current = QLabel("Текущий капитал: $0")
        self.lbl_current.setStyleSheet("font-size: 14px; color: #ddd;")
        
        self.lbl_remaining = QLabel("Осталось: $0")
        self.lbl_remaining.setStyleSheet("font-size: 14px; color: #ddd;")
        
        self.lbl_prediction = QLabel("⏳ При текущем темпе: неизвестно")
        self.lbl_prediction.setStyleSheet("color: #aaa; font-style: italic; margin-top: 5px;")
        
        info_layout = QHBoxLayout()
        info_layout.addWidget(self.lbl_current)
        info_layout.addSpacing(20)
        info_layout.addWidget(self.lbl_remaining)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #1e1e1e;
                border-radius: 10px;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.lbl_prediction)
        
        self.content_layout.addWidget(self.goal_card)

    def create_toolbar(self):
        toolbar_layout = QHBoxLayout()
        
        # Focus Mode Button
        self.btn_focus = QPushButton("🔍 Фокус")
        self.btn_focus.setCheckable(True)
        self.btn_focus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_focus.setStyleSheet("""
            QPushButton {
                background-color: #34495e; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:checked { background-color: #e67e22; }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        self.btn_focus.clicked.connect(self.toggle_focus_mode)
        
        # Export Button
        self.btn_export = QPushButton("💾 Экспорт")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        self.btn_export.clicked.connect(self.export_report)
        
        # Achievements Button
        self.btn_achievements = QPushButton("🏆 Достижения")
        self.btn_achievements.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_achievements.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        self.btn_achievements.clicked.connect(self.show_achievements)
        
        # Help Button
        self.btn_help = QPushButton("❓ Помощь")
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_help.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        self.btn_help.clicked.connect(self.show_help)
        
        toolbar_layout.addWidget(self.btn_focus)
        toolbar_layout.addWidget(self.btn_export)
        toolbar_layout.addWidget(self.btn_achievements)
        toolbar_layout.addWidget(self.btn_help)
        toolbar_layout.addStretch()
        
        self.layout.addLayout(toolbar_layout)

    def create_stats_row(self):
        self.stats_container = QWidget()
        row_layout = QHBoxLayout(self.stats_container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        # DNA Profile
        dna_card, dna_layout = self.create_card("🧬 DNA Профиль")
        self.lbl_dna_type = QLabel("Анализ...")
        self.lbl_dna_type.setStyleSheet("font-size: 20px; font-weight: bold; color: #9b59b6;")
        self.lbl_dna_desc = QLabel("Совершите больше сделок для анализа")
        self.lbl_dna_desc.setWordWrap(True)
        self.lbl_dna_desc.setStyleSheet("color: #ccc;")
        
        btn_dna_info = QPushButton("ℹ️ Подробнее")
        btn_dna_info.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dna_info.setStyleSheet("background-color: transparent; color: #3498db; border: none; text-align: left; font-weight: bold;")
        btn_dna_info.clicked.connect(self.show_dna_details)
        
        dna_layout.addWidget(self.lbl_dna_type)
        dna_layout.addWidget(self.lbl_dna_desc)
        dna_layout.addWidget(btn_dna_info)
        dna_layout.addStretch()
        
        # Efficiency Index
        eff_card, eff_layout = self.create_card("📊 Индекс Эффективности")
        self.lbl_eff_score = QLabel("0 / 100")
        self.lbl_eff_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_eff_score.setStyleSheet("font-size: 36px; font-weight: bold; color: #f1c40f;")
        
        eff_details_layout = QGridLayout()
        self.lbl_roi_stat = QLabel("ROI: 0%")
        self.lbl_frozen_stat = QLabel("Заморозка: 0%")
        
        # Style labels
        for lbl in [self.lbl_roi_stat, self.lbl_frozen_stat]:
            lbl.setStyleSheet("color: #bbb; font-size: 13px;")
            
        eff_details_layout.addWidget(self.lbl_roi_stat, 0, 0)
        eff_details_layout.addWidget(self.lbl_frozen_stat, 0, 1)
        
        btn_roi_info = QPushButton("ℹ️ Формула ROI")
        btn_roi_info.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_roi_info.setStyleSheet("background-color: transparent; color: #3498db; border: none; text-align: left; font-weight: bold;")
        btn_roi_info.clicked.connect(self.show_roi_details)
        
        eff_layout.addWidget(self.lbl_eff_score)
        eff_layout.addLayout(eff_details_layout)
        eff_layout.addWidget(btn_roi_info)
        
        row_layout.addWidget(dna_card)
        row_layout.addWidget(eff_card)
        self.content_layout.addWidget(self.stats_container)

    def create_advisor_section(self):
        self.advisor_card, layout = self.create_card("🦉 Умный Советник")
        self.advisor_content = QLabel("Загрузка советов...")
        self.advisor_content.setWordWrap(True)
        self.advisor_content.setStyleSheet("font-size: 14px; line-height: 1.4; color: #ddd;")
        layout.addWidget(self.advisor_content)
        self.content_layout.addWidget(self.advisor_card)

    def create_simulator_section(self):
        self.simulator_card, layout = self.create_card("🧪 Симулятор «А что если?»")
        
        # Grid for inputs
        controls_layout = QGridLayout()
        controls_layout.setSpacing(15)
        
        # Input: Investment
        self.sim_invest = QLineEdit()
        self.sim_invest.setPlaceholderText("Вложения ($)")
        self.sim_invest.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444; border-radius: 5px; padding: 5px; color: white;")
        self.sim_invest.textChanged.connect(self.run_simulation)
        
        # Slider: ROI
        self.sim_roi = QSlider(Qt.Orientation.Horizontal)
        self.sim_roi.setRange(1, 100) # 1% to 100%
        self.sim_roi.setValue(15)
        self.sim_roi.valueChanged.connect(self.run_simulation)
        
        self.lbl_sim_roi_display = QLabel("ROI: 15%")
        
        # Slider: Cycles
        self.sim_cycles = QSlider(Qt.Orientation.Horizontal)
        self.sim_cycles.setRange(1, 30)
        self.sim_cycles.setValue(5)
        self.sim_cycles.valueChanged.connect(self.run_simulation)
        
        self.lbl_sim_cycles_display = QLabel("Оборотов: 5")

        controls_layout.addWidget(QLabel("Вложения:"), 0, 0)
        controls_layout.addWidget(self.sim_invest, 0, 1)
        
        controls_layout.addWidget(self.lbl_sim_roi_display, 1, 0)
        controls_layout.addWidget(self.sim_roi, 1, 1)
        
        controls_layout.addWidget(self.lbl_sim_cycles_display, 2, 0)
        controls_layout.addWidget(self.sim_cycles, 2, 1)
        
        layout.addLayout(controls_layout)
        
        layout.addSpacing(15)
        self.lbl_sim_result = QLabel("Итог: $0 (+ $0)")
        self.lbl_sim_result.setStyleSheet("font-size: 18px; font-weight: bold; color: #2ecc71; margin-top: 10px;")
        layout.addWidget(self.lbl_sim_result)
        
        self.content_layout.addWidget(self.simulator_card)

    # --- Logic ---

    def calculate_net_worth(self):
        """Calculates total liquid cash + inventory value."""
        total = 0.0
        
        # Clothes
        clothes_stats = self.data_manager.get_category_stats("clothes")
        # Net Worth = Current Balance (Liquid) + Inventory Value (Assets @ Buy Price)
        inventory_value = sum(float(item.get("buy_price", 0)) for item in self.data_manager.get_clothes_inventory())
        total += clothes_stats.get("current_balance", 0) + inventory_value
        
        # Car Rental
        rental_stats = self.data_manager.get_category_stats("car_rental")
        total += rental_stats.get("current_balance", 0)
        
        # Mining
        mining_stats = self.data_manager.get_category_stats("mining")
        total += mining_stats.get("current_balance", 0)
        
        return total

    def refresh_data(self):
        planning_data = self.data_manager.get_capital_planning_data()
        if not planning_data: return

        # 1. Goal Logic
        target = planning_data.get("target_amount", 0.0)
        # Only update text if not focused to avoid overwriting user typing
        if not self.goal_input.hasFocus():
            self.goal_input.setText(str(int(target)) if target else "")
        
        current_capital = self.calculate_net_worth()
        self.lbl_current.setText(f"Текущий капитал: ${current_capital:,.2f}")
        
        if target > 0:
            remaining = max(0, target - current_capital)
            progress = min(100, (current_capital / target) * 100) if target else 0
            
            self.lbl_remaining.setText(f"Осталось: ${remaining:,.2f}")
            self.progress_bar.setValue(int(progress))
            
            # Prediction logic
            avg_daily_profit = self.calculate_avg_daily_profit()
            if avg_daily_profit > 0 and remaining > 0:
                days_left = math.ceil(remaining / avg_daily_profit)
                self.lbl_prediction.setText(f"⏳ При текущем темпе цель будет достигнута примерно за {days_left} дн.")
            elif remaining <= 0:
                self.lbl_prediction.setText("🎉 Цель достигнута!")
            else:
                self.lbl_prediction.setText("⏳ При текущем темпе: невозможно (прибыль <= 0)")
        else:
            self.lbl_remaining.setText("Осталось: -")
            self.progress_bar.setValue(0)
            self.lbl_prediction.setText("Установите цель, чтобы увидеть прогноз.")

        # 2. DNA & Stats
        self.analyze_dna()
        self.update_advisor()
        
        # 3. Simulator (Init)
        if not self.sim_invest.text():
            self.sim_invest.setText(str(int(current_capital)))

        # 4. Check Achievements
        self.check_achievements()

    def toggle_focus_mode(self):
        enabled = self.btn_focus.isChecked()
        
        # Hide/Show complex sections
        self.stats_container.setVisible(not enabled)
        self.advisor_card.setVisible(not enabled)
        self.simulator_card.setVisible(not enabled)
        
        # In focus mode, we hide the goal input and save button, showing only progress.
        self.goal_input.setVisible(not enabled)
        self.btn_save_goal.setVisible(not enabled)

    def export_report(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Экспорт отчета", "capital_report.txt", "Text Files (*.txt)")
        if not filename: return
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"=== ОТЧЕТ PO КАПИТАЛУ ({datetime.now().strftime('%d.%m.%Y')}) ===\n\n")
                
                # Goal
                target = float(self.goal_input.text() or 0)
                current = self.calculate_net_worth()
                f.write(f"Цель: ${target:,.2f}\n")
                f.write(f"Текущий капитал: ${current:,.2f}\n")
                if target > 0:
                    prog = (current / target) * 100
                    f.write(f"Прогресс: {prog:.1f}%\n")
                f.write("\n")
                
                # Stats
                f.write(f"DNA Тип: {self.lbl_dna_type.text()}\n")
                f.write(f"Индекс эффективности: {self.lbl_eff_score.text()}\n")
                f.write(f"{self.lbl_roi_stat.text()}\n")
                f.write(f"{self.lbl_frozen_stat.text()}\n")
                f.write("\n")
                
                # Advisor
                f.write("=== СОВЕТЫ ===\n")
                # Strip HTML tags for text export
                tips = self.advisor_content.text().replace("<b>", "").replace("</b>", "").replace("<br>", "\n")
                f.write(tips)
                f.write("\n")
                
            QMessageBox.information(self, "Успех", "Отчет успешно сохранен!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчет: {e}")

    def show_achievements(self):
        unlocked_ids = self.data_manager.get_achievements()
        
        achievements = [
            # Wealth
            {"id": "first_blood", "title": "Первая прибыль", "desc": "Совершите первую прибыльную сделку.", "icon": "🩸"},
            {"id": "millionaire", "title": "Миллионер", "desc": "Достичь капитала $1,000,000.", "icon": "💰"},
            {"id": "multi_millionaire", "title": "Мультимиллионер", "desc": "Достичь капитала $10,000,000.", "icon": "🏦"},
            {"id": "billionaire", "title": "Миллиардер", "desc": "Достичь капитала $100,000,000.", "icon": "🚀"},
            
            # Clothes / Reselling
            {"id": "wardrobe_novice", "title": "Модник", "desc": "Купите 10 вещей.", "icon": "👕"},
            {"id": "wardrobe_master", "title": "Владелец бутика", "desc": "Купите 50 вещей.", "icon": "👗"},
            {"id": "clean_hands", "title": "Чистые руки", "desc": "10 сделок подряд без убытка.", "icon": "✨"},
            {"id": "shark", "title": "Акула бизнеса", "desc": "ROI одной сделки > 50%.", "icon": "🦈"},
            {"id": "sniper", "title": "Снайпер", "desc": "ROI одной сделки > 100%.", "icon": "🎯"},
            {"id": "hoarder", "title": "Плюшкин", "desc": "Накопить товара на $10,000.", "icon": "📦"},
            {"id": "warehouse_king", "title": "Король склада", "desc": "Накопить товара на $100,000.", "icon": "🏭"},
            {"id": "veteran_reseller", "title": "Ветеран рынка", "desc": "Продайте 100 вещей.", "icon": "🏷️"},
            
            # Cars
            {"id": "fleet_manager", "title": "Автодилер", "desc": "10 сделок с авто.", "icon": "🚗"},
            {"id": "magnate", "title": "Магнат", "desc": "50 сделок с авто.", "icon": "🏎️"},
            {"id": "high_roller", "title": "Крупная рыба", "desc": "Сделка с авто > $100,000.", "icon": "💎"},
            
            # Mining
            {"id": "miner", "title": "Шахтер", "desc": "10 записей о майнинге.", "icon": "⛏️"},
            {"id": "crypto_lord", "title": "Криптобарон", "desc": "100 записей о майнинге.", "icon": "💾"},
            
            # Misc
            {"id": "frozen_king", "title": "Снежная королева", "desc": "Заморожено > 80% капитала.", "icon": "❄️"},
            {"id": "safe_hands", "title": "Ликвидность", "desc": "0% замороженного капитала.", "icon": "💧"},
            {"id": "lesson_learned", "title": "Горький опыт", "desc": "Закройте сделку в минус.", "icon": "📉"}
        ]
        
        dlg = AchievementsDialog(self, achievements, unlocked_ids)
        dlg.exec()

    def check_achievements(self):
        # Check conditions and unlock if needed
        unlocked = []
        
        # Data Gathering
        sold = self.data_manager.get_clothes_sold()
        inventory = self.data_manager.get_clothes_inventory()
        car_txs = self.data_manager.get_transactions("car_rental")
        mining_txs = self.data_manager.get_transactions("mining")
        net_worth = self.calculate_net_worth()
        inventory_val = sum(float(i.get("buy_price", 0)) for i in inventory)
        
        # --- 1. Wealth ---
        if net_worth >= 1000000: unlocked.append("millionaire")
        if net_worth >= 10000000: unlocked.append("multi_millionaire")
        if net_worth >= 100000000: unlocked.append("billionaire")
        
        # --- 2. Clothes / Reselling ---
        if len(sold) > 0:
            for item in sold:
                buy = float(item.get("buy_price", 0))
                sell = float(item.get("sell_price", 0))
                profit = sell - buy
                
                if profit > 0:
                    unlocked.append("first_blood")
                elif profit < 0:
                    unlocked.append("lesson_learned")
                    
                if buy > 0:
                    roi = profit / buy
                    if roi > 0.5: unlocked.append("shark")
                    if roi > 1.0: unlocked.append("sniper")
        
        # Streaks & Counts
        if len(sold) >= 10:
            streak = 0
            max_streak = 0
            for item in sold:
                if float(item.get("sell_price", 0)) >= float(item.get("buy_price", 0)):
                    streak += 1
                else:
                    streak = 0
                max_streak = max(max_streak, streak)
            if max_streak >= 10: unlocked.append("clean_hands")
            
        if len(sold) >= 100: unlocked.append("veteran_reseller")
        
        # Inventory Counts (approximate "bought" count as inventory + sold)
        total_bought = len(inventory) + len(sold)
        if total_bought >= 10: unlocked.append("wardrobe_novice")
        if total_bought >= 50: unlocked.append("wardrobe_master")
        
        if inventory_val > 10000: unlocked.append("hoarder")
        if inventory_val > 100000: unlocked.append("warehouse_king")
        
        # --- 3. Cars ---
        if len(car_txs) >= 10: unlocked.append("fleet_manager")
        if len(car_txs) >= 50: unlocked.append("magnate")
        
        for t in car_txs:
            if abs(float(t.get("amount", 0))) > 100000:
                unlocked.append("high_roller")
                break
                
        # --- 4. Mining ---
        if len(mining_txs) >= 10: unlocked.append("miner")
        if len(mining_txs) >= 100: unlocked.append("crypto_lord")
        
        # --- 5. Misc ---
        if net_worth > 0:
            frozen_ratio = inventory_val / net_worth
            if frozen_ratio > 0.8: unlocked.append("frozen_king")
            if frozen_ratio == 0 and net_worth > 1000: unlocked.append("safe_hands")
            
        # Save new unlocks
        current_unlocked = self.data_manager.get_achievements()
        new_unlocks = False
        for ach_id in set(unlocked): # Use set to avoid duplicates
            if ach_id not in current_unlocked:
                self.data_manager.unlock_achievement(ach_id)
                new_unlocks = True
                
        if new_unlocks:
            # Could trigger a toast here if we had one
            pass

    def save_goal(self):
        try:
            val = float(self.goal_input.text())
        except ValueError:
            val = 0.0
            
        data = self.data_manager.get_capital_planning_data()
        data["target_amount"] = val
        self.data_manager.update_capital_planning_data(data)
        self.refresh_data()

    def calculate_avg_daily_profit(self):
        # Analyze last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        total_profit = 0
        
        # Clothes Profit
        sold = self.data_manager.get_clothes_sold()
        for item in sold:
            try:
                s_date_str = item.get("sell_date", "")
                if not s_date_str: continue
                # Handle formats
                if "." in s_date_str: s_date = datetime.strptime(s_date_str, "%d.%m.%Y")
                else: s_date = datetime.strptime(s_date_str, "%Y-%m-%d")
                
                if start_date <= s_date <= end_date:
                    profit = float(item.get("sell_price", 0)) - float(item.get("buy_price", 0))
                    total_profit += profit
            except: pass
            
        # Other categories (Car, Mining)
        # We need to scan transactions for income/expense
        for cat in ["car_rental", "mining"]:
            txs = self.data_manager.get_transactions(cat)
            for t in txs:
                try:
                    t_date_str = t.get("date", "")
                    if "." in t_date_str: t_date = datetime.strptime(t_date_str, "%d.%m.%Y")
                    else: t_date = datetime.strptime(t_date_str, "%Y-%m-%d")
                    
                    if start_date <= t_date <= end_date:
                        total_profit += float(t.get("amount", 0))
                except: pass
                
        return total_profit / 30

    def analyze_dna(self):
        # Simple heuristic analysis
        sold = self.data_manager.get_clothes_sold()
        
        total_trades = len(sold)
        total_margin = 0
        
        for item in sold:
            buy = float(item.get("buy_price", 0))
            sell = float(item.get("sell_price", 0))
            if buy > 0:
                margin = (sell - buy) / buy
                total_margin += margin
                
        avg_margin = (total_margin / total_trades) * 100 if total_trades else 0
        
        # Determine DNA Type
        dna_type = "🌱 Начинающий"
        desc = "Мало данных для анализа."
        
        if total_trades > 0:
            if total_trades > 20 and avg_margin < 20:
                dna_type = "⚡ Скальпер"
                desc = "Быстрые сделки, небольшой навар. Твоя сила в обороте!"
            elif avg_margin > 40:
                dna_type = "🦁 Снайпер"
                desc = "Редкие сделки, но с огромной прибылью. Ты умеешь ждать."
            elif total_trades > 10:
                dna_type = "⚖️ Трейдер"
                desc = "Хороший баланс между риском и прибылью."
            
        self.lbl_dna_type.setText(dna_type)
        self.lbl_dna_desc.setText(desc)
        
        # Efficiency Score Calculation
        # Score = (ROI * 0.5) + (Activity * 0.2) + (Safety * 0.3)
        roi_score = min(100, avg_margin * 2)
        activity_score = min(100, total_trades * 1.5)
        
        # Safety: inverse of frozen capital ratio
        inventory_val = sum(float(i.get("buy_price", 0)) for i in self.data_manager.get_clothes_inventory())
        net_worth = self.calculate_net_worth()
        frozen_ratio = (inventory_val / net_worth) if net_worth else 0
        safety_score = max(0, 100 - (frozen_ratio * 100))
        
        score = int((roi_score * 0.5) + (activity_score * 0.2) + (safety_score * 0.3))
        self.lbl_eff_score.setText(f"{score} / 100")
        
        self.lbl_roi_stat.setText(f"ROI: {avg_margin:.1f}%")
        self.lbl_frozen_stat.setText(f"Заморозка: {frozen_ratio*100:.1f}%")

    def update_advisor(self):
        tips = []
        net_worth = self.calculate_net_worth()
        
        # --- 0. Role Identification & Context ---
        # Determine main source of income
        clothes_profit = 0
        mining_profit = 0
        cars_profit = 0
        
        # Simple heuristic based on transaction counts for now
        clothes_cnt = len(self.data_manager.get_clothes_sold())
        mining_cnt = len(self.data_manager.get_transactions("mining"))
        cars_cnt = len(self.data_manager.get_transactions("car_rental"))
        
        role = "Новичок"
        if clothes_cnt > max(mining_cnt, cars_cnt) and clothes_cnt > 5: role = "Трейдер"
        elif mining_cnt > max(clothes_cnt, cars_cnt) and mining_cnt > 5: role = "Майнер"
        elif cars_cnt > max(clothes_cnt, mining_cnt) and cars_cnt > 5: role = "Автодилер"
        
        tips.append(f"👤 <b>Ваша роль: {role}</b>")
        
        # --- 1. Newbie Guide (Step-by-Step) ---
        if net_worth < 50000 and clothes_cnt < 5:
            tips.append("🎓 <b>Обучение: Первые шаги</b>")
            tips.append("1. 🏪 <b>Рынок:</b> Купите дешевую одежду на рынке (поиск дешевле $500).")
            tips.append("2. 🏷️ <b>Наценка:</b> Выставьте её с наценкой 10-20%.")
            tips.append("3. 💰 <b>Капитал:</b> Не тратьте всё сразу, держите 30% кэша на случай выгодных предложений.")
        
        # --- 2. Frozen Capital Analysis ---
        inventory_val = sum(float(i.get("buy_price", 0)) for i in self.data_manager.get_clothes_inventory())
        frozen_pct = (inventory_val / net_worth * 100) if net_worth else 0
        
        if frozen_pct > 60:
            tips.append(f"⚠️ <b>Риск: Высокая заморозка ({frozen_pct:.0f}%)</b><br>Большая часть денег в товаре. Снизьте цены на старый товар (более 3 дней), чтобы вернуть деньги в оборот.")
        elif frozen_pct < 10 and net_worth > 5000:
            tips.append("💡 <b>Совет: Деньги должны работать</b><br>У вас много свободного кэша. Рассмотрите покупку видеокарт для майнинга или более дорогих авто.")
            
        # --- 3. ROI Analysis & Event Integration ---
        sold = self.data_manager.get_clothes_sold()
        if sold:
            last_5 = sold[-5:]
            recent_margin_sum = 0
            count = 0
            for item in last_5:
                buy = float(item.get("buy_price", 0))
                sell = float(item.get("sell_price", 0))
                if buy > 0: 
                    recent_margin_sum += (sell - buy) / buy
                    count += 1
            
            if count > 0:
                recent_margin = (recent_margin_sum / count) * 100
                if recent_margin < 10:
                    tips.append("📉 <b>Внимание: Падает маржа</b><br>Последние сделки принесли менее 10%. Рынок насыщен? Попробуйте сменить категорию товара.")
                elif recent_margin > 50:
                    tips.append("🔥 <b>Отлично: Высокая эффективность</b><br>Ваш ROI > 50%. Попробуйте масштабироваться: покупайте более дорогие лоты.")
        
        # --- 4. Role-Specific Tips ---
        if role == "Майнер":
            tips.append("⛏️ <b>Совет майнеру:</b> Следите за курсом биткоина. Продавайте только на пиках.")
        elif role == "Автодилер":
            tips.append("🚗 <b>Совет дилеру:</b> Аренда авто выгодна в долгосрок. Проверяйте состояние авто перед покупкой.")
        
        if not tips:
            tips.append("✅ <b>Всё отлично!</b><br>Твоя стратегия работает эффективно. Продолжай в том же духе.")
            
        self.advisor_content.setText("<br><br>".join(tips))

    def run_simulation(self):
        try:
            invest = float(self.sim_invest.text() or 0)
            roi = self.sim_roi.value() / 100.0
            cycles = self.sim_cycles.value()
            
            self.lbl_sim_roi_display.setText(f"ROI: {int(roi*100)}%")
            self.lbl_sim_cycles_display.setText(f"Оборотов: {cycles}")
            
            # Compound interest formula: A = P * (1 + r)^n
            final_amount = invest * (1 + roi) ** cycles
            profit = final_amount - invest
            
            self.lbl_sim_result.setText(f"Итог: ${final_amount:,.2f} (+ ${profit:,.2f})")
        except:
            self.lbl_sim_result.setText("Ошибка данных")

    def show_dna_details(self):
        DNADetailsDialog(
            self,
            self.lbl_dna_type.text(),
            self.lbl_dna_desc.text(),
            self.lbl_roi_stat.text(),
            self.lbl_frozen_stat.text(),
            self.lbl_eff_score.text()
        ).exec()

    def show_roi_details(self):
        ROIDetailsDialog(self).exec()
        formula_frame = QFrame()
        formula_frame.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444; border-radius: 5px; padding: 10px;")
        f_layout = QVBoxLayout(formula_frame)
        lbl_form = QLabel("ROI = (Прибыль / Вложения) × 100%")
        lbl_form.setStyleSheet("font-size: 18px; font-weight: bold; color: #3498db;")
        lbl_form.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_layout.addWidget(lbl_form)
        layout.addWidget(formula_frame)
        
        # Example
        lbl_ex = QLabel("Пример: Купил за $100, продал за $150.\nПрибыль = $50.\nROI = (50 / 100) * 100 = 50%.")
        lbl_ex.setStyleSheet("font-style: italic; color: #aaa; margin-top: 5px;")
        layout.addWidget(lbl_ex)
        
        layout.addSpacing(20)
        
        # Efficiency Table
        lbl_table_title = QLabel("Уровни эффективности:")
        lbl_table_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl_table_title)
        
        table_frame = QFrame()
        table_frame.setStyleSheet("background-color: #333; border-radius: 5px;")
        t_layout = QGridLayout(table_frame)
        
        headers = ["ROI", "Оценка", "Совет"]
        for i, h in enumerate(headers):
            l = QLabel(h)
            l.setStyleSheet("font-weight: bold; color: #fff;")
            t_layout.addWidget(l, 0, i)
            
        rows = [
            ("< 0%", "Убыток", "Анализируйте ошибки"),
            ("0-10%", "Низкий", "Ищите товары дешевле"),
            ("10-30%", "Норма", "Стабильный доход"),
            ("30-50%", "Высокий", "Отличная сделка"),
            ("> 50%", "Снайпер", "Масштабируйте успех")
        ]
        
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                l = QLabel(val)
                l.setStyleSheet("color: #ccc;")
                t_layout.addWidget(l, r_idx+1, c_idx)
                
        layout.addWidget(table_frame)
        
        btn_close = QPushButton("Понятно")
        btn_close.clicked.connect(dlg.accept)
        btn_close.setStyleSheet("background-color: #3498db; color: white; padding: 8px; border-radius: 5px; margin-top: 20px;")
        layout.addWidget(btn_close)
        
        dlg.exec()

    def show_help(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("❓ Справка и Обучение")
        dlg.setFixedSize(700, 600)
        dlg.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        layout = QVBoxLayout(dlg)
        
        # Title
        lbl_title = QLabel("Руководство пользователя")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl_title)
        
        # Tabs
        from PyQt6.QtWidgets import QTabWidget, QTextEdit
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #ddd; padding: 8px 20px; }
            QTabBar::tab:selected { background: #3498db; color: white; }
        """)
        
        # 1. General Tab
        tab_gen = QWidget()
        l_gen = QVBoxLayout(tab_gen)
        txt_gen = QTextEdit()
        txt_gen.setReadOnly(True)
        txt_gen.setHtml("""
            <h3>👋 Добро пожаловать!</h3>
            <p>Это приложение поможет вам стать богаче в GTA 5 RP.</p>
            <p><b>Основные возможности:</b></p>
            <ul>
                <li>📊 <b>Учет сделок:</b> Записывайте покупки и продажи одежды, авто и майнинг.</li>
                <li>🎯 <b>Планирование:</b> Ставьте финансовые цели и следите за прогрессом.</li>
                <li>🦉 <b>Умный советник:</b> Получайте персональные советы на основе ваших действий.</li>
                <li>🧬 <b>DNA Профиль:</b> Анализ вашего стиля игры и система наследования.</li>
            </ul>
        """)
        l_gen.addWidget(txt_gen)
        tabs.addTab(tab_gen, "Общее")
        
        # 2. Advisor Tab
        tab_adv = QWidget()
        l_adv = QVBoxLayout(tab_adv)
        txt_adv = QTextEdit()
        txt_adv.setReadOnly(True)
        txt_adv.setHtml("""
            <h3>🦉 Умный Советник</h3>
            <p>Советник анализирует ваши последние действия и капитал.</p>
            <p><b>Как это работает:</b></p>
            <ul>
                <li>Если у вас много денег в товаре, он предупредит о риске заморозки.</li>
                <li>Если ваш ROI падает, он подскажет сменить стратегию.</li>
                <li>Он определяет вашу роль (Трейдер, Майнер, Автодилер) и дает профильные советы.</li>
            </ul>
        """)
        l_adv.addWidget(txt_adv)
        tabs.addTab(tab_adv, "Советник")
        
        # 3. DNA & ROI Tab
        tab_dna = QWidget()
        l_dna = QVBoxLayout(tab_dna)
        txt_dna = QTextEdit()
        txt_dna.setReadOnly(True)
        txt_dna.setHtml("""
            <h3>🧬 DNA и ROI</h3>
            <p><b>DNA Профиль:</b> Это ваш игровой "генетический код". Он формируется на основе вашего стиля торговли (агрессивный, осторожный и т.д.).</p>
            <p><b>Наследование:</b> В будущем вы сможете передавать накопленные бонусы (репутацию, навыки) новым персонажам.</p>
            <hr>
            <h3>📊 ROI (Return on Investment)</h3>
            <p>Показатель эффективности ваших вложений.</p>
            <p>Формула: <code>(Прибыль / Вложения) * 100%</code></p>
            <p>Старайтесь держать ROI выше 30%.</p>
        """)
        l_dna.addWidget(txt_dna)
        tabs.addTab(tab_dna, "DNA и ROI")
        
        # 4. Video Tutorials
        tab_vid = QWidget()
        l_vid = QVBoxLayout(tab_vid)
        txt_vid = QTextEdit()
        txt_vid.setReadOnly(True)
        txt_vid.setHtml("""
            <h3>🎥 Видео-уроки</h3>
            <p>Мы подготовили для вас серию обучающих видео:</p>
            <ul>
                <li><a href="#">Как заработать первый миллион</a></li>
                <li><a href="#">Секреты перепродажи авто</a></li>
                <li><a href="#">Майнинг ферма: старт с нуля</a></li>
            </ul>
            <p><i>(Ссылки будут доступны в релизной версии)</i></p>
        """)
        l_vid.addWidget(txt_vid)
        tabs.addTab(tab_vid, "Видео")
        
        layout.addWidget(tabs)
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(dlg.accept)
        btn_close.setStyleSheet("background-color: #3498db; color: white; padding: 8px; border-radius: 5px;")
        layout.addWidget(btn_close)
        
        dlg.exec()
