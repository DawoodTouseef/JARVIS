from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from typing import Optional, List, Dict
from jarvis_integration.themes.theme_manager import ThemeManager


class JarvisSelectField(QWidget):
    def __init__(self, label: str = "", options: Optional[List[str]] = None,
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

        self.combo = QComboBox()
        if options:
            self.combo.addItems(options)
        self.layout.addWidget(self.combo)

        self.apply_styles()

    def current_text(self):
        return self.combo.currentText()

    def set_options(self, options):
        self.combo.clear()
        self.combo.addItems(options)

    def apply_styles(self):
        """Apply className, ID, and sx styles to the combo box."""
        style = ""
        if self.className:
            class_style = self.theme_manager.get_class_styles(self.className)
            style += f"\nQComboBox {{ {class_style} }}"
        if self.id:
            id_style = self.theme_manager.get_id_styles(self.id)
            style += f"\nQComboBox#{self.id} {{ {id_style} }}"
        if self.sx:
            sx_style = "; ".join(f"{key}: {value}" for key, value in self.sx.items())
            style += f"\nQComboBox {{ {sx_style}; }}"
        self.combo.setStyleSheet(style)