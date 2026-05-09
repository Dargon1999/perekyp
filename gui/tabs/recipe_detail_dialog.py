from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QWidget, QScrollArea, 
    QFrame, QGridLayout, QSizePolicy, QStackedWidget,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QCursor, QPainter
from gui.styles import StyleManager
from gui.animations import AnimationManager

class RecipeDetailDialog(QDialog):
    def __init__(self, recipe_name, recipe_manager, parent=None):
        super().__init__(parent)
        self.recipe_manager = recipe_manager
        
        # Navigation Stack: Stores recipe names
        self.history_stack = [recipe_name]
        
        self.setWindowTitle(f"Рецепт: {recipe_name}")
        
        # Custom Window Flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Overlay Sizing: Cover the parent window or full screen
        if parent and parent.window():
            self.setGeometry(parent.window().geometry())
        else:
            self.resize(1024, 768)

        self._drag_pos = None
        
        self.init_ui()
        self.apply_styles()
        
        # Animate Appearance
        AnimationManager.fade_in(self.container)

        # Render initial view
        self.render_view()

    def close_animated(self):
        AnimationManager.fade_out(self.container, on_finished=self.accept)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_animated()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        # Draw the darkened overlay background
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))

    def mousePressEvent(self, event):
        # Check if click is on the overlay (outside the container)
        if not self.container.geometry().contains(event.position().toPoint()):
            self.close_animated()
            return

    def init_ui(self):
        # Main Layout (Dialog) - Overlay
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Container Frame (The Card)
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setFixedSize(800, 700)
        self.layout.addWidget(self.container)
        
        # Container Layout
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 1. Top Bar: Just Spacer (Close button is floating or absolute)
        # Actually user wants "upper left corner of the dish card"
        # We can put it inside the container using a layout or absolute positioning
        # Let's use a layout but put Close button first
        
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 16, 16, 16) # 16px margins as requested
        
        # Close Button (Cross Icon)
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(44, 44) # 44x44 clickable area
        self.btn_close.setObjectName("CloseButton")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close_animated)
        
        # To ensure the cross icon itself is 24x24 inside the 44x44 button, we can use font size or icon size.
        # User requested "standard size 24x24 pixels" for the cross.
        # If using text "✕", font-size ~24px is good.
        
        top_layout.addStretch()
        top_layout.addWidget(self.btn_close)
        
        container_layout.addWidget(top_bar)
        
        # 2. Content Area (Scrollable)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        container_layout.addWidget(self.scroll_area)
        
        self.content_widget = QWidget()
        self.content_widget.setObjectName("ScrollContents")
        self.scroll_area.setWidget(self.content_widget)
        
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(20, 20, 20, 20)

    def apply_styles(self):
        t = StyleManager.get_theme("dark")
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            
            QFrame#MainContainer {{
                background-color: {t['bg_main']};
                border: 1px solid {t['border']};
                border-radius: 16px;
            }}
            
            QFrame#TopBar {{
                background-color: transparent;
                border-bottom: 1px solid {t['border']};
            }}
            
            QPushButton#CloseButton {{
                background-color: transparent;
                border: none;
                color: {t['text_secondary']};
                font-size: 24px; /* Icon size approx */
                font-weight: normal;
                border-radius: 22px; /* Circular hover effect */
            }}
            QPushButton#CloseButton:hover {{
                background-color: {t['danger']};
                color: white;
            }}
            
            QLabel {{ color: {t['text_main']}; }}
            QScrollArea {{ background-color: transparent; border: none; }}
            QWidget#ScrollContents {{ background-color: transparent; }}
            
            QFrame#SectionFrame {{
                background-color: {t['bg_secondary']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
            
            QPushButton {{
                background-color: {t['bg_tertiary']};
                color: {t['text_main']};
                border: 1px solid {t['border']};
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{ 
                background-color: {t['accent']};
                border-color: {t['accent']};
                color: white;
            }}
            
            /* Breadcrumbs */
            QLabel#Breadcrumb {{
                color: {t['text_secondary']};
                font-size: 14px;
            }}
            QLabel#BreadcrumbActive {{
                color: {t['accent']};
                font-weight: bold;
                font-size: 14px;
            }}
            
            /* Ingredient Button (Clickable) */
            QPushButton#IngredientButton {{
                background-color: {t['bg_tertiary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                text-align: left;
                padding: 12px;
            }}
            QPushButton#IngredientButton:hover {{
                background-color: {t['bg_tertiary']};
                border: 1px solid {t['accent']};
            }}
            
            /* Ingredient Static (Non-clickable) */
            QFrame#IngredientStatic {{
                background-color: {t['bg_tertiary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

    def render_view(self):
        # Clear current content
        self.clear_layout(self.content_layout)
        
        # In this linear view design, we ignore the history_stack navigation
        # and always render the root recipe (first item in stack) in a linear fashion
        root_recipe = self.history_stack[0]
        
        # Get cooking steps (topological sort)
        steps = self.recipe_manager.get_crafting_steps(root_recipe)
        
        # --- Header ---
        header_frame = QFrame()
        header_frame.setObjectName("SectionFrame")
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title = QLabel(root_recipe)
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #ff9800; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)
        
        # Linear Structure (Top Ingredients)
        ing_list_lbl = QLabel()
        ing_obj = self.recipe_manager.get_ingredient(root_recipe)
        if ing_obj and ing_obj.recipe:
            ing_list_lbl.setText(" + ".join(ing_obj.recipe))
        else:
            ing_list_lbl.setText("Базовый ингредиент")
        ing_list_lbl.setStyleSheet("font-size: 16px; color: #aaa; margin-bottom: 10px;")
        ing_list_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(ing_list_lbl)
        
        # Stats
        if ing_obj and ing_obj.stats:
            stats_layout = QHBoxLayout()
            stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            satiety = ing_obj.stats.get('satiety', 0)
            mood = ing_obj.stats.get('mood', 0)
            power = ing_obj.stats.get('power', 0)
            difficulty = ing_obj.stats.get('difficulty', 'Нормально')
            
            stats_items = [
                (f"🍽 {satiety}", "#e0e0e0"),
                (f"🙂 {mood}", "#e0e0e0"),
                (f"💪 {power}", "#ff5252" if power < 0 else "#4caf50"),
                (f"⚙️ {difficulty}", "#ffa726")
            ]
            
            for text, color in stats_items:
                lbl = QLabel(text)
                lbl.setStyleSheet(f"background-color: #444; color: {color}; padding: 5px 10px; border-radius: 4px; font-weight: bold; margin: 0 5px;")
                stats_layout.addWidget(lbl)
                
            header_layout.addLayout(stats_layout)
            
        self.content_layout.addWidget(header_frame)
        
        # Description (Placeholder or Detailed)
        desc_frame = QFrame()
        desc_frame.setObjectName("SectionFrame")
        desc_layout = QVBoxLayout(desc_frame)
        desc_title = QLabel("Описание блюда")
        desc_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff9800;")
        desc_layout.addWidget(desc_title)
        
        dish_type = self.recipe_manager.get_dish_type(root_recipe)
        
        # Use detailed description if available
        if ing_obj and hasattr(ing_obj, 'details') and ing_obj.details.get('description'):
            desc_text = ing_obj.details['description']
        else:
            desc_text = f"Это блюдо категории '{dish_type}'. "
            if ing_obj and ing_obj.stats.get('satiety', 0) > 30:
                desc_text += "Оно очень сытное и отлично подходит для восстановления сил. "
            if ing_obj and ing_obj.stats.get('mood', 0) > 30:
                desc_text += "Поднимает настроение! "
            if ing_obj and ing_obj.type == 'final':
                desc_text += "Требует предварительной подготовки ингредиентов."
            
        desc_lbl = QLabel(desc_text)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #ccc; font-size: 14px; line-height: 1.4;")
        desc_layout.addWidget(desc_lbl)
        self.content_layout.addWidget(desc_frame)

        # --- Cooking Structure (Topological) ---
        steps_header = QLabel("Рецепт приготовления")
        steps_header.setStyleSheet("font-size: 22px; font-weight: bold; color: #ff9800; margin-top: 15px;")
        self.content_layout.addWidget(steps_header)
        
        if not steps:
            # Simple item or base ingredient
            no_steps_lbl = QLabel("Этот ингредиент является базовым и не требует сложного приготовления (или рецепт неизвестен).")
            self.content_layout.addWidget(no_steps_lbl)
        else:
            for i, step_item in enumerate(steps, 1):
                step_frame = QFrame()
                step_frame.setObjectName("SectionFrame")
                step_layout = QVBoxLayout(step_frame)
                
                # Step Title
                step_title = QLabel(f"{i}. {step_item.name}")
                step_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff9800;")
                step_layout.addWidget(step_title)
                
                # Description logic
                if step_item.name == root_recipe:
                    sub_desc = "Если у вас есть все готовые ингредиенты, приготовление становится доступным:"
                else:
                    sub_desc = f"Чтобы приготовить {step_item.name}, необходимо:"
                    
                sub_desc_lbl = QLabel(sub_desc)
                sub_desc_lbl.setStyleSheet("color: #aaa; margin-bottom: 5px;")
                step_layout.addWidget(sub_desc_lbl)
                
                # Ingredients List
                if step_item.recipe:
                    # Create visual blocks for ingredients
                    ing_container = QWidget()
                    ing_layout = QHBoxLayout(ing_container)
                    ing_layout.setContentsMargins(0,0,0,0)
                    ing_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    
                    for ing in step_item.recipe:
                        # Box style
                        ing_lbl = QLabel(ing)
                        ing_lbl.setStyleSheet("""
                            background-color: #444; 
                            color: #e0e0e0; 
                            padding: 8px 12px; 
                            border-radius: 6px; 
                            font-weight: bold;
                            border: 1px solid #555;
                        """)
                        ing_layout.addWidget(ing_lbl)
                        
                        # Plus sign except for last
                        if ing != step_item.recipe[-1]:
                            plus = QLabel("+")
                            plus.setStyleSheet("color: #888; font-size: 18px; font-weight: bold;")
                            ing_layout.addWidget(plus)
                            
                    step_layout.addWidget(ing_container)
                
                self.content_layout.addWidget(step_frame)
                
        # Final Success Message
        success_frame = QFrame()
        success_frame.setStyleSheet("""
            background-color: #2e3b2f; 
            border: 1px solid #4caf50; 
            border-radius: 8px; 
            padding: 15px;
            margin-top: 10px;
        """)
        success_layout = QHBoxLayout(success_frame)
        success_lbl = QLabel("➡️ При наличии всех компонентов блюдо успешно готовится.")
        success_lbl.setStyleSheet("color: #a5d6a7; font-weight: bold; font-size: 14px;")
        success_layout.addWidget(success_lbl)
        self.content_layout.addWidget(success_frame)
        
        self.content_layout.addStretch()

    def navigate_to(self, recipe_name):
        self.history_stack.append(recipe_name)
        self.render_view()

    def go_back(self):
        if len(self.history_stack) > 1:
            self.history_stack.pop()
            self.render_view()

    def update_breadcrumbs(self):
        self.clear_layout(self.breadcrumbs_layout)
        
        for i, name in enumerate(self.history_stack):
            if i > 0:
                sep = QLabel(" > ")
                sep.setObjectName("Breadcrumb")
                self.breadcrumbs_layout.addWidget(sep)
            
            lbl = QLabel(name)
            if i == len(self.history_stack) - 1:
                lbl.setObjectName("BreadcrumbActive")
            else:
                lbl.setObjectName("Breadcrumb")
            self.breadcrumbs_layout.addWidget(lbl)
            
        self.breadcrumbs_layout.addStretch()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
