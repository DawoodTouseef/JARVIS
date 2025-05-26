from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
from typing import Optional, Dict
from jarvis_integration.themes.theme_manager import ThemeManager


class JarvisPasswordField(QWidget):
    def __init__(self, label: str = "", placeholder: str = "",
                 sx: Optional[Dict[str, str]] = None, className: Optional[str] = None,
                 id: Optional[str] = None, theme: str = "default"):
        super().__init__()
        self.theme_manager = ThemeManager(theme)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.className = className
        self.id = id
        self.sx = sx or {}

        if id:
            self.setObjectName(id)

        self.label = QLabel(label)
        self.layout.addWidget(self.label)

        self.input_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setEchoMode(QLineEdit.Password)

        self.toggle_button = QPushButton("👁")
        self.toggle_button.setFixedWidth(30)
        self.toggle_button.setCheckable(True)
        self.toggle_button.toggled.connect(self.toggle_password)

        self.input_layout.addWidget(self.input)
        self.input_layout.addWidget(self.toggle_button)
        self.layout.addLayout(self.input_layout)

        self.apply_styles()

    def toggle_password(self, checked):
        self.input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def text(self):
        return self.input.text()

    def set_text(self, text):
        self.input.setText(text)

    def apply_styles(self):
        """Apply className, ID, and sx styles to the input widget."""
        style = ""
        if self.className:
            class_style = self.theme_manager.get_class_styles(self.className)
            style += f"\nQLineEdit {{ {class_style} }}"
        if self.id:
            id_style = self.theme_manager.get_id_styles(self.id)
            style += f"\nQLineEdit#{self.id} {{ {id_style} }}"
        if self.sx:
            sx_style = "; ".join(f"{key}: {value}" for key, value in self.sx.items())
            style += f"\nQLineEdit {{ {sx_style}; }}"
        self.input.setStyleSheet(style)