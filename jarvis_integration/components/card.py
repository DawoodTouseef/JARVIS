from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QWidget
from typing import Optional, Dict
from jarvis_integration.themes.theme_manager import ThemeManager


class JarvisCard(QGroupBox):
    def __init__(self, title: str, content: Optional[str] = None,
                 sx: Optional[Dict[str, str]] = None, className: Optional[str] = None,
                 id: Optional[str] = None, theme: str = "default"):
        super().__init__(title)
        self.theme_manager = ThemeManager(theme)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.className = className
        self.id = id
        self.sx = sx or {}

        if id:
            self.setObjectName(id)

        # If content is provided, add it as a label
        if content:
            self.layout.addWidget(QLabel(content))

        self.apply_styles()

    def add_widget(self, widget):
        """Method to add any custom widget to the card."""
        self.layout.addWidget(widget)

    def apply_styles(self):
        """Apply base, className, ID, and sx styles."""
        style = """
            QGroupBox {
                border: 2px solid #00BCD4;
                border-radius: 10px;
                margin-top: 20px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #00BCD4;
            }
        """
        if self.className:
            class_style = self.theme_manager.get_class_styles(self.className)
            style += f"\nQGroupBox {{ {class_style} }}"
        if self.id:
            id_style = self.theme_manager.get_id_styles(self.id)
            style += f"\nQGroupBox#{self.id} {{ {id_style} }}"
        if self.sx:
            sx_style = "; ".join(f"{key}: {value}" for key, value in self.sx.items())
            style += f"\nQGroupBox {{ {sx_style}; }}"
        self.setStyleSheet(style)