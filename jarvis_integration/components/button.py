from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from typing import Callable, Optional, Dict
from jarvis_integration.utils.style_utils import darken_color, transparentize_color
from jarvis_integration.themes.theme_manager import ThemeManager

class JarvisButton(QPushButton):
    VALID_VARIANTS = {"contained", "outlined", "text"}
    VALID_COLORS = {"success", "error", "secondary", "primary", "default"}
    VALID_SIZES = {"small", "medium", "large"}

    def __init__(self,
                 text: str,
                 on_click: Optional[Callable] = None,
                 variant: str = "text",
                 color: str = "secondary",
                 size: str = "medium",
                 icon: Optional[QIcon] = None,
                 disableElevation: bool = False,
                 border_radius: int = 8,
                 sx: Optional[Dict[str, str]] = None,
                 className: Optional[str] = None,
                 id: Optional[str] = None,
                 theme: str = "default"):
        super().__init__(text)
        self.theme_manager = ThemeManager(theme)
        self.variant = variant
        self.color = color
        self.size = size
        self.disableElevation = disableElevation
        self.border_radius = border_radius
        self.className = className
        self.id = id
        self.sx = sx or {}

        if variant not in self.VALID_VARIANTS:
            raise ValueError(f"Invalid variant: {variant}. Choose from {self.VALID_VARIANTS}")
        if color not in self.VALID_COLORS:
            raise ValueError(f"Invalid color: {color}. Choose from {self.VALID_COLORS}")
        if size not in self.VALID_SIZES:
            raise ValueError(f"Invalid size: {size}. Choose from {self.VALID_SIZES}")
        if on_click is not None and not callable(on_click):
            raise ValueError("on_click must be a callable function")

        if icon:
            self.setIcon(icon)

        if on_click:
            self.clicked.connect(lambda checked: on_click())

        if id:
            self.setObjectName(id)

        self.setCursor(Qt.PointingHandCursor)
        self.set_style()

    def set_style(self):
        color_map = {
            "success": {"bg": "#4CAF50", "fg": "#ffffff", "border": "#4CAF50"},
            "error": {"bg": "#f44336", "fg": "#ffffff", "border": "#f44336"},
            "secondary": {"bg": "#2196F3", "fg": "#ffffff", "border": "#2196F3"},
            "primary": {"bg": "#3f51b5", "fg": "#ffffff", "border": "#3f51b5"},
            "default": {"bg": "#e0e0e0", "fg": "#000000", "border": "#e0e0e0"}
        }
        colors = color_map[self.color]

        if self.size == "small":
            padding = "5px 12px"
            font_size = "12px"
        elif self.size == "large":
            padding = "15px 30px"
            font_size = "16px"
        else:
            padding = "10px 20px"
            font_size = "14px"

        shadow = "box-shadow: none;" if self.disableElevation else \
                 "box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.2);"

        radius = f"{self.border_radius}px"

        if self.variant == "contained":
            style = f"""
                QPushButton {{
                    background-color: {colors['bg']};
                    color: {colors['fg']};
                    border: none;
                    border-radius: {radius};
                    padding: {padding};
                    font-size: {font_size};
                    {shadow}
                }}
                QPushButton:hover {{
                    background-color: {darken_color(colors['bg'], 0.1)};
                }}
                QPushButton:focus {{
                    outline: none;
                    border: 2px solid {transparentize_color(colors['bg'], 0.5)};
                }}
            """
        elif self.variant == "outlined":
            style = f"""
                QPushButton {{
                    background-color: transparent;
                    color: {colors['border']};
                    border: 2px solid {colors['border']};
                    border-radius: {radius};
                    padding: {padding};
                    font-size: {font_size};
                }}
                QPushButton:hover {{
                    background-color: {transparentize_color(colors['border'], 0.08)};
                }}
                QPushButton:focus {{
                    outline: none;
                    border: 2px solid {transparentize_color(colors['border'], 0.5)};
                }}
            """
        else:
            style = f"""
                QPushButton {{
                    background-color: transparent;
                    color: {colors['border']};
                    border: none;
                    border-radius: {radius};
                    padding: {padding};
                    font-size: {font_size};
                }}
                QPushButton:hover {{
                    background-color: {transparentize_color(colors['border'], 0.08)};
                }}
                QPushButton:focus {{
                    outline: none;
                    border: 1px solid {transparentize_color(colors['border'], 0.5)};
                }}
            """

        if self.className:
            class_style = self.theme_manager.get_class_styles(self.className)
            style += f"\nQPushButton {{ {class_style} }}"

        if self.id:
            id_style = self.theme_manager.get_id_styles(self.id)
            style += f"\nQPushButton#{self.id} {{ {id_style} }}"

        if self.sx:
            sx_style = "; ".join(f"{key}: {value}" for key, value in self.sx.items())
            style += f"\nQPushButton {{ {sx_style}; }}"

        self.setStyleSheet(style)

    def set_selected(self, is_selected: bool):
        self.set_style()
        if is_selected:
            self.setStyleSheet(self.styleSheet() + """
                QPushButton {
                    outline: 2px solid #FFD700;
                    border-width: 2px;
                }
            """)