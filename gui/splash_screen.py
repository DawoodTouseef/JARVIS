from PyQt5.QtWidgets import QSplashScreen, QLabel, QGraphicsDropShadowEffect, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont, QColor


class SplashScreen(QSplashScreen):
    def __init__(self, background_path="assets/splash.png", message="Loading J.A.R.V.I.S"):
        super().__init__(QPixmap(background_path))
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowOpacity(0.95)
        self.dot_count = 0
        self.loading_text_base = message

        # Container widget for styling and layout
        self.container = QWidget(self)
        self.container.setGeometry(0, self.height() - 80, self.width(), 60)
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Main loading label
        self.label = QLabel(self.loading_text_base + "...", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(0, self.height() - 60, self.width(), 40)
        self.label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        self.label.setFont(QFont("Consolas", 14))

        # Glow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 255, 255))  # Cyan glow
        shadow.setOffset(0, 0)
        self.label.setGraphicsEffect(shadow)

        self.layout.addWidget(self.label)

        # Timer for animated dots
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_loading_text)
        self.timer.start(400)

    def animate_loading_text(self):
        dots = "." * ((self.dot_count % 4) + 1)
        self.label.setText(f"{self.loading_text_base}{dots}")
        self.dot_count += 1

    def update_message(self, text: str):
        self.loading_text_base = text
        self.dot_count = 0
        self.label.setText(self.loading_text_base + "...")
        self.repaint()
