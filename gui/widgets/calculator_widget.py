from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, 
    QGridLayout, QLineEdit, QLabel, QApplication, QCheckBox,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QScreen, QPen, QFont
from gui.styles import StyleManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Calculator")

class CalculatorWidget(QFrame):
    result_ready = pyqtSignal(str, bool)
    closed = pyqtSignal()

    def __init__(self, parent=None, data_manager=None, settings_key="fishing_calc_pos"):
        super().__init__(parent)
        self.data_manager = data_manager
        self.settings_key = settings_key
        
        # Load mode from settings
        self.is_accumulation_mode = True
        if self.data_manager:
            self.is_accumulation_mode = self.data_manager.get_setting("calc_accumulation_mode", True)
        
        # Modern Palette
        self.colors = {
            'bg': '#1e2124',
            'header': '#2f3136',
            'display_bg': '#000000',
            'display_text': '#43b581',
            'btn_normal': '#36393f',
            'btn_hover': '#4f545c',
            'btn_pressed': '#202225',
            'accent': '#7289da',
            'accent_hover': '#677bc4',
            'text': '#ffffff',
            'text_muted': '#b9bbbe',
            'border': '#202225'
        }
        
        # Fixed size based on exact specifications - REFINED COMPACT
        self.setFixedSize(260, 460) 
        
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.isDragging = False
        self.dragPosition = QPoint()
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(250)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.finished.connect(self._on_fade_finished)
        
        self.setup_ui()
        self.expression = ""
        
        # Modern UI Styles - REFINED COMPACT
        self.setStyleSheet(f"""
            QFrame#MainFrame {{
                background-color: {self.colors['bg']};
                border-radius: 12px;
                border: 1px solid {self.colors['border']};
            }}
            QFrame#HeaderFrame {{
                background-color: {self.colors['header']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid {self.colors['border']};
            }}
            QLineEdit {{
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 20px; 
                font-weight: 600;
                padding: 12px; 
                min-height: 40px; 
                background: {self.colors['display_bg']};
                color: {self.colors['display_text']};
                border-radius: 8px; 
                border: 1px solid {self.colors['border']};
                margin: 0 12px; 
            }}
           QPushButton {{
    background-color: {self.colors['btn_normal']};
    color: {self.colors['text']};
    border: 1px solid {self.colors['border']};
    border-radius: 8px;

    font-size: 14px;
    font-weight: 600;

    min-height: 0px;
    min-width: 0px;
    padding: 0px;
}}
            QPushButton#ActionBtn {{
                background-color: {self.colors['accent']};
                color: white;
                border: none;
                min-width: 108px; 
            }}
            QPushButton:hover {{
                background-color: {self.colors['btn_hover']};
                border-color: {self.colors['accent']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['btn_pressed']};
                padding-top: 2px;
            }}
            QPushButton#ActionBtn:hover {{
                background-color: {self.colors['accent_hover']};
            }}
            QPushButton#OpBtn {{
                background-color: {self.colors['header']};
                color: {self.colors['accent']};
                border: 1px solid {self.colors['border']};
            }}
            QLabel#HeaderTitle {{
                color: {self.colors['text']};
                font-weight: 600; 
                font-size: 14px; 
            }}
            /* Modern Toggle Style */
            QCheckBox {{
                color: {self.colors['text']};
                font-size: 10px;
                font-weight: 400;
                spacing: 10px;
                padding: 4px;
                margin: 0 12px;
            }}
            QCheckBox::indicator {{
                width: 28px;
                height: 14px;
            }}
            QCheckBox::indicator:unchecked {{
                image: none;
                background: {self.colors['btn_normal']};
                border-radius: 7px;
                border: 1px solid {self.colors['border']};
            }}
            QCheckBox::indicator:checked {{
                image: none;
                background: {self.colors['accent']};
                border-radius: 7px;
                border: 1px solid {self.colors['accent_hover']};
            }}
        """)

    def setup_ui(self):
        # Container to apply border-radius properly with shadow
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_frame = QFrame()
        self.main_frame.setObjectName("MainFrame")
        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(0, 0, 0, 16) 
        layout.setSpacing(10) 
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.main_frame.setGraphicsEffect(shadow)
        
        # Header - REFINED COMPACT
        self.header_frame = QFrame()
        self.header_frame.setObjectName("HeaderFrame")
        self.header_frame.setFixedHeight(48) 
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(16, 0, 16, 0) 
        
        title = QLabel("Калькулятор")
        title.setObjectName("HeaderTitle")
        header_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18) 
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 18px; 
                font-weight: bold; 
                color: #ffffff;
                padding: 0;
                margin: 0;
            }}
            QPushButton:hover {{
                color: #ff4757;
            }}
        """)
        self.close_btn.clicked.connect(self.animate_hide)
        header_layout.addWidget(self.close_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(self.header_frame)
        
        # Space between header and content
        layout.addSpacing(8) 
        
        # Mode Toggle (Accumulation)
        self.mode_toggle = QCheckBox("Накапливать сумму")
        self.mode_toggle.setChecked(self.is_accumulation_mode)
        self.mode_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_toggle.toggled.connect(self.on_mode_toggled)
        layout.addWidget(self.mode_toggle)
        
        # Display
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setPlaceholderText("0")
        self.display.textChanged.connect(self.adjust_display_font)
        layout.addWidget(self.display)
        
        # Grid Container 
        grid_container = QFrame()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(16, 0, 16, 0) 
        grid_layout.setSpacing(6) 
        
        buttons = [
            ('C', 0, 0), ('%', 0, 1), ('/', 0, 2), ('⌫', 0, 3),
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('*', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('-', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('+', 3, 3),
            ('0', 4, 0), ('.', 4, 1), ('=', 4, 2, 1, 2)
        ]
        
        operators = ['/', '*', '-', '+', '%', '⌫', 'C']
        
        for b in buttons:
            btn = QPushButton(str(b[0]))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(35, 30) 
            
            if b[0] == '=':
                btn.setObjectName("ActionBtn")
                btn.setFixedSize(74, 40) 
            elif b[0] in operators:
                btn.setObjectName("OpBtn")
            
            if len(b) == 5:
                grid_layout.addWidget(btn, b[1], b[2], b[3], b[4])
            else:
                grid_layout.addWidget(btn, b[1], b[2])
                
            btn.clicked.connect(lambda checked, t=b[0]: self.on_click(t))
            
        layout.addWidget(grid_container)
        self.main_layout.addWidget(self.main_frame)

    def adjust_display_font(self):
        """Dynamically shrinks font size for long numbers."""
        text = self.display.text()
        length = len(text)
        
        # Base font size: 30px
        base_size = 30
        
        if length > 12:
            new_size = max(12, base_size - (length - 12) * 2)
        elif length > 8:
            new_size = max(18, base_size - (length - 8) * 2)
        else:
            new_size = base_size
            
        self.display.setStyleSheet(self.display.styleSheet() + f"font-size: {new_size}px;")

    def on_mode_toggled(self, checked):
        self.is_accumulation_mode = checked
        if self.data_manager:
            self.data_manager.set_setting("calc_accumulation_mode", checked)

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()
        
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.on_enter_pressed()
        elif key == Qt.Key.Key_Escape:
            self.animate_hide()
        elif key == Qt.Key.Key_Backspace:
            self.on_click('⌫')
        elif key == Qt.Key.Key_Delete or text.lower() == 'c':
            self.on_click('C')
        elif text in "0123456789.+-*/%":
            if text == ',': text = '.'
            self.on_click(text)
        elif key == Qt.Key.Key_Comma:
            self.on_click('.')
        elif key == Qt.Key.Key_Equal:
            self.on_click('=')
        else:
            super().keyPressEvent(event)

    def on_click(self, text):
        try:
            if text == 'C':
                self.expression = ""
            elif text == '⌫':
                self.expression = self.expression[:-1]
            elif text == '=':
                self.calculate_expression()
            else:
                if text in "+-*/%" and (not self.expression or self.expression[-1] in "+-*/%"):
                    return
                self.expression += str(text)
            self.display.setText(self.expression)
        except Exception as e:
            logger.error(f"Error on click {text}: {e}")
            self.expression = "Error"
            self.display.setText(self.expression)

    def calculate_expression(self):
        try:
            if not self.expression: return
            safe_expr = self.expression.replace('%', '/100')
            if not all(c in "0123456789.+-*/() " for c in safe_expr):
                raise ValueError("Invalid characters")
                
            result = eval(safe_expr)
            self.expression = str(round(result, 2))
            self.display.setText(self.expression)
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            self.expression = "Error"
            self.display.setText(self.expression)

    def on_enter_pressed(self):
        if not self.expression or self.expression == "Error":
            return
        if any(op in self.expression for op in "+-*/%"):
            self.calculate_expression()
        self.emit_result()

    def emit_result(self):
        if self.expression and self.expression != "Error":
            self.result_ready.emit(self.expression, self.is_accumulation_mode)
            self.animate_hide()

    def animate_hide(self):
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()

    def _on_fade_finished(self):
        if self.fade_animation.endValue() == 0.0:
            self.hide()
            self.setWindowOpacity(1.0)

    def showEvent(self, event):
        self.setWindowOpacity(0.0)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        super().showEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # IMPROVED: Allow dragging from the entire header frame area
            if self.header_frame.underMouse():
                self.isDragging = True
                self.dragPosition = event.globalPosition().toPoint() - self.pos()
                event.accept()

    def mouseMoveEvent(self, event):
        if self.isDragging:
            new_pos = event.globalPosition().toPoint() - self.dragPosition
            current_screen = QApplication.screenAt(event.globalPosition().toPoint()) or QApplication.primaryScreen()
            screen_geo = current_screen.availableGeometry()
            
            x = max(screen_geo.left(), min(new_pos.x(), screen_geo.right() - self.width()))
            y = max(screen_geo.top(), min(new_pos.y(), screen_geo.bottom() - self.height()))
            
            self.move(x, y)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.isDragging = False
        if self.data_manager:
            self.data_manager.set_setting(self.settings_key, [self.pos().x(), self.pos().y()])

    def hideEvent(self, event):
        self.closed.emit()
        super().hideEvent(event)


