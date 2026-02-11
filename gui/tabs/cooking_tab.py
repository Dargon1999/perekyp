from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QScrollArea, QFrame, QGridLayout,
    QSizePolicy, QCheckBox, QSpacerItem, QApplication, QDialog,
    QTreeWidget, QTreeWidgetItem, QListWidget
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QIcon
from gui.styles import StyleManager
from gui.recipe_manager import RecipeManager
from gui.tabs.recipe_detail_dialog import RecipeDetailDialog
from utils import resource_path
import os


class RecipeCard(QFrame):
    def __init__(self, recipe, dish_type, manager, parent=None):
        super().__init__(parent)
        self.recipe = recipe
        self.dish_type = dish_type
        self.manager = manager
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setObjectName("RecipeCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(280) # Reduced to fit 3 in row
        
        # Get Theme Colors
        t = StyleManager.DARK_THEME
        
        self.setStyleSheet(f"""
            #RecipeCard {{
                background-color: {t['bg_card']};
                border-radius: 12px;
                border: 1px solid {t['border']};
            }}
            #RecipeCard:hover {{
                background-color: {t['bg_tertiary']};
                border: 1px solid {t['accent']};
                /* Transform is not supported in QSS for widgets directly like this, removed to avoid warnings */
            }}
            QLabel {{ font-family: 'Segoe UI', sans-serif; }}
        """)
        self.init_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            dlg = RecipeDetailDialog(self.recipe.name, self.manager, self)
            dlg.exec()

    def init_ui(self):
        t = StyleManager.DARK_THEME
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12) # Compact margins
        layout.setSpacing(10) # Compact spacing

        # --- Header: Title + Type Icon ---
        header_layout = QHBoxLayout()
        
        # Title
        name_label = QLabel(self.recipe.name)
        name_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {t['text_main']};") # Reduced font size
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Type Icon (Emoji/Text based on type)
        type_icon_map = {
            "Навык 0": "🥚", "Навык 1": "🍜", "Навык 2": "🥘", 
            "Навык 3": "🍖", "Навык 4": "🍰", "Навык 5": "👑", "Другое": "🥣"
        }
        icon_char = type_icon_map.get(self.dish_type, "🍽️")
        type_lbl = QLabel(icon_char)
        type_lbl.setStyleSheet(f"font-size: 18px; color: {t['text_secondary']};") # Reduced font size
        type_lbl.setToolTip(self.dish_type)
        header_layout.addWidget(type_lbl)
        
        layout.addLayout(header_layout)

        # --- Ingredients Formula ---
        # "Мясо + Овощи + Бульон + Огонь"
        # Style: Ingredients in Accent Color, '+' in Secondary Text
        ing_layout = QHBoxLayout()
        ing_layout.setSpacing(4)
        
        if self.recipe.recipe:
            full_text = " + ".join(self.recipe.recipe)
            # We can use Rich Text for coloring
            plus_color = t['text_secondary']
            ing_color = t['accent'] # Or a specific blue if accent is too bright
            
            colored_text = full_text.replace(" + ", f" <span style='color: {plus_color};'>+</span> ")
            ing_label = QLabel(f"<span style='color: {ing_color}; font-weight: 600;'>{colored_text}</span>")
            ing_label.setWordWrap(True)
            ing_label.setTextFormat(Qt.TextFormat.RichText)
            ing_label.setStyleSheet("font-size: 12px; line-height: 1.3;") # Reduced font size
            layout.addWidget(ing_label)
        else:
            base_lbl = QLabel("Базовый ингредиент")
            base_lbl.setStyleSheet(f"color: {t['text_secondary']}; font-style: italic; font-size: 12px;")
            layout.addWidget(base_lbl)

        # Spacer
        layout.addSpacing(6)

        # --- Stats Grid ---
        stats_layout = QGridLayout()
        stats_layout.setSpacing(8) # Compact spacing
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        stats = self.recipe.stats
        
        # Helper to create stat widget: Icon Label + Value Label
        def add_stat_row(row, col, icon, label_text, value, value_color):
            container = QWidget()
            container.setStyleSheet("background-color: transparent;")
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(6)
            
            # Icon/Label
            lbl = QLabel(f"{icon} {label_text}")
            lbl.setStyleSheet(f"color: {t['text_secondary']}; font-size: 12px; background-color: transparent;")
            h_layout.addWidget(lbl)
            
            # Value
            val = QLabel(str(value))
            val.setStyleSheet(f"color: {value_color}; font-weight: bold; font-size: 13px; background-color: transparent;")
            h_layout.addWidget(val)
            h_layout.addStretch()
            
            stats_layout.addWidget(container, row, col)

        # Satiety (Green)
        satiety = stats.get('satiety', 0)
        add_stat_row(0, 0, "🍖", "Сыт.", satiety, t['success'])
        
        # Mood (Orange)
        mood = stats.get('mood', 0)
        add_stat_row(0, 1, "😋", "Настр.", mood, t['warning'])
        
        # Power (Red/Yellow) - usually negative for cost
        power = stats.get('power', 0)
        add_stat_row(1, 0, "⚡", "Сила", power, t['danger'] if power < 0 else "#ffd740")
        
        # Difficulty (Color Coded)
        diff = stats.get('difficulty', 'Простой')
        diff_color = t['success'] # Easy
        if diff == "Средний": diff_color = t['warning']
        elif diff == "Сложный": diff_color = t['danger']
        
        add_stat_row(1, 1, "🍳", "Сложность", diff, diff_color)

        layout.addLayout(stats_layout)
        layout.addStretch()

class CookingTab(QWidget):
    def __init__(self, data_manager, main_window):
        super().__init__()
        self.data_manager = data_manager
        self.main_window = main_window
        self.recipe_manager = RecipeManager()
        self.all_recipes = []
        
        # Caching and Pagination
        self.filter_cache = {}
        self.current_filtered_recipes = []
        self.loaded_count = 0
        self.page_size = 15
        self.card_widgets = [] # Track card widgets for resizing
        
        self.init_ui()
        
        # Defer loading
        # QTimer.singleShot(100, self.load_data)
        self.is_initialized = False

    def showEvent(self, event):
        if not self.is_initialized:
            self.load_data()
            self.is_initialized = True
        super().showEvent(event)
        QTimer.singleShot(0, self.recalculate_grid)

    def init_ui(self):
        t = StyleManager.DARK_THEME
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10) # Compact margins
        self.layout.setSpacing(10) # Compact spacing

        # Controls Area (Single Row to match reference)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8) # Compact spacing
        
        # 1. Search (Wide)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск блюда или ингредиента...")
        self.search_input.setFixedHeight(32) # Compact height
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t['input_bg']};
                color: {t['text_main']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {t['accent']};
            }}
        """)
        self.search_input.textChanged.connect(self.apply_filters)
        controls_layout.addWidget(self.search_input, 4)
        
        # Helper for Combo Styles
        combo_style = f"""
            QComboBox {{
                background-color: #1a1d24;
                color: #ffffff;
                border: 1px solid #2a2e36;
                border-radius: 8px;
                padding: 0 12px;
                min-width: 100px;
                height: 32px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border: 1px solid #4a4e59;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #888;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1a1d24;
                color: #ffffff;
                border: 1px solid #2a2e36;
                selection-background-color: #4a90e2;
            }}
        """
        
        # 2. Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Все типы", "Навык 0", "Навык 1", "Навык 2", "Навык 3", "Навык 4", "Навык 5", "Другое"])
        self.type_combo.currentTextChanged.connect(self.apply_filters)
        self.type_combo.setStyleSheet(combo_style)
        controls_layout.addWidget(self.type_combo, 1)
        
        # 3. Difficulty
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["Любая сложность", "Простой", "Средний", "Сложный"])
        self.diff_combo.currentTextChanged.connect(self.apply_filters)
        self.diff_combo.setStyleSheet(combo_style)
        controls_layout.addWidget(self.diff_combo, 1)

        # 4. Sort
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Сортировка: Назван", "Сортировка: Сытость", "Сортировка: Настроение", "Сортировка: Сила", "Сортировка: Сложность"])
        self.sort_combo.currentIndexChanged.connect(self.apply_filters)
        self.sort_combo.setStyleSheet(combo_style)
        controls_layout.addWidget(self.sort_combo, 1)
        
        # Hidden filters (Satiety/Mood/Power) - kept for logic but removed from UI to match reference
        # To restore them, add them back to layout or a secondary row.
        # For now, initializing them so logic doesn't break
        self.satiety_combo = QComboBox()
        self.satiety_combo.addItems(["Любая сытость", "Легкое (<15)", "Среднее (15-40)", "Сытное (>40)"])
        self.satiety_combo.currentIndexChanged.connect(self.apply_filters)
        
        self.mood_combo = QComboBox()
        self.mood_combo.addItems(["Любое настроение", "Обычное (0-20)", "Бодрящее (21-50)", "Праздничное (>50)"])
        self.mood_combo.currentIndexChanged.connect(self.apply_filters)
        
        self.power_combo = QComboBox()
        self.power_combo.addItems(["Любая сила", "Малая (0 до -5)", "Средняя (-6 до -15)", "Высокая (<-15)"])
        self.power_combo.currentIndexChanged.connect(self.apply_filters)

        self.layout.addLayout(controls_layout)

        # Scroll Area for Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Initially hide horizontal scrollbar, show only at bottom
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QGridLayout(self.scroll_content)
        self.scroll_layout.setSpacing(20) # Gap 20px
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
        
        self.scroll.verticalScrollBar().valueChanged.connect(self.check_scroll_bottom)

    def load_data(self):
        # Load recipes from RecipeManager
        raw_recipes = self.recipe_manager.get_all_recipes()
        self.all_recipes = []
        for r in raw_recipes:
            # Add dish type helper
            r.dish_type = self.recipe_manager.get_dish_type(r.name)
            self.all_recipes.append(r)
            
        self.apply_filters()

    def apply_filters(self):
        search_text = self.search_input.text().lower()
        dish_type = self.type_combo.currentText()
        difficulty = self.diff_combo.currentText()
        satiety_idx = self.satiety_combo.currentIndex()
        mood_idx = self.mood_combo.currentIndex()
        power_idx = self.power_combo.currentIndex()
        sort_mode = self.sort_combo.currentIndex()
        
        # Check cache
        cache_key = (search_text, dish_type, difficulty, satiety_idx, mood_idx, power_idx, sort_mode)
        if cache_key in self.filter_cache:
            self.display_recipes(self.filter_cache[cache_key])
            return
        
        filtered = []
        
        for r in self.all_recipes:
            # 1. Search (Name or Ingredients)
            ing_str = " ".join(r.recipe).lower() if r.recipe else ""
            if search_text and (search_text not in r.name.lower() and search_text not in ing_str):
                continue
                
            # 2. Type
            if dish_type != "Все типы" and r.dish_type != dish_type:
                continue
                
            # 3. Difficulty
            if difficulty != "Любая сложность" and r.stats.get('difficulty') != difficulty:
                continue
                
            # 4. Satiety
            s = r.stats.get('satiety', 0)
            if satiety_idx == 1 and s >= 15: continue # < 15
            if satiety_idx == 2 and (s < 15 or s > 40): continue # 15-40
            if satiety_idx == 3 and s <= 40: continue # > 40
            
            # 5. Mood
            m = r.stats.get('mood', 0)
            if mood_idx == 1 and m > 20: continue # 0-20
            if mood_idx == 2 and (m <= 20 or m > 50): continue # 21-50
            if mood_idx == 3 and m <= 50: continue # > 50

            # 6. Power
            p = r.stats.get('power', 0)
            if power_idx == 1 and (p < -5 or p > 0): continue # 0 to -5
            if power_idx == 2 and (p < -15 or p >= -5): continue # -6 to -15
            if power_idx == 3 and p >= -15: continue # < -15
            
            filtered.append(r)
            
        # Sort
        if sort_mode == 0: # Name
            filtered.sort(key=lambda x: x.name)
        elif sort_mode == 1: # Satiety
            filtered.sort(key=lambda x: x.stats.get('satiety', 0), reverse=True)
        elif sort_mode == 2: # Mood
            filtered.sort(key=lambda x: x.stats.get('mood', 0), reverse=True)
        elif sort_mode == 3: # Power
            filtered.sort(key=lambda x: x.stats.get('power', 0), reverse=True)
        elif sort_mode == 4: # Difficulty
            diff_map = {"Простой": 1, "Средний": 2, "Сложный": 3}
            filtered.sort(key=lambda x: diff_map.get(x.stats.get('difficulty', 'Простой'), 0))
            
        self.filter_cache[cache_key] = filtered
        self.display_recipes(filtered)

    def display_recipes(self, recipes):
        self.current_filtered_recipes = recipes
        self.loaded_count = 0
        self.card_widgets = [] # Clear tracked widgets
        
        # Clear layout
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        if not recipes:
            no_res = QLabel("Нет рецептов, соответствующих критериям.")
            no_res.setStyleSheet("color: #777; font-size: 14px; margin-top: 20px;")
            no_res.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.addWidget(no_res, 0, 0, 1, 3)
            return

        self.load_more_recipes()


        
    def get_column_count(self):
        # Dynamic column count based on available width
        width = self.scroll.viewport().width()
        if width <= 0: return 3 # Default fallback
        
        # Reduced width threshold to allow 3 columns in standard window
        # 280 min width + spacing = ~300px per column
        cols = max(1, width // 300)
        return cols

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Recalculate grid on resize
        QTimer.singleShot(100, self.recalculate_grid)

    
    def recalculate_grid(self):
        cols = self.get_column_count()
        
        # Apply column stretch to ensure equal width columns
        # This simulates "flex: 33.33%" or "flex: 50%" behavior
        # We reset all first, then set the active ones
        current_col_count = self.scroll_layout.columnCount()
        for c in range(current_col_count):
             self.scroll_layout.setColumnStretch(c, 0)
        for c in range(cols):
             self.scroll_layout.setColumnStretch(c, 1)
        
        if not self.card_widgets:
            return
            
        for idx, widget in enumerate(self.card_widgets):
            row = idx // cols
            col = idx % cols
            self.scroll_layout.addWidget(widget, row, col)

    def load_more_recipes(self):
        start = self.loaded_count
        end = min(start + self.page_size, len(self.current_filtered_recipes))
        
        if start >= end:
            return
            
        batch = self.current_filtered_recipes[start:end]
        
        # Create cards and append to list
        for r in batch:
            card = RecipeCard(r, r.dish_type, self.recipe_manager)
            self.card_widgets.append(card)
            
        self.loaded_count = end
        
        # Delegate placement to recalculate_grid for consistent layout logic
        # This ensures the grid is always calculated correctly (e.g. 3 cols) from the first element
        self.recalculate_grid()

    def check_scroll_bottom(self, value):
        max_val = self.scroll.verticalScrollBar().maximum()
        
        # Load more recipes if near bottom
        if value >= max_val * 0.9:
            self.load_more_recipes()
            # Update max_val after loading
            max_val = self.scroll.verticalScrollBar().maximum()
            
        # Toggle horizontal scrollbar visibility
        # Only show when scrolled to the very bottom (with small threshold)
        if value >= max_val - 5: 
            if self.scroll.horizontalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAsNeeded:
                self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            if self.scroll.horizontalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAlwaysOff:
                self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

