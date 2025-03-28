import os
import json
import yaml
import shutil
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QLineEdit, QFormLayout, QComboBox, QTabWidget, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QFont, QIcon
from config import SESSION_PATH, JARVIS_DIR
from langchain.tools import BaseTool
from typing import List, Optional, Type
from importlib import import_module

TOOLS: List[BaseTool] = []


def load_integrations():
    with open(os.path.join(JARVIS_DIR, "gui", "integrations.yml"), "r") as file:
        return yaml.safe_load(file)


def load_saved_settings():
    settings_path = os.path.join(SESSION_PATH, "integrations.json")
    if os.path.exists(settings_path):
        with open(settings_path, "r") as file:
            return json.load(file)
    return {}


def save_settings(saved_data):
    settings_path = os.path.join(SESSION_PATH, "integrations.json")
    with open(settings_path, "w") as file:
        json.dump(saved_data, file, indent=4)


def load_tool(integration_name: str) -> Optional[BaseTool]:
    integrations = load_integrations() or {}
    saved_data = load_saved_settings()

    if integration_name not in integrations or integration_name not in saved_data:
        return None

    tool_config = integrations[integration_name]["tool_config"]
    main_file = tool_config["main_file"]
    module_name = f"tools.{integration_name}.main"

    # Add tools directory to sys.path
    tools_dir = os.path.join(JARVIS_DIR, "tools")
    if tools_dir not in sys.path:
        sys.path.append(tools_dir)

    try:
        module = import_module(module_name)
        tool_class = getattr(module, f"{integration_name}Tool")
        tool_instance = tool_class(saved_data[integration_name])
        return tool_instance
    except (ImportError, AttributeError) as e:
        print(f"Error loading tool {integration_name}: {str(e)}")
        return None


class NewIntegrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Integration")
        self.setFixedSize(500, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter integration name...")
        layout.addWidget(QLabel("Integration Name:"))
        layout.addWidget(self.name_input)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Enter integration description...")
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.desc_input)

        self.dir_button = QPushButton("Select Directory")
        self.dir_button.clicked.connect(self.select_directory)
        self.dir_path = ""
        self.dir_label = QLabel("No directory selected")
        self.dir_label.setStyleSheet("color: gray;")
        layout.addWidget(QLabel("Directory:"))
        layout.addWidget(self.dir_button)
        layout.addWidget(self.dir_label)

        save_button = QPushButton("Add Integration")
        save_button.clicked.connect(self.save_integration)
        layout.addStretch()
        layout.addWidget(save_button)

        self.setLayout(layout)

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Integration Directory")
        if directory and self.validate_directory(directory):
            self.dir_path = directory
            self.dir_label.setText(os.path.basename(directory))
        else:
            self.dir_label.setText("Invalid directory structure")
            self.dir_path = ""

    def validate_directory(self, directory):
        required_files = ['main.py', 'integration.yml', 'requirements.txt']
        dir_path = Path(directory)
        for file in required_files:
            if not (dir_path / file).exists():
                QMessageBox.warning(self, "File Missing Error", f"Error: Missing required file {file}")
                return False
        return True

    def save_integration(self):
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()

        if not name or not self.dir_path:
            QMessageBox.warning(self, "Error", "Error: Integration name and directory are required")
            return

        integrations = load_integrations() or {}
        if name in integrations:
            QMessageBox.warning(self, "Integration warnings", "Error: Integration name already exists")
            return

        integration_yml_path = Path(self.dir_path) / 'integration.yml'
        with open(integration_yml_path, 'r') as f:
            integration_config = yaml.safe_load(f)

        if integration_config is None:
            QMessageBox.warning(self, "YAML Error", "yml file shouldn't be empty!")
            return

        integrations[name] = {
            "description": desc,
            "directory": self.dir_path,
            "forms": integration_config.get('forms', []),
            "tool_config": {
                "main_file": str(Path(self.dir_path) / 'main.py'),
                "requirements": str(Path(self.dir_path) / 'requirements.txt')
            }
        }

        with open(os.path.join(JARVIS_DIR, "gui", "integrations.yml"), "w") as file:
            yaml.safe_dump(integrations, file)

        tools_dir = os.path.join(JARVIS_DIR, "tools")
        os.makedirs(tools_dir, exist_ok=True)
        shutil.copytree(self.dir_path, os.path.join(tools_dir, name), dirs_exist_ok=True)

        QMessageBox.information(self, "Added successfully", f"Added new integration: {name}")
        self.accept()


class IntegrationItem(QWidget):
    def __init__(self, integration_name, integration_desc, parent=None):
        super().__init__(parent)
        self.integration_name = integration_name
        self.integration_desc = integration_desc
        self.connected = self.check_connection()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        name_label = QLabel(self.integration_name)
        name_label.setFont(QFont("Arial", 14))
        layout.addWidget(name_label)

        desc_label = QLabel(self.integration_desc)
        desc_label.setFont(QFont("Arial", 10))
        desc_label.setStyleSheet("color: gray;")
        layout.addWidget(desc_label)
        layout.addStretch()

        self.connect_button = QPushButton("Disconnect" if self.connected else "Connect")
        self.connect_button.setStyleSheet(
            "background-color: #03a9f4; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.connect_button.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(
            "background-color: #ff4444; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.delete_button.clicked.connect(self.delete_integration)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def check_connection(self):
        saved_data = load_saved_settings()
        return self.integration_name in saved_data

    def toggle_connection(self):
        if self.connected:
            self.disconnect_integration()
        else:
            self.open_connect_dialog()

    def open_connect_dialog(self):
        dialog = ConnectIntegrationDialog(self.integration_name, self)
        if dialog.exec_():
            self.connected = True
            self.connect_button.setText("Disconnect")
            tool = load_tool(self.integration_name)
            if tool:
                TOOLS.append(tool)
                print(TOOLS)
                print(f"Connected and loaded tool: {self.integration_name}")
            else:
                print(f"Failed to load tool: {self.integration_name}")

    def disconnect_integration(self):
        saved_data = load_saved_settings()
        if self.integration_name in saved_data:
            del saved_data[self.integration_name]
            save_settings(saved_data)
            self.connected = False
            self.connect_button.setText("Connect")
            # Remove tool from TOOLS list
            global TOOLS
            TOOLS = [tool for tool in TOOLS if tool.name != self.integration_name]
            print(f"Disconnected from {self.integration_name}")

    def delete_integration(self):
        if self.connected:
            self.disconnect_integration()

        integrations = load_integrations()
        if self.integration_name in integrations:
            del integrations[self.integration_name]
            with open(os.path.join(JARVIS_DIR, "gui", "integrations.yml"), "w") as file:
                yaml.safe_dump(integrations, file)

            tools_dir = os.path.join(JARVIS_DIR, "tools", self.integration_name)
            if os.path.exists(tools_dir):
                shutil.rmtree(tools_dir)

        self.setParent(None)
        self.deleteLater()
        print(f"Deleted integration {self.integration_name}")


class ConnectIntegrationDialog(QDialog):
    def __init__(self, integration_name, parent=None):
        super().__init__(parent)
        self.integration_name = integration_name
        self.setWindowTitle(f"Connect {integration_name}")
        self.setFixedSize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        integrations = load_integrations()
        integration_forms = integrations.get(self.integration_name, {}).get("forms", [])

        self.inputs = {}
        for form in integration_forms:
            tab = QWidget()
            form_layout = QFormLayout()
            fields = form.get("fields", [])
            self.inputs[form["title"]] = {}

            for field in fields:
                field_name = field.get("name")
                field_type = field.get("type", "text")

                if field_type == "text":
                    input_layout = QHBoxLayout()
                    input_widget = QLineEdit()
                    input_widget.setEchoMode(QLineEdit.Password)
                    input_widget.setPlaceholderText(f"Enter {field_name}...")
                    input_widget.setStyleSheet("padding: 5px; font-size: 14px;")

                    toggle_button = QPushButton()
                    toggle_button.setCheckable(True)
                    toggle_button.setIcon(QIcon(os.path.join(JARVIS_DIR, "icons", "eye-off.svg")))
                    toggle_button.setFixedSize(30, 30)
                    toggle_button.clicked.connect(
                        lambda _, txt=input_widget, btn=toggle_button: self.toggle_visibility(txt, btn))

                    input_layout.addWidget(input_widget)
                    input_layout.addWidget(toggle_button)
                    input_container = QWidget()
                    input_container.setLayout(input_layout)

                    self.inputs[form["title"]][field_name] = input_widget
                    form_layout.addRow(field_name, input_container)

                elif field_type == "combobox":
                    input_widget = QComboBox()
                    input_widget.addItems(field.get("options", []))
                    form_layout.addRow(field_name, input_widget)
                    self.inputs[form["title"]][field_name] = input_widget

                elif field_type == "file":
                    input_widget = QPushButton("Choose File")
                    input_widget.clicked.connect(lambda _, name=field_name: self.select_file(name))
                    self.inputs[form["title"]][field_name + "_path"] = ""
                    form_layout.addRow(field_name, input_widget)
                    self.inputs[form["title"]][field_name] = input_widget

                else:
                    input_widget = QLineEdit()
                    form_layout.addRow(field_name, input_widget)
                    self.inputs[form["title"]][field_name] = input_widget

            tab.setLayout(form_layout)
            self.tabs.addTab(tab, form["title"])

        layout.addWidget(self.tabs)
        save_button = QPushButton("Connect")
        save_button.clicked.connect(self.save_connection)
        layout.addWidget(save_button)
        self.setLayout(layout)

    def toggle_visibility(self, textbox, button):
        if textbox.echoMode() == QLineEdit.Password:
            textbox.setEchoMode(QLineEdit.Normal)
            button.setIcon(QIcon(os.path.join(JARVIS_DIR, "icons", "eye.svg")))
        else:
            textbox.setEchoMode(QLineEdit.Password)
            button.setIcon(QIcon(os.path.join(JARVIS_DIR, "icons", "eye-off.svg")))

    def select_file(self, field_name):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.inputs[self.tabs.tabText(self.tabs.currentIndex())][field_name + "_path"] = file_path

    def save_connection(self):
        config_data = {}
        for tab_name, fields in self.inputs.items():
            config_data[tab_name] = {field: input_widget.text().strip() if isinstance(input_widget,
                                                                                      QLineEdit) else input_widget.currentText() if isinstance(
                input_widget, QComboBox) else self.inputs[tab_name][field + "_path"] for field, input_widget in
                                     fields.items()}

        saved_data = load_saved_settings()
        saved_data[self.integration_name] = config_data
        save_settings(saved_data)
        print(f"Saved {self.integration_name} with settings: {config_data}")
        self.accept()


class IntegrationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Integrations")
        self.setFixedSize(800, 600)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        controls_layout = QHBoxLayout()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search integrations...")
        self.search_bar.textChanged.connect(self.filter_integrations)
        controls_layout.addWidget(self.search_bar)

        self.add_button = QPushButton("Add New")
        self.add_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.add_button.clicked.connect(self.add_new_integration)
        controls_layout.addWidget(self.add_button)

        main_layout.addLayout(controls_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.integrations_widget = QWidget()
        self.integrations_layout = QVBoxLayout(self.integrations_widget)
        self.scroll_area.setWidget(self.integrations_widget)
        main_layout.addWidget(self.scroll_area)

        self.populate_integrations()
        self.setLayout(main_layout)

    def populate_integrations(self):
        for i in range(self.integrations_layout.count() - 1, -1, -1):
            item = self.integrations_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            self.integrations_layout.removeItem(item)

        integrations = load_integrations() or {}
        for name, details in integrations.items():
            item = IntegrationItem(name, details.get("description", "No description"))
            self.integrations_layout.addWidget(item)
        self.integrations_layout.addStretch()

    def filter_integrations(self):
        filter_text = self.search_bar.text().lower()
        for i in range(self.integrations_layout.count() - 1):
            item = self.integrations_layout.itemAt(i)
            if item.widget():
                widget = item.widget()
                widget.setVisible(filter_text in widget.integration_name.lower())

    def add_new_integration(self):
        dialog = NewIntegrationDialog(self)
        if dialog.exec_():
            self.populate_integrations()


if __name__ == "__main__":
    app = QApplication([])
    dialog = IntegrationsDialog()
    dialog.show()
    app.exec_()