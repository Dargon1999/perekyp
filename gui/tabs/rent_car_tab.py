from gui.tabs.generic_tab import GenericTab
from PyQt6.QtWidgets import QPushButton, QMessageBox, QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel, QHBoxLayout, QScrollArea, QFrame, QWidget
from PyQt6.QtCore import Qt
from gui.styles import StyleManager
from gui.tabs.timers_tab import TimerCard

class RentCarTab(GenericTab):
    def __init__(self, data_manager, category="car_rental", parent=None):
        super().__init__(data_manager, category, parent)
        
        # Insert Active Rentals section at the top (index 0 or 1)
        # GenericTab layout: Header(0), Stats(1), Table(2), Footer(3)
        # We want it after Stats? Or before Table.
        
        self.setup_active_rentals()
        # Insert after Stats (index 2)
        self.layout.insertWidget(2, self.active_rentals_container)
        
        self.update_active_rentals() # Manually call update after setup

    def get_extra_fields(self):
        return []

    def setup_active_rentals(self):
        self.active_rentals_container = QWidget()
        self.active_rentals_layout = QVBoxLayout(self.active_rentals_container)
        self.active_rentals_layout.setContentsMargins(0, 0, 0, 0)
        self.active_rentals_layout.setSpacing(10)
        
        lbl = QLabel("Активные аренды (Таймеры)")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #bdc3c7;")
        self.active_rentals_layout.addWidget(lbl)
        
        self.rentals_scroll = QScrollArea()
        self.rentals_scroll.setWidgetResizable(True)
        self.rentals_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.rentals_scroll.setFixedHeight(170) # Height for one row of cards
        self.rentals_scroll.setStyleSheet("background: transparent;")
        
        self.rentals_content = QWidget()
        self.rentals_cards_layout = QHBoxLayout(self.rentals_content)
        self.rentals_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.rentals_cards_layout.setSpacing(15)
        self.rentals_cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.rentals_scroll.setWidget(self.rentals_content)
        self.active_rentals_layout.addWidget(self.rentals_scroll)
        
        # Initially hide if empty? No, handled in refresh
        
    def apply_theme(self, theme_name):
        super().apply_theme(theme_name)
        self.update_balance_editability()

    def refresh_data(self):
        super().refresh_data()
        self.update_balance_editability()
        if hasattr(self, 'rentals_cards_layout'):
            self.update_active_rentals()

    def update_balance_editability(self):
        """Enable or disable manual balance editing based on settings."""
        if not hasattr(self, 'stat_balance'): return
        
        is_manual = self.data_manager.get_setting("allowManualBalanceEdit", False)
        
        if is_manual:
            self.stat_balance.value_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.stat_balance.value_label.setToolTip("Нажмите дважды для изменения баланса вручную")
        else:
            self.stat_balance.value_label.setCursor(Qt.CursorShape.ArrowCursor)
            self.stat_balance.value_label.setToolTip("")

    def on_balance_clicked(self):
        # Explanatory message if disabled
        if not self.data_manager.get_setting("allowManualBalanceEdit", False):
            QMessageBox.information(
                self, "Информация", 
                "Для изменения баланса включите опцию «Разрешить ручное редактирование баланса» в Настройках → Управление балансом"
            )
            return
            
        # Call start_inline_balance_edit from base class instead of old dialog logic
        if hasattr(self, 'start_inline_balance_edit'):
            self.start_inline_balance_edit()
        else:
            # Fallback if somehow not available
            from PyQt6.QtWidgets import QInputDialog
            current_val = self.data_manager.get_total_capital_balance()["liquid_cash"]
            
            dialog = QInputDialog(self)
            dialog.setWindowTitle("Ручное редактирование")
            dialog.setLabelText("Введите новый текущий баланс ($):")
            dialog.setDoubleValue(current_val)
            dialog.setDoubleRange(-1000000000, 1000000000)
            dialog.setDoubleDecimals(2)
            
            if dialog.exec():
                new_val = dialog.doubleValue()
                self.update_balance_via_api(new_val)

    def setup_stats(self):
        super().setup_stats()
        # Connect DOUBLE click to the balance label
        self.stat_balance.value_label.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.stat_balance.value_label and event.type() == event.Type.MouseButtonDblClick:
            self.on_balance_clicked()
            return True
        return super().eventFilter(obj, event)

    def update_active_rentals(self):
        if not hasattr(self, 'rentals_cards_layout'):
            return

        # Clear existing cards
        while self.rentals_cards_layout.count():
            item = self.rentals_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        timers = self.data_manager.get_timers()
        rental_timers = [t for t in timers if t["type"] == "Аренда Транспорта"]
        
        if not rental_timers:
            self.active_rentals_container.setVisible(False)
        else:
            self.active_rentals_container.setVisible(True)
            for timer in rental_timers:
                card = TimerCard(timer, self)
                # Adjust card size for horizontal layout if needed
                card.setFixedWidth(250)
                self.rentals_cards_layout.addWidget(card)



