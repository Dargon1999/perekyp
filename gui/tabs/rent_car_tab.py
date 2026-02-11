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
        
    def refresh_data(self):
        super().refresh_data()
        if hasattr(self, 'rentals_cards_layout'):
            self.update_active_rentals()
        
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



