from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QAbstractAnimation, QParallelAnimationGroup, QPoint, QRect
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget, QLayout

class AnimationManager:
    _running_animations = []
    
    @staticmethod
    def fade_in(widget: QWidget, duration=300):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        def cleanup():
            if widget.graphicsEffect() == effect:
                widget.setGraphicsEffect(None)
        
        anim.finished.connect(cleanup)
        widget._fade_anim = anim
        AnimationManager._running_animations.append(anim)
        anim.finished.connect(lambda: AnimationManager._running_animations.remove(anim) if anim in AnimationManager._running_animations else None)
        anim.start()

    @staticmethod
    def fade_out(widget: QWidget, duration=300, on_finished=None):
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
        AnimationManager._running_animations.append(anim)
        anim.start()

    @staticmethod
    def slide_in(widget: QWidget, start_pos: QPoint, end_pos: QPoint, duration=400):
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(duration)
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        widget._slide_anim = anim
        AnimationManager._running_animations.append(anim)
        anim.start()

    @staticmethod
    def scale_in(widget: QWidget, duration=200):
        widget.setScale(0.8)
        widget.setOpacity(0)
        
        anim_opacity = QPropertyAnimation(widget, b"opacity")
        anim_opacity.setDuration(duration)
        anim_opacity.setStartValue(0)
        anim_opacity.setEndValue(1)
        anim_opacity.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        widget._scale_anim = anim_opacity
        AnimationManager._running_animations.append(anim_opacity)
        anim_opacity.start()

    @staticmethod
    def pulse(widget: QWidget, scale=1.05, duration=150):
        anim = QPropertyAnimation(widget, b"scale")
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(scale)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        anim2 = QPropertyAnimation(widget, b"scale")
        anim2.setDuration(duration)
        anim2.setStartValue(scale)
        anim2.setEndValue(1.0)
        anim2.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        group = QParallelAnimationGroup()
        group.addAnimation(anim)
        group.addAnimation(anim2)
        AnimationManager._running_animations.append(group)
        group.start()

    @staticmethod
    def stop_all():
        for anim in AnimationManager._running_animations[:]:
            if anim.state() == QAbstractAnimation.State.Running:
                anim.stop()
        AnimationManager._running_animations.clear()
