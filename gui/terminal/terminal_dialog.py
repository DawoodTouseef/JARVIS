import os.path
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from .terminal_widget import TerminalWidget
from config import JARVIS_DIR

class TerminalDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Virtual Assistant Terminal")
        self.resize(800, 600)

        # Layout
        layout = QVBoxLayout()

        # Terminal widget
        self.terminal = TerminalWidget(self)
        layout.addWidget(self.terminal)

        self.setLayout(layout)

        # Load stylesheet
        self.load_stylesheet()

    def load_stylesheet(self):
        """Load external stylesheet"""
        try:
            with open(os.path.join(JARVIS_DIR, "gui", "terminal", "styles", "terminal.qss"), 'r') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    def closeEvent(self, event):
        """Clean up on close"""
        self.terminal.close()
        super().closeEvent(event)