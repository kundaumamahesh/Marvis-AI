from PyQt6.QtCore import (
    QPropertyAnimation
)

class Animations:

    @staticmethod
    def fade(widget):

        animation = QPropertyAnimation(
            widget,
            b"windowOpacity"
        )

        animation.setDuration(500)

        animation.setStartValue(0)

        animation.setEndValue(1)

        animation.start()
