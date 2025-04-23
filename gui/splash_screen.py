from PyQt5.QtWidgets import (
    QSplashScreen, QLabel, QGraphicsDropShadowEffect,
    QVBoxLayout, QWidget, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont, QColor


class SplashScreen(QSplashScreen):
    def __init__(self, background_path="assets/splash.png", message="Loading J.A.R.V.I.S"):
        super().__init__(QPixmap(background_path))

        # 🛠 Fix: keep it always on top
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setEnabled(False)  # Prevent accidental clicks hiding it
        self.setFocusPolicy(Qt.NoFocus)

        self.loading_text_base = message
        self.dot_count = 0

        # UI Container
        self.container = QWidget(self)
        self.container.setGeometry(0, self.height() - 100, self.width(), 80)
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(20, 0, 20, 10)

        # Loading label
        self.label = QLabel(self.loading_text_base + "...", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Consolas", 14, QFont.Bold))
        self.label.setStyleSheet("color: white;")
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(25)
        glow.setColor(QColor(0, 255, 255))
        glow.setOffset(0, 0)
        self.label.setGraphicsEffect(glow)
        self.layout.addWidget(self.label)

        # Progress bar
        self.progress = QProgressBar(self)
        self.progress.setFixedHeight(20)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #1c1c1c;
                color: white;
                border-radius: 10px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ffff, stop:1 #0077ff
                );
                border-radius: 10px;
            }
        """)
        self.layout.addWidget(self.progress)

        # Timer for animated dots
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_loading_text)
        self.timer.start(400)

    def animate_loading_text(self):
        dots = "." * ((self.dot_count % 4) + 1)
        self.label.setText(f"{self.loading_text_base}{dots}")
        self.dot_count += 1

    def update_message(self, text: str, progress: int = None):
        self.loading_text_base = text
        self.dot_count = 0
        self.label.setText(self.loading_text_base + "...")
        if progress is not None:
            self.progress.setValue(progress)
        self.repaint()

    def mousePressEvent(self, event):
        event.ignore()  # Prevent hiding splash on click
