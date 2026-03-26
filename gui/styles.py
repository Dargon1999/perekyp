class StyleManager:
    _themes = None
    
    @classmethod
    def _init_themes(cls):
        if cls._themes is not None:
            return
        
        cls._themes = {
            "dark": {
                "bg_main": "#0a0f1a",
                "bg_secondary": "#111827",
                "bg_tertiary": "#1f2937",
                "bg_card": "#111827",
                "accent": "#3b82f6",
                "accent_hover": "#60a5fa",
                "accent_pressed": "#2563eb",
                "accent_glow": "rgba(59, 130, 246, 0.3)",
                "text_main": "#f9fafb",
                "text_secondary": "#9ca3af",
                "border": "#374151",
                "success": "#10b981",
                "danger": "#ef4444",
                "warning": "#f59e0b",
                "input_bg": "#0d1117",
                "scrollbar_handle": "#4b5563",
                "shadow": "rgba(0, 0, 0, 0.4)",
                "card_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
            },
            "dark_blue": {
                "bg_main": "#0c1929",
                "bg_secondary": "#132337",
                "bg_tertiary": "#1a3352",
                "bg_card": "#132337",
                "accent": "#3b82f6",
                "accent_hover": "#60a5fa",
                "accent_pressed": "#2563eb",
                "accent_glow": "rgba(59, 130, 246, 0.4)",
                "text_main": "#e2e8f0",
                "text_secondary": "#94a3b8",
                "border": "#1e3a5f",
                "success": "#10b981",
                "danger": "#ef4444",
                "warning": "#f59e0b",
                "input_bg": "#0a1525",
                "scrollbar_handle": "#2563eb",
                "shadow": "rgba(0, 0, 0, 0.5)",
                "card_shadow": "0 4px 12px -2px rgba(0, 0, 0, 0.4), 0 2px 6px -1px rgba(59, 130, 246, 0.15)",
            },
            "light": {
                "bg_main": "#f9fafb",
                "bg_secondary": "#ffffff",
                "bg_tertiary": "#f3f4f6",
                "bg_card": "#ffffff",
                "accent": "#3b82f6",
                "accent_hover": "#2563eb",
                "accent_pressed": "#1d4ed8",
                "accent_glow": "rgba(59, 130, 246, 0.2)",
                "text_main": "#111827",
                "text_secondary": "#6b7280",
                "border": "#e5e7eb",
                "success": "#10b981",
                "danger": "#ef4444",
                "warning": "#f59e0b",
                "input_bg": "#ffffff",
                "scrollbar_handle": "#d1d5db",
                "shadow": "rgba(0, 0, 0, 0.1)",
                "card_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
            },
        }
    
    @staticmethod
    def get_theme(theme_name="dark"):
        import logging
        StyleManager._init_themes()
        theme = StyleManager._themes.get(theme_name, StyleManager._themes["dark"]).copy()
        
        # Override with custom accent if available
        try:
            from data_manager import DataManager
            dm = DataManager()
            custom_accent = dm.get_setting("accent_color")
            if custom_accent and isinstance(custom_accent, str) and len(custom_accent) == 7:
                # Validate hex format
                if custom_accent.startswith("#"):
                    try:
                        r = int(custom_accent[1:3], 16)
                        g = int(custom_accent[3:5], 16)
                        b = int(custom_accent[5:7], 16)
                        theme["accent"] = custom_accent
                        theme["accent_glow"] = f"rgba({r}, {g}, {b}, 0.3)"
                    except ValueError:
                        logging.warning(f"Invalid accent color value: {custom_accent}")
        except Exception as e:
            logging.warning(f"Failed to load custom accent: {e}")
            
        return theme

    DARK_THEME = property(lambda self: StyleManager.get_theme("dark"))
    DARK_BLUE_THEME = property(lambda self: StyleManager.get_theme("dark_blue"))
    LIGHT_THEME = property(lambda self: StyleManager.get_theme("light"))

    @staticmethod
    def get_qss(theme_name="dark"):
        t = StyleManager.get_theme(theme_name)
        
        return f"""
            QMainWindow {{
                background-color: transparent;
            }}
            QWidget {{
                background-color: {t['bg_main']};
                color: {t['text_main']};
                font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 14px;
            }}
            
            QFrame, QWidget#Container {{
                border: none;
            }}

            QWidget#SideBar {{
                background-color: {t['bg_secondary']};
                border-right: 1px solid {t['border']};
            }}

            QWidget#TitleBar {{
                background-color: {t['bg_secondary']};
                border-bottom: 1px solid {t['border']};
            }}
            
            QPushButton#NavButton {{
                background-color: transparent;
                color: {t['text_secondary']};
                text-align: left;
                padding: 12px 20px;
                border: none;
                border-left: 3px solid transparent;
                font-weight: 500;
                font-size: 13px;
                border-radius: 0;
            }}
            QPushButton#NavButton:hover {{
                background-color: {t['bg_tertiary']};
                color: {t['text_main']};
            }}
            QPushButton#NavButton:checked {{
                background-color: {t['accent_glow']};
                color: {t['accent']};
                border-left: 3px solid {t['accent']};
                font-weight: 600;
            }}
            QPushButton#NavButton QIcon {{
                padding-right: 10px;
            }}

            QPushButton#ArrowButton {{
                background-color: transparent;
                color: {t['text_main']};
                border: none;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
                font-size: 24px;
                font-weight: bold;
            }}
            QPushButton#ArrowButton:hover {{
                background-color: transparent;
                color: {t['accent']};
            }}
            
            QPushButton {{
                background-color: {t['accent']};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {t['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {t['accent_pressed']};
            }}
            QPushButton:disabled {{
                background-color: {t['bg_tertiary']};
                color: {t['text_secondary']};
            }}

            QPushButton[class="secondary"] {{
                background-color: transparent;
                border: 1px solid {t['border']};
                color: {t['text_main']};
            }}
            QPushButton[class="secondary"]:hover {{
                border-color: {t['accent']};
                background-color: {t['bg_tertiary']};
            }}

            QPushButton[class="success"] {{
                background-color: {t['success']};
            }}
            QPushButton[class="success"]:hover {{
                background-color: #059669;
            }}

            QPushButton[class="danger"] {{
                background-color: {t['danger']};
            }}
            QPushButton[class="danger"]:hover {{
                background-color: #dc2626;
            }}

            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {t['input_bg']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 10px 12px;
                color: {t['text_main']};
                selection-background-color: {t['accent']};
                selection-color: white;
                font-size: 14px;
            }}

            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                width: 24px;
                background-color: transparent;
                border-left: 1px solid {t['border']};
            }}
            QSpinBox::up-button {{
                subcontrol-position: top right;
                border-top-right-radius: 7px;
                border-bottom: 1px solid {t['border']};
            }}
            QSpinBox::down-button {{
                subcontrol-position: bottom right;
                border-bottom-right-radius: 7px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {t['bg_tertiary']};
            }}
            QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
                background-color: {t['accent']};
            }}
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                width: 0;
                height: 0;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {t['accent']};
            }}
            QLineEdit:hover {{
                border: 1px solid {t['accent_hover']};
            }}
            QLineEdit::placeholder {{
                color: {t['text_secondary']};
            }}

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
                font-size: 18px;
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

            QTableWidget {{
                background-color: {t['bg_main']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                gridline-color: {t['border']};
                selection-background-color: {t['accent']};
                selection-color: white;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
            }}
            QTableWidget::item:selected {{
                background-color: rgba(59, 130, 246, 0.15);
                color: {t['text_main']};
            }}
            QHeaderView::section {{
                background-color: {t['bg_secondary']};
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid {t['border']};
                border-right: 1px solid {t['border']};
                font-weight: 600;
                color: {t['text_secondary']};
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QTableCornerButton::section {{
                background-color: {t['bg_secondary']};
                border: none;
            }}

            QScrollBar:vertical {{
                border: none;
                background: {t['bg_main']};
                width: 10px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scrollbar_handle']};
                min-height: 40px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: {t['bg_main']};
                height: 10px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {t['scrollbar_handle']};
                min-width: 40px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {t['accent']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}

            QDialog {{
                background-color: {t['bg_main']};
            }}
            
            QComboBox {{
                background-color: {t['bg_secondary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {t['text_main']};
                font-size: 13px;
            }}
            QComboBox:hover {{
                border: 2px solid {t['accent']};
            }}
            QComboBox:focus {{
                border: 2px solid {t['accent']};
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
            }}
            QComboBox QAbstractItemView {{
                background-color: {t['bg_secondary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                selection-background-color: {t['accent']};
                selection-color: white;
                color: {t['text_main']};
                outline: none;
                padding: 5px;
            }}

            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            
            QCheckBox {{
                spacing: 10px;
                color: {t['text_main']};
                font-size: 14px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {t['border']};
                border-radius: 5px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {t['accent']};
                border-color: {t['accent']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {t['accent']};
            }}
            
            QWidget#TitleBar {{
                background-color: {t['bg_secondary']};
                border-bottom: 1px solid {t['border']};
            }}
            QPushButton#TitleBarButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton#TitleBarButton:hover {{
                background-color: {t['bg_tertiary']};
            }}
            QPushButton#CloseButton:hover {{
                background-color: {t['danger']};
                color: white;
            }}

            QGroupBox {{
                border: 1px solid {t['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: {t['text_secondary']};
            }}

            QProgressBar {{
                border: none;
                border-radius: 6px;
                background-color: {t['bg_tertiary']};
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {t['accent']};
                border-radius: 6px;
            }}
        """

    @staticmethod
    def _get_check_icon_path():
        return "" 

    @staticmethod
    def get_heading_style(theme_name="dark"):
        t = StyleManager.get_theme(theme_name)
        return f"font-size: 24px; font-weight: bold; color: {t['text_main']}; margin-bottom: 10px;"

    @staticmethod
    def get_card_style(theme_name="dark"):
        t = StyleManager.get_theme(theme_name)
        return f"""
            QFrame {{
                background-color: {t['bg_card']};
                border: 1px solid {t['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """
