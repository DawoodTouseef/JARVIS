from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QHBoxLayout, QSizePolicy, QPushButton
from PyQt5.QtCore import Qt, QRegExp, QMimeData
from PyQt5.QtGui import QRegExpValidator, QDoubleValidator, QDrag
from typing import Optional, Callable, Dict
from jarvis_integration.themes.theme_manager import ThemeManager

class JarvisTextField(QWidget):
    VALID_TYPES = {"text", "password", "email", "number"}
    VALID_COLORS = {"primary", "secondary", "success", "error"}

    def __init__(self,
                 label: str = "",
                 placeholder: str = "",
                 validate_func: Optional[Callable] = None,
                 multiline: bool = False,
                 type: str = "text",
                 minRows: int = 1,
                 maxRows: int = 5,
                 rows: Optional[int] = None,
                 sx: Optional[Dict[str, str]] = None,
                 className: Optional[str] = None,
                 id: Optional[str] = None,
                 theme: str = "default",
                 icon: Optional[str] = None,
                 fullWidth: bool = False,
                 color: str = "primary",
                 defaultValue: str = ""):
        super().__init__()
        self.theme_manager = ThemeManager(theme)
        self.validate_func = validate_func
        self.multiline = multiline
        self.type = type.lower()
        self.minRows = minRows
        self.maxRows = maxRows
        self.rows = rows
        self.className = className
        self.id = id
        self.sx = sx or {}
        self.icon = icon if icon is not None else ("👁" if type == "password" else None)
        self.fullWidth = fullWidth
        self.color = color.lower()
        self.defaultValue = defaultValue
        self.is_password_visible = False

        if self.type not in self.VALID_TYPES:
            raise ValueError(f"Invalid type: {self.type}. Choose from {self.VALID_TYPES}")
        if self.color not in self.VALID_COLORS:
            raise ValueError(f"Invalid color: {self.color}. Choose from {self.VALID_COLORS}")
        if self.type in {"password", "email", "number"} and multiline:
            raise ValueError(f"Multiline is not supported for type '{self.type}'")

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

        self.input_widget = None
        self.icon_widget = None

        if self.icon:
            if self.type == "password":
                self.icon_widget = QPushButton(self.icon)
                self.icon_widget.setFixedWidth(24)
                self.icon_widget.clicked.connect(self.toggle_password)
            else:
                self.icon_widget = QLabel(self.icon)
                self.icon_widget.setFixedWidth(24)
                self.icon_widget.setStyleSheet("font-size: 16px; padding: 5px;")
            self.input_layout.addWidget(self.icon_widget)

        if multiline:
            self.input = QTextEdit()
            self.input_widget = self.input
            if rows:
                self.input.setFixedHeight(rows * 24)
            else:
                self.input.setMinimumHeight(minRows * 24)
                self.input.setMaximumHeight(maxRows * 24)
                self.input.textChanged.connect(self.adjust_height)
            self.input.setPlainText(defaultValue)
        else:
            self.input = QLineEdit()
            self.input_widget = self.input
            self.input.setPlaceholderText(placeholder)
            self.configure_input()
            self.input.setText(defaultValue)

        if self.fullWidth:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.setMaximumWidth(500)

        self.input_layout.addWidget(self.input_widget)
        self.layout.addLayout(self.input_layout)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        self.layout.addWidget(self.error_label)

        self.apply_styles()
        self.setAcceptDrops(True)

    def configure_input(self):
        if self.type == "password":
            self.input.setEchoMode(QLineEdit.Password)
        elif self.type == "email":
            email_regex = QRegExp(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
            validator = QRegExpValidator(email_regex, self.input)
            self.input.setValidator(validator)
        elif self.type == "number":
            validator = QDoubleValidator(self.input)
            self.input.setValidator(validator)
        self.input.textChanged.connect(self.validate)

    def toggle_password(self):
        if self.type != "password":
            return
        self.is_password_visible = not self.is_password_visible
        self.input.setEchoMode(QLineEdit.Normal if self.is_password_visible else QLineEdit.Password)
        self.icon_widget.setText("👁" if self.is_password_visible else self.icon)

    def validate(self):
        if not hasattr(self, 'error_label'):
            return

        if self.validate_func:
            result = self.validate_func(self.input.text())
            if result is not True:
                self.error_label.setText(result)
            else:
                self.error_label.setText("")
        elif self.type == "email":
            text = self.input.text()
            if text and ("@" not in text or "." not in text):
                self.error_label.setText("Invalid email address")
            else:
                self.error_label.setText("")

    def adjust_height(self):
        doc_height = self.input.document().size().height()
        new_height = min(max(doc_height * 1.5, self.minRows * 24), self.maxRows * 24)
        self.input.setFixedHeight(int(new_height))

    def text(self):
        return self.input.toPlainText() if self.multiline else self.input.text()

    def set_text(self, text):
        if self.multiline:
            self.input.setPlainText(text)
        else:
            self.input.setText(text)

    def apply_styles(self):
        highlight_color = self.theme_manager.get_color(self.color)
        style = f"""
            QLineEdit, QTextEdit {{
                border: 1px solid #ccc;
                padding: 6px;
                border-radius: 4px;
                font-size: 14px;
                background: #fff;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {highlight_color};
            }}
        """
        if self.className:
            class_style = self.theme_manager.get_class_styles(self.className)
            style += f"\nQLineEdit, QTextEdit {{ {class_style} }}"
        if self.id:
            id_style = self.theme_manager.get_id_styles(self.id)
            style += f"\nQLineEdit#{self.id}, QTextEdit#{self.id} {{ {id_style} }}"
        if self.sx:
            sx_style = "; ".join(f"{key}: {value}" for key, value in self.sx.items())
            style += f"\nQLineEdit, QTextEdit {{ {sx_style}; }}"
        if self.type == "password":
            style += "\nQLineEdit {{ border: 1px solid #f44336; }}"
        self.input_widget.setStyleSheet(style)

        if self.icon and self.icon_widget:
            if self.type == "password":
                icon_style = f"""
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
            else:
                icon_style = f"""
                    QLabel {{
                        color: {self.theme_manager.get_color('text')};
                        padding: 5px;
                        font-size: 14px;
                    }}
                """
            if self.className:
                icon_style += f"\nQLabel, QPushButton {{ {self.theme_manager.get_class_styles(self.className)} }}"
            if self.id:
                icon_style += f"\nQLabel#{self.id}-icon, QPushButton#{self.id}-icon {{ {self.theme_manager.get_id_styles(self.id)} }}"
            self.icon_widget.setStyleSheet(icon_style)
            if self.id:
                self.icon_widget.setObjectName(f"{self.id}-icon")

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.id:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.id)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
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