class StyleManager:
    @staticmethod
    def get_theme(theme_name="dark"):
        if theme_name == "light":
            return StyleManager.LIGHT_THEME
        return StyleManager.DARK_THEME

    # Midnight Modern Palette (Restored Dark Blue)
    DARK_THEME = {
        "bg_main": "#0f172a",       # Slate 900
        "bg_secondary": "#1e293b",  # Slate 800
        "bg_tertiary": "#334155",   # Slate 700
        "bg_card": "#1e293b",
        "accent": "#3b82f6",        # Blue 500
        "accent_hover": "#2563eb",  # Blue 600
        "accent_pressed": "#1d4ed8",# Blue 700
        "text_main": "#f1f5f9",     # Slate 100
        "text_secondary": "#94a3b8",# Slate 400
        "border": "#334155",        # Slate 700
        "success": "#10b981",       # Emerald 500
        "danger": "#ef4444",        # Red 500
        "warning": "#f59e0b",       # Amber 500
        "input_bg": "#020617",      # Slate 950
        "scrollbar_handle": "#475569",
    }

    LIGHT_THEME = {
        "bg_main": "#f8fafc",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#e2e8f0",
        "bg_card": "#ffffff",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "accent_pressed": "#1d4ed8",
        "text_main": "#0f172a",
        "text_secondary": "#64748b",
        "border": "#cbd5e1",
        "success": "#10b981",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "input_bg": "#ffffff",
        "scrollbar_handle": "#cbd5e1",
    }

    @staticmethod
    def get_qss(theme_name="dark"):
        t = StyleManager.get_theme(theme_name)
        
        return f"""
            /* Global Reset */
            QMainWindow {{
                background-color: transparent;
            }}
            QWidget {{
                background-color: {t['bg_main']};
                color: {t['text_main']};
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 14px;
            }}
            
            /* Frames & Containers */
            QFrame, QWidget#Container {{
                border: none;
            }}

            /* SideBar / Navigation */
            QWidget#SideBar {{
                background-color: {t['bg_secondary']};
                border-right: 1px solid {t['border']};
            }}

            /* Title Bar */
            QWidget#TitleBar {{
                background-color: {t['bg_secondary']};
                border-bottom: 1px solid {t['border']};
            }}
            
            /* Navigation Buttons */
            QPushButton#NavButton {{
                background-color: transparent;
                color: {t['text_secondary']};
                text-align: left;
                padding: 12px 24px;
                border: none;
                border-left: 3px solid transparent;
                font-weight: 600;
                font-size: 14px;
                border-radius: 0px;
            }}
            QPushButton#NavButton:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {t['text_main']};
            }}
            QPushButton#NavButton:checked {{
                background-color: rgba(59, 130, 246, 0.1); /* Low opacity accent */
                color: {t['accent']};
                border-left: 3px solid {t['accent']};
            }}
            QPushButton#NavButton QIcon {{
                padding-right: 10px;
            }}

            /* Standard Buttons */
            QPushButton {{
                background-color: {t['accent']};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {t['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {t['accent_pressed']};
                padding-top: 11px; /* Slight press effect */
                padding-bottom: 9px;
            }}
            QPushButton:disabled {{
                background-color: {t['bg_tertiary']};
                color: {t['text_secondary']};
            }}

            /* Outlined/Secondary Button Style (if needed via objectName or class) */
            QPushButton[class="secondary"] {{
                background-color: transparent;
                border: 1px solid {t['border']};
                color: {t['text_main']};
            }}
            QPushButton[class="secondary"]:hover {{
                border-color: {t['text_secondary']};
                background-color: {t['bg_tertiary']};
            }}

            /* Input Fields */
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {t['input_bg']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 10px;
                color: {t['text_main']};
                selection-background-color: {t['accent']};
                selection-color: white;
            }}

            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                width: 25px;
                background-color: transparent;
                border-left: 1px solid {t['border']};
            }}
            QSpinBox::up-button {{
                subcontrol-position: top right;
                border-top-right-radius: 6px;
                border-bottom: 1px solid {t['border']};
            }}
            QSpinBox::down-button {{
                subcontrol-position: bottom right;
                border-bottom-right-radius: 6px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {t['bg_tertiary']};
            }}
            QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
                background-color: {t['accent']};
            }}
            QSpinBox::up-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid {t['text_secondary']};
                width: 0;
                height: 0;
            }}
            QSpinBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {t['text_secondary']};
                width: 0;
                height: 0;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {t['accent']};
            }}
            QLineEdit:hover {{
                border: 1px solid {t['text_secondary']};
            }}

            /* Labels */
            QLabel {{
                background-color: transparent;
                border: none;
            }}
            QLabel#Header {{
                font-size: 24px;
                font-weight: 700;
                color: {t['text_main']};
            }}
            QLabel#WindowTitle {{
                font-size: 20px;
                font-weight: 700;
                color: {t['text_main']};
                background-color: transparent;
            }}
            QLabel#SubHeader {{
                font-size: 16px;
                font-weight: 600;
                color: {t['text_secondary']};
            }}
            QLabel#Label {{
                color: {t['text_secondary']};
                font-size: 13px;
                font-weight: 500;
            }}

            /* Tables */
            QTableWidget {{
                background-color: {t['bg_main']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                gridline-color: {t['border']};
                selection-background-color: {t['accent']};
                selection-color: white;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: rgba(59, 130, 246, 0.2);
                color: {t['text_main']};
            }}
            QHeaderView::section {{
                background-color: {t['bg_secondary']};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {t['border']};
                border-right: 1px solid {t['border']};
                font-weight: 600;
                color: {t['text_secondary']};
            }}
            QTableCornerButton::section {{
                background-color: {t['bg_secondary']};
                border: none;
            }}

            /* ScrollBars */
            QScrollBar:vertical {{
                border: none;
                background: {t['bg_main']};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scrollbar_handle']};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: {t['bg_main']};
                height: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {t['scrollbar_handle']};
                min-width: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {t['accent']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            /* Dialogs */
            QDialog {{
                background-color: {t['bg_main']};
            }}
            
            /* Combo Box */
            QComboBox {{
                background-color: {t['bg_secondary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 8px 15px;
                color: {t['text_main']};
                font-size: 13px;
            }}
            QComboBox:hover {{
                border: 1px solid {t['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {t['text_secondary']};
                margin-right: 10px;
                margin-top: 2px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t['bg_secondary']};
                border: 1px solid {t['border']};
                selection-background-color: {t['accent']};
                selection-color: white;
                color: {t['text_main']};
                outline: none;
                padding: 5px;
            }}

            /* ScrollArea */
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            
            /* Checkbox */
            QCheckBox {{
                spacing: 8px;
                color: {t['text_main']};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {t['text_secondary']};
                border-radius: 4px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {t['accent']};
                border-color: {t['accent']};
                /* image: url(); Removed to prevent QFSFileEngine error */
            }}
            QCheckBox::indicator:hover {{
                border-color: {t['accent']};
            }}
            
            /* Custom Title Bar specific */
            QWidget#TitleBar {{
                background-color: {t['bg_secondary']};
                border-bottom: 1px solid {t['border']};
            }}
            QPushButton#TitleBarButton {{
                background-color: transparent;
                border: none;
                border-radius: 0;
            }}
            QPushButton#TitleBarButton:hover {{
                background-color: {t['bg_tertiary']};
            }}
            QPushButton#CloseButton:hover {{
                background-color: {t['danger']};
                color: white;
            }}
        """

    @staticmethod
    def _get_check_icon_path():
        # Placeholder or return empty if handled by code/resource
        # For simplicity, we rely on color fill or add a custom SVG later
        return "" 

    @staticmethod
    def get_heading_style(theme_name="dark"):
        t = StyleManager.get_theme(theme_name)
        return f"font-size: 24px; font-weight: bold; color: {t['text_main']}; margin-bottom: 10px;"
