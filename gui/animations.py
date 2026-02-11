from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QAbstractAnimation, QParallelAnimationGroup, QPoint
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget

class AnimationManager:
    @staticmethod
    def fade_in(widget: QWidget, duration=300):
        """Fades in a widget from 0 to 1 opacity."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Cleanup effect after animation to avoid "Painter not active" errors
        # and improve performance
        def cleanup():
            widget.setGraphicsEffect(None)
            
        anim.finished.connect(cleanup)
        
        # Keep reference to avoid GC
        widget._fade_anim = anim
        
        anim.start()

    @staticmethod
    def fade_out(widget: QWidget, duration=300, on_finished=None):
        """Fades out a widget from 1 to 0 opacity."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        if on_finished:
            anim.finished.connect(on_finished)
            
        widget._fade_anim = anim
        anim.start()

    @staticmethod
    def slide_in(widget: QWidget, start_pos: QPoint, end_pos: QPoint, duration=400):
        """Slides a widget from start_pos to end_pos."""
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(duration)
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.setEasingCurve(QEasingCurve.Type.OutBack) # Bouncy effect
        
        widget._slide_anim = anim
        anim.start()
