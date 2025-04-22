from PyQt5.QtWidgets import QWidget, QHBoxLayout
from jarvis_integration.components.button import JarvisButton
from typing import Callable, List, Union, Dict,Optional
from jarvis_integration.themes.theme_manager import ThemeManager


class JarvisButtonGroup(QWidget):
    def __init__(
        self,
        labels: List[str],
        on_change: Callable[[int, str], None] = None,
        variant: Union[str, List[str], Dict[str, str]] = "outlined",
        color: Union[str, List[str], Dict[str, str]] = "secondary",
        size: Union[str, List[str], Dict[str, str]] = "medium",
        selected_index: int = 0,
        sx: Optional[Dict[str, str]] = None,
        className: Optional[str] = None,
        id: Optional[str] = None,
        theme: str = "default"
    ):
        super().__init__()
        self.theme_manager = ThemeManager(theme)
        self.on_change = on_change
        self.buttons: List[JarvisButton] = []
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.selected_index = selected_index
        self.labels = labels
        self.className = className
        self.id = id
        self.sx = sx or {}

        if id:
            self.setObjectName(id)

        for index, label in enumerate(labels):
            btn_variant = self._resolve_value(variant, index, label, "outlined")
            btn_color = self._resolve_value(color, index, label, "secondary")
            btn_size = self._resolve_value(size, index, label, "medium")

            btn = JarvisButton(
                text=label,
                on_click=lambda checked=False, idx=index, lbl=label: self.button_clicked(idx, lbl),
                variant=btn_variant,
                color=btn_color,
                size=btn_size,
                theme=theme
            )
            self.buttons.append(btn)
            self.layout.addWidget(btn)

        self.apply_styles()
        self.highlight_selected()

    def _resolve_value(self, source, index, label, default):
        if isinstance(source, str):
            return source
        elif isinstance(source, list):
            return source[index] if index < len(source) else default
        elif isinstance(source, dict):
            return source.get(label, default)
        return default

    def button_clicked(self, index, label):
        self.selected_index = index
        self.highlight_selected()
        if self.on_change:
            self.on_change(index, label)

    def highlight_selected(self):
        for i, btn in enumerate(self.buttons):
            btn.set_selected(i == self.selected_index)

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