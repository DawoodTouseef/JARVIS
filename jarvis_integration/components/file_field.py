from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QSizePolicy, QPushButton, QFileDialog
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag
from typing import Optional, Callable, Dict
from jarvis_integration.themes.theme_manager import ThemeManager
import os

class JarvisFileField(QWidget):
    VALID_COLORS = {"primary", "secondary", "success", "error"}
    VALID_SELECT_TYPES = {"file", "folder"}

    def __init__(self,
                 label: str = "",
                 placeholder: str = "",
                 validate_func: Optional[Callable] = None,
                 select_type: str = "file",
                 file_filter: str = "All Files (*.*)",
                 sx: Optional[Dict[str, str]] = None,
                 className: Optional[str] = None,
                 id: Optional[str] = None,
                 theme: str = "default",
                 fullWidth: bool = False,
                 color: str = "primary",
                 defaultValue: str = ""):
        super().__init__()
        self.theme_manager = ThemeManager(theme)
        self.validate_func = validate_func
        self.select_type = select_type.lower()
        self.file_filter = file_filter
        self.className = className
        self.id = id
        self.sx = sx or {}
        self.fullWidth = fullWidth
        self.color = color.lower()
        self.defaultValue = defaultValue

        if self.color not in self.VALID_COLORS:
            raise ValueError(f"Invalid color: {self.color}. Choose from {self.VALID_COLORS}")
        if self.select_type not in self.VALID_SELECT_TYPES:
            raise ValueError(f"Invalid select_type: {self.select_type}. Choose from {self.VALID_SELECT_TYPES}")

        if id:
            self.setObjectName(id)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)

        if label:
            self.label = QLabel(label)
            self.label.setStyleSheet("font-size: 14px; color: #333;")
            self.layout.addWidget(self.label)

        self.input_layout = QHBoxLayout()
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        self.input_layout.setSpacing(5)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setReadOnly(True)
        self.input.setText(defaultValue)
        self.input.textChanged.connect(self.validate)

        self.select_button = QPushButton("📂")
        self.select_button.setFixedWidth(30)
        self.select_button.clicked.connect(self.open_dialog)

        self.input_layout.addWidget(self.input)
        self.input_layout.addWidget(self.select_button)
        self.layout.addLayout(self.input_layout)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        self.layout.addWidget(self.error_label)

        self.setAcceptDrops(True)

        if self.fullWidth:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.setMaximumWidth(500)

        self.apply_styles()

    def open_dialog(self):
        if self.select_type == "file":
            path, _ = QFileDialog.getOpenFileName(self, "Select File", "", self.file_filter)
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if path:
            self.input.setText(path)
            self.validate()

    def validate(self):
        if not hasattr(self, 'error_label'):
            return

        text = self.input.text()
        if not text:
            self.error_label.setText("Please select a file or folder")
            return

        if self.validate_func:
            result = self.validate_func(text)
            if result is not True:
                self.error_label.setText(result)
            else:
                self.error_label.setText("")
        elif not os.path.exists(text):
            self.error_label.setText("Invalid file or folder path")
        else:
            self.error_label.setText("")

    def text(self):
        return self.input.text()

    def set_text(self, text):
        self.input.setText(text)
        self.validate()

    def apply_styles(self):
        highlight_color = self.theme_manager.get_color(self.color)
        style = f"""
            QLineEdit {{
                border: 1px solid #ccc;
                padding: 6px;
                border-radius: 4px;
                font-size: 14px;
                background: #fff;
            }}
            QLineEdit:focus {{
                border: 2px solid {highlight_color};
            }}
        """
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

        button_style = f"""
            QPushButton {{
                color: {self.theme_manager.get_color('text')};
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f9f9f9;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #e0e0e0;
            }}
        """
        if self.className:
            button_style += f"\nQPushButton {{ {self.theme_manager.get_class_styles(self.className)} }}"
        if self.id:
            button_style += f"\nQPushButton#{self.id}-button {{ {self.theme_manager.get_id_styles(self.id)} }}"
        self.select_button.setStyleSheet(button_style)
        if self.id:
            self.select_button.setObjectName(f"{self.id}-button")

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.id:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.id)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0].toLocalFile()
            if (self.select_type == "file" and os.path.isfile(url)) or (self.select_type == "folder" and os.path.isdir(url)):
                self.set_text(url)
                event.acceptProposedAction()
        elif event.mimeData().hasText():
            source_id = event.mimeData().text()
            if source_id and hasattr(self, 'parent') and self.parent():
                source_widget = self.parent().findChild(QWidget, source_id)
                if source_widget:
                    source_layout = source_widget.parent().layout()
                    target_layout = self.parent().layout()
                    if source_layout and target_layout:
                        source_index = source_layout.indexOf(source_widget)
                        target_index = target_layout.indexOf(self)
                        source_layout.removeWidget(source_widget)
                        target_layout.removeWidget(self)
                        source_layout.insertWidget(source_index, self)
                        target_layout.insertWidget(target_index, source_widget)
                        event.acceptProposedAction()