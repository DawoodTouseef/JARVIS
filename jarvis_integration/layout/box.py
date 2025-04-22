from PyQt5.QtWidgets import QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from typing import Optional, Dict
from jarvis_integration.themes.theme_manager import ThemeManager


class JarvisBoxLayout(QWidget):
    def __init__(self, parent=None, spacing=15,
                 sx: Optional[Dict[str, str]] = None, className: Optional[str] = None,
                 id: Optional[str] = None, theme: str = "default"):
        super().__init__(parent)
        self.theme_manager = ThemeManager(theme)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(spacing)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.className = className
        self.id = id
        self.sx = sx or {}

        if id:
            self.setObjectName(id)

        self.apply_styles()

    def add_widget(self, widget, stretch=0, alignment=None):
        """Convenient method to add widgets to the layout."""
        if alignment is not None:
            self.layout.addWidget(widget, stretch, alignment)
        else:
            self.layout.addWidget(widget, stretch)

    def apply_styles(self):
        """Apply className, ID, and sx styles."""
        style = ""
        if self.className:
            class_style = self.theme_manager.get_class_styles(self.className)
            style += f"\nQWidget {{ {class_style} }}"
        if self.id:
            id_style = self.theme_manager.get_id_styles(self.id)
            style += f"\nQWidget#{self.id} {{ {id_style} }}"
        if self.sx:
            sx_style = "; ".join(f"{key}: {value}" for key, value in self.sx.items())
            style += f"\nQWidget {{ {sx_style}; }}"
        self.setStyleSheet(style)

    def __repr__(self):
        return f"<JarvisBoxLayout spacing={self.layout.spacing()} widgets={self.layout.count()}>"