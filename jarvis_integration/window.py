from PyQt5.QtWidgets import QMainWindow, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QMimeData
from PyQt5.QtGui import QFont
from typing import Optional, Dict, List, Union, Callable
from jarvis_integration.themes.theme_manager import ThemeManager
from jarvis_integration.components.text_field import JarvisTextField
from jarvis_integration.components.file_field import JarvisFileField
from jarvis_integration.components.button import JarvisButton
from jarvis_integration.components.select_field import JarvisSelectField

class JarvisWindow:
    def __init__(self, theme: str = "default"):
        self.theme_manager = ThemeManager(theme)
        self.window = None
        self.layout = None
        self.widgets = {}
        self.animations = {}
        self.is_dialog = False
        self.accept_action = None
        self.reject_action = None

    def main_window(self, title: str = "Jarvis Window", width: int = 600, height: int = 600, resizable: bool = True) -> 'JarvisWindow':
        self.window = QMainWindow()
        self.window.setWindowTitle(title)
        self.window.setGeometry(100, 100, width, height)
        self.window.setMinimumSize(400, 500)
        if not resizable:
            self.window.setFixedSize(width, height)
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.is_dialog = False
        return self

    def dialog(self, title: str = "Jarvis Dialog", width: int = 400, height: int = 250, modal: bool = True, parent: Optional[QWidget] = None) -> 'JarvisWindow':
        self.window = QDialog(parent)
        self.window.setWindowTitle(title)
        self.window.setGeometry(150, 150, width, height)
        self.window.setMinimumSize(300, 200)
        self.window.setModal(modal)
        self.layout = QVBoxLayout(self.window)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.is_dialog = True
        return self

    def set_style(self, style: Dict[str, str]) -> 'JarvisWindow':
        css = "; ".join(f"{k.replace('_', '-')}: {v}" for k, v in style.items())
        self.window.setStyleSheet(f"QWidget {{ {css} }}")
        return self

    def add_layout(self, layout_type: str = "vertical", spacing: int = 10, row: int = None, col: int = None, row_span: int = 1, col_span: int = 1) -> 'JarvisWindow':
        if layout_type == "vertical":
            new_layout = QVBoxLayout()
        elif layout_type == "horizontal":
            new_layout = QHBoxLayout()
        elif layout_type == "grid":
            new_layout = QGridLayout()
        else:
            raise ValueError(f"Unsupported layout: {layout_type}")
        new_layout.setSpacing(spacing)
        new_layout.setContentsMargins(0, 0, 0, 0)
        if isinstance(self.layout, QGridLayout) and row is not None and col is not None:
            self.layout.addLayout(new_layout, row, col, row_span, col_span)
        else:
            self.layout.addLayout(new_layout)
        self.layout = new_layout
        return self

    def end_layout(self) -> 'JarvisWindow':
        parent_widget = self.layout.parentWidget()
        if parent_widget and parent_widget.layout():
            self.layout = parent_widget.layout()
        return self

    def add_text(self, text: str, font_size: int = 14, style: Dict[str, str] = None, id: str = None, draggable: bool = False, align: str = "center") -> 'JarvisWindow':
        widget = QLabel(text)
        font = QFont()
        font.setPointSize(font_size)
        widget.setFont(font)
        widget.setMaximumWidth(500)
        if style:
            css = "; ".join(f"{k.replace('_', '-')}: {v}" for k, v in style.items())
            widget.setStyleSheet(f"QLabel {{ {css} }}")
        if id:
            self.widgets[id] = widget
            widget.setObjectName(id)
        if draggable:
            widget.setAcceptDrops(True)
            widget.mousePressEvent = lambda event: self._start_drag(event, widget)
            widget.dragEnterEvent = lambda event: event.acceptProposedAction()
            widget.dropEvent = lambda event: self._handle_drop(event, widget)
        alignment = self._parse_alignment(align)
        if isinstance(self.layout, QGridLayout):
            self.layout.addWidget(widget, self.layout.rowCount(), 0, alignment=alignment)
        else:
            self.layout.addWidget(widget, alignment=alignment)
        return self

    def add_text_field(self, label: str = "", placeholder: str = "", type: str = "text", icon: str = None, full_width: bool = False, color: str = "primary", default_value: str = "", id: str = None, style: Dict[str, str] = None, draggable: bool = False, row: int = None, col: int = None) -> 'JarvisWindow':
        widget = JarvisTextField(label=label, placeholder=placeholder, type=type, icon=icon, fullWidth=full_width, color=color, defaultValue=default_value, sx=style, id=id)
        if id:
            self.widgets[id] = widget
        if draggable:
            widget.setAcceptDrops(True)
            widget.mousePressEvent = lambda event: self._start_drag(event, widget)
            widget.dragEnterEvent = lambda event: event.acceptProposedAction()
            widget.dropEvent = lambda event: self._handle_drop(event, widget)
        if isinstance(self.layout, QGridLayout) and row is not None and col is not None:
            self.layout.addWidget(widget, row, col)
        else:
            self.layout.addWidget(widget)
        return self

    def add_file_field(self, label: str = "", placeholder: str = "", select_type: str = "file", file_filter: str = "All Files (*.*)", full_width: bool = False, color: str = "primary", default_value: str = "", id: str = None, style: Dict[str, str] = None, draggable: bool = False, row: int = None, col: int = None, validate_func: Optional[Callable] = None) -> 'JarvisWindow':
        widget = JarvisFileField(
            label=label,
            placeholder=placeholder,
            select_type=select_type,
            file_filter=file_filter,
            fullWidth=full_width,
            color=color,
            defaultValue=default_value,
            sx=style,
            id=id,
            validate_func=validate_func
        )
        if id:
            self.widgets[id] = widget
        if draggable:
            widget.setAcceptDrops(True)
            widget.mousePressEvent = lambda event: self._start_drag(event, widget)
            widget.dragEnterEvent = lambda event: event.acceptProposedAction()
            widget.dropEvent = lambda event: self._handle_drop(event, widget)
        if isinstance(self.layout, QGridLayout) and row is not None and col is not None:
            self.layout.addWidget(widget, row, col)
        else:
            self.layout.addWidget(widget)
        return self

    def add_button(self, text: str, on_click: Callable = None, style: Dict[str, str] = None, id: str = None, variant: str = "contained", color: str = "primary", size: str = "medium", draggable: bool = False, row: int = None, col: int = None) -> 'JarvisWindow':
        widget = JarvisButton(text=text, on_click=on_click, variant=variant, color=color, size=size, sx=style, id=id)
        widget.setMaximumWidth(500)
        if id:
            self.widgets[id] = widget
        if draggable:
            widget.setAcceptDrops(True)
            widget.mousePressEvent = lambda event: self._start_drag(event, widget)
            widget.dragEnterEvent = lambda event: event.acceptProposedAction()
            widget.dropEvent = lambda event: self._handle_drop(event, widget)
        if isinstance(self.layout, QGridLayout) and row is not None and col is not None:
            self.layout.addWidget(widget, row, col)
        else:
            self.layout.addWidget(widget)
        return self

    def add_select(self, label: str = "", options: List[str] = None, default_value: str = "", style: Dict[str, str] = None, id: str = None, draggable: bool = False, row: int = None, col: int = None) -> 'JarvisWindow':
        widget = JarvisSelectField(label=label, options=options)
        widget.setMaximumWidth(500)
        if default_value:
            widget.combo.setCurrentText(default_value)
        if style:
            css = "; ".join(f"{k.replace('_', '-')}: {v}" for k, v in style.items())
            widget.combo.setStyleSheet(f"QComboBox {{ {css} }}")
        if id:
            self.widgets[id] = widget
        if draggable:
            widget.setAcceptDrops(True)
            widget.mousePressEvent = lambda event: self._start_drag(event, widget)
            widget.dragEnterEvent = lambda event: event.acceptProposedAction()
            widget.dropEvent = lambda event: self._handle_drop(event, widget)
        if isinstance(self.layout, QGridLayout) and row is not None and col is not None:
            self.layout.addWidget(widget, row, col)
        else:
            self.layout.addWidget(widget)
        return self

    def set_dialog_actions(self, accept_text: str = "OK", reject_text: str = "Cancel", accept_action: Callable = None, reject_action: Callable = None) -> 'JarvisWindow':
        if not self.is_dialog:
            raise ValueError("Dialog actions can only be set for dialogs")
        self.accept_action = accept_action
        self.reject_action = reject_action
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        if accept_text:
            accept_button = JarvisButton(text=accept_text, on_click=self._accept_dialog, variant="contained", color="success")
            accept_button.setMaximumWidth(150)
            action_layout.addWidget(accept_button)
        if reject_text:
            reject_button = JarvisButton(text=reject_text, on_click=self._reject_dialog, variant="outlined", color="error")
            reject_button.setMaximumWidth(150)
            action_layout.addWidget(reject_button)
        self.layout.addLayout(action_layout)
        return self

    def animate(self, target_id: str, type: str = "fade", duration: int = 1000, easing: str = "InOutQuad", from_value=None, to_value=None, auto_start: bool = False, loop: bool = False, trigger_id: str = None) -> 'JarvisWindow':
        if target_id not in self.widgets:
            return self
        widget = self.widgets[target_id]
        if type == "fade":
            anim = QPropertyAnimation(widget, b"windowOpacity")
            anim.setStartValue(from_value if from_value is not None else 0.0)
            anim.setEndValue(to_value if to_value is not None else 1.0)
        elif type == "slide":
            anim = QPropertyAnimation(widget, b"geometry")
            start_rect = widget.geometry()
            end_rect = QRect(0, start_rect.y(), start_rect.width(), start_rect.height())
            anim.setStartValue(start_rect)
            anim.setEndValue(end_rect)
        elif type == "scale":
            anim = QPropertyAnimation(widget, b"geometry")
            start_rect = widget.geometry()
            scale_factor = to_value if to_value is not None else 1.0
            anim.setStartValue(start_rect)
            anim.setEndValue(QRect(0, start_rect.y(), int(start_rect.width() * scale_factor), int(start_rect.height() * scale_factor)))
        else:
            return self
        anim.setDuration(duration)
        anim.setEasingCurve(getattr(QEasingCurve, easing, QEasingCurve.InOutQuad))
        if loop:
            anim.finished.connect(anim.start)
        if trigger_id and trigger_id in self.widgets:
            self.widgets[trigger_id].clicked.connect(anim.start)
        if auto_start:
            anim.start()
        self.animations[target_id + "_" + type] = anim
        return self

    def show(self) -> None:
        if self.is_dialog:
            self.window.exec_()
        else:
            self.window.show()

    def _accept_dialog(self):
        if self.accept_action:
            self.accept_action()
        self.window.accept()

    def _reject_dialog(self):
        if self.reject_action:
            self.reject_action()
        self.window.reject()

    def _parse_alignment(self, align: str) -> Qt.AlignmentFlag:
        align = align.lower()
        if align == "center":
            return Qt.AlignCenter
        elif align == "left":
            return Qt.AlignLeft
        elif align == "right":
            return Qt.AlignRight
        elif align == "top":
            return Qt.AlignTop
        elif align == "bottom":
            return Qt.AlignBottom
        return Qt.AlignCenter

    def _start_drag(self, event, widget):
        if event.buttons() != Qt.LeftButton:
            return
        drag = QDrag(widget)
        mime_data = QMimeData()
        mime_data.setText(widget.objectName())
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)

    def _handle_drop(self, event, widget):
        source_id = event.mimeData().text()
        if source_id in self.widgets:
            source_widget = self.widgets[source_id]
            source_layout = source_widget.parent().layout() if source_widget.parent() else None
            target_layout = widget.parent().layout() if widget.parent() else None
            if source_layout and target_layout:
                source_index = source_layout.indexOf(source_widget)
                target_index = target_layout.indexOf(widget)
                source_layout.removeWidget(source_widget)
                target_layout.removeWidget(widget)
                source_layout.insertWidget(source_index, widget)
                target_layout.insertWidget(target_index, source_widget)
                event.acceptProposedAction()