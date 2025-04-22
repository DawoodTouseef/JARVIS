from PyQt5.QtWidgets import QWidget, QGridLayout
from PyQt5.QtCore import Qt
from typing import Optional, Dict
from jarvis_integration.themes.theme_manager import ThemeManager

class JarvisGridLayout(QWidget):
    def __init__(self, parent=None, columns: int = 2, spacing: int = 10,
                 sx: Optional[Dict[str, str]] = None, className: Optional[str] = None,
                 id: Optional[str] = None, theme: str = "default"):
        super().__init__(parent)
        self.theme_manager = ThemeManager(theme)
        self.layout = QGridLayout(self)
        self.layout.setSpacing(spacing)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.columns = columns
        self.className = className
        self.id = id
        self.sx = sx or {}

        if id:
            self.setObjectName(id)

        self.apply_styles()

    def add_widget(self, widget, row: int = None, col: int = None, row_span: int = 1, col_span: int = 1, alignment: Qt.AlignmentFlag = None):
        if row is None or col is None:
            row = self.layout.rowCount()
            col = 0
        if alignment:
            self.layout.addWidget(widget, row, col, row_span, col_span, alignment)
        else:
            self.layout.addWidget(widget, row, col, row_span, col_span)

    def apply_styles(self):
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
        return f"<JarvisGridLayout columns={self.columns} spacing={self.layout.spacing()} widgets={self.layout.count()}>"