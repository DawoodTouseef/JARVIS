import uuid
from PyQt5.QtWidgets import (
     QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QCheckBox, QPushButton, QStackedWidget, QWidget,QMessageBox,QComboBox,QFileDialog,QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont,QIcon
import os
from config import SESSION_PATH, JARVIS_DIR,Model
import shutil
import json
from utils.models.users import Users
from gui.MemorySetting import MemorySettings
from utils.models.agents import Agent


class ClickableLabel(QLabel):
    """Custom QLabel to make it clickable."""
    clicked = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        """Emit clicked signal when label is clicked."""
        self.clicked.emit(self.text())
        super().mousePressEvent(event)


class AndroidSettingsDialog(QDialog):
    """A QDialog with multiple pages mimicking Android settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 400, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 16px;
                color: #333;
            }
            QCheckBox {
                font-size: 14px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search settings...")
        self.search_bar.textChanged.connect(self.filter_settings)
        search_layout.addWidget(self.search_bar)
        layout.addLayout(search_layout)

        # Scroll Area for the dynamic layout
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # Stacked Widget for Pages
        self.stacked_widget = QStackedWidget()
        self.main_page = self.create_main_page()
        self.detail_page = self.create_detail_page()
        self.llm_settings_page = QWidget()
        self.huggingface_settings_page = QWidget()
        self.llm_model_settings_page = QWidget()
        self.vision_model_settings_page = QWidget()
        self.connection_page = QWidget(self.scroll_area)
        self.connection_page.setStyleSheet("""
        *{
            border:none;
        }
        """)
        self.stacked_widget.addWidget(self.main_page)
        self.stacked_widget.addWidget(self.detail_page)
        self.stacked_widget.addWidget(self.llm_settings_page)
        self.stacked_widget.addWidget(self.connection_page)
        self.stacked_widget.addWidget(self.huggingface_settings_page)
        self.stacked_widget.addWidget(self.llm_model_settings_page)
        self.stacked_widget.addWidget(self.vision_model_settings_page)
        layout.addWidget(self.stacked_widget)

        self.setLayout(layout)

    def create_main_page(self):
        """Create the main settings page."""
        page = QWidget()
        self.main_layout = QVBoxLayout()

        # Sections with Toggles
        self.add_settings_section("General", ["Agent", "Memory","LLM Settings"])
        self.add_settings_section("Wake Word", ["Wake Word Settings"])
        self.add_settings_section("Integrations",['Integration'])
        self.add_settings_section("User", ["Logout"])

        # Message for "No Setting Available"
        self.no_setting_label = QLabel("No Setting Available")
        self.no_setting_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.no_setting_label.setStyleSheet("color: gray; margin-top: 20px;")
        self.no_setting_label.setAlignment(Qt.AlignCenter)
        self.no_setting_label.hide()

        self.main_layout.addWidget(self.no_setting_label)
        page.setLayout(self.main_layout)
        return page

    def create_detail_page(self):
        """Create a detail page for specific settings."""
        page = QWidget()
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Setting Details
        self.detail_label = QLabel("Setting Details")
        self.detail_label.setFont(QFont("Arial", 16))
        layout.addWidget(self.detail_label, alignment=Qt.AlignCenter)

        page.setLayout(layout)
        return page

    def add_settings_section(self, section_name, settings):
        """Add a section with settings to the main page."""
        self.main_layout.addWidget(self.create_section_label(section_name))
        for setting in settings:
            self.main_layout.addLayout(self.create_toggle_row(setting))

    def create_section_label(self, text):
        """Create a section label."""
        label = QLabel(text)
        label.setFont(QFont("Arial", 14, QFont.Bold))
        label.setStyleSheet("color: #555; margin-top: 10px;")
        return label

    def create_toggle_row(self, label_text):
        """Create a row with a label and a toggle switch."""
        row_layout = QHBoxLayout()

        # Clickable Label
        label = ClickableLabel(label_text)
        label.setFont(QFont("Arial", 12))
        label.clicked.connect(self.go_to_detail_page)
        row_layout.addWidget(label)

        # Toggle Switch (without page navigation)
        toggle = QCheckBox()
        toggle.setStyleSheet("""
            QCheckBox::indicator {
                width: 40px;
                height: 20px;
                border-radius: 10px;
                border: 1px solid #ccc;
                background-color: lightgray;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 1px solid #4CAF50;
            }
        """)
        row_layout.addWidget(toggle, alignment=Qt.AlignRight)

        return row_layout

    def clear_dynamic_widgets(self):
        """Remove all existing widgets and layouts in the config_button layout."""
        while self.config_button.count():
            item = self.config_button.takeAt(0)
            if item.widget():
                # If it's a widget, delete it
                item.widget().deleteLater()
            elif item.layout():
                # If it's a layout, recursively clear it
                self.clear_layout(item.layout())

    def clear_layout(self, layout):
        """Recursively clear all widgets and layouts from a given layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
        layout.deleteLater()

    def create_wakeword_page(self):
        """Create the wake word configuration page."""
        page = QWidget()
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)
        layout.addWidget(back_button, alignment=Qt.AlignLeft)
        with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
            data = json.load(f)
        if "email" in data:
            users = Users.get_user_by_email(data['email'])
            if users.settings is not None:
                wakeword_engine = json.loads(users.settings.json()).get('wakeword').get('wakeword_engine')
                engine_label = QLabel(f"Wake Word Engine Selected: {wakeword_engine}")
                layout.addWidget(engine_label)
        # Wake Word Engine Dropdown
        engine_layout = QHBoxLayout()
        engine_label = QLabel("Wake Word Engine:")
        self.wakeword_engine = QComboBox()
        self.wakeword_engine.addItems(["Select Engine","pvporcupine", "openwakeword"])
        engine_layout.addWidget(engine_label)
        engine_layout.addWidget(self.wakeword_engine,alignment=Qt.AlignCenter)
        self.wakeword_engine.currentIndexChanged.connect(self.wakeword_click_action)
        layout.addLayout(engine_layout)

        # Configure Button
        self.config_button = QVBoxLayout()
        layout.addLayout(self.config_button)

        page.setLayout(layout)
        return page
    def wakeword_click_action(self,index,row=None):
        self.clear_dynamic_widgets()
        layout = self.config_button
        if index==1:
            api_key = None
            with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
                data = json.load(f)
            if "email" in data:
                users = Users.get_user_by_email(data['email'])
                if users.settings is not None:
                    api_key = json.loads(users.settings.json()).get('wakeword').get('api_key')
            # API Key Input
            api_layout = QHBoxLayout()
            api_label = QLabel("API Key:")
            if api_key is None:
                self.api_input = QLineEdit()
            else:
                self.api_input = QLineEdit(api_key)
            self.api_input.setPlaceholderText("Enter pvporcupine API key")
            api_layout.addWidget(api_label)
            api_layout.addWidget(self.api_input)
            layout.addLayout(api_layout)

            # Model File Upload
            model_layout = QHBoxLayout()
            model_label = QLabel("Upload Model (Optional):")
            model_path = None
            with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
                data = json.load(f)
            if "email" in data:
                users = Users.get_user_by_email(data['email'])
                if users.settings is not None:
                    model_path = json.loads(users.settings.json()).get('wakeword').get('model_path')
            if model_path is not None:
                self.model_input = QLineEdit(model_path)
            else:
                self.model_input = QLineEdit()
            self.model_input.setPlaceholderText("No file selected")
            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(self.browse_model_file)
            model_layout.addWidget(model_label)
            model_layout.addWidget(self.model_input)
            model_layout.addWidget(browse_button)
            layout.addLayout(model_layout)

            # Save Button
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.save_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)
        elif index==2:
            # Model File Upload
            model_layout = QHBoxLayout()
            model_label = QLabel("Upload Model:")
            model_path = None
            with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
                data = json.load(f)
            if "email" in data:
                users = Users.get_user_by_email(data['email'])
                if users.settings is not None:
                    model_path = json.loads(users.settings.json()).get('wakeword').get('model_path')
            if model_path is not None:
                self.model_input = QLineEdit(model_path)
            else:
                self.model_input = QLineEdit()
            self.model_input.setPlaceholderText("No file selected")
            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(self.browse_model_file)
            model_layout.addWidget(model_label)
            model_layout.addWidget(self.model_input)
            model_layout.addWidget(browse_button)
            layout.addLayout(model_layout)

            # Save Button
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.save_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)

    def browse_model_file(self):
        """Open a file dialog to select a model file."""
        wakeword_engine = self.wakeword_engine.currentText()
        file_filter = "All Files (*)"  # Default filter

        # Set file filter based on the selected wake word engine
        if wakeword_engine == "pvporcupine":
            file_filter = "Porcupine Model Files (*.ppn)"
        elif wakeword_engine == "openwakeword":
            file_filter = "OpenWakeWord Model Files (*.tflite *.onnx)"

        # Open file dialog with the specific file filter
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Wake Word Model File", "", file_filter)

        if file_path:
            self.model_input.setText(file_path)


    def save_configuration(self):
            """Save the API key and optional model file."""
            wakeword_engine=self.wakeword_engine.currentText()

            if "pvporcupine" in wakeword_engine:
                api_key = self.api_input.text().strip()
                if not api_key and "pvporcupine" in wakeword_engine:
                    QMessageBox.warning(self, "Save Failed", "API Key is required!")
                    return
            model_file = self.model_input.text().strip()
            if not model_file and "openwakword"  in wakeword_engine:
                QMessageBox.warning(self, "Save Failed", "Model File is required!")
                return
            # Save model file to the target directory
            model_path = ""
            if model_file:
                MODEL_SAVE_PATH = os.path.join(SESSION_PATH, "wakeword")
                if not os.path.exists(MODEL_SAVE_PATH):
                    os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
                model_name = os.path.basename(model_file)
                model_path = os.path.join(MODEL_SAVE_PATH, model_name)
                shutil.copyfile(model_file, model_path)

            # Save configuration
            config = {"wakeword_engine": wakeword_engine}
            if wakeword_engine in [] and model_path is not None:
                config["model_path"]= model_path
            if "pvporcupine" in wakeword_engine:
                config["api_key"]=api_key
            with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
                data = json.load(f)
            if "email" in data:
                users = Users.get_user_by_email(data['email'])
                if users:
                    settings = {}
                    if users.settings:
                        settings.update(users.settings)
                    settings['wakeword']=config
                    Users.update_user_by_id(id=users.id, updated={"settings": settings})

            QMessageBox.information(self, "Saved", "Wake word configuration saved successfully!")

    def create_memory_page(self):
        """Create the memory configuration page."""
        page = QWidget()
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Clear Memory Button
        memory_button = QPushButton("Clear Memory")
        memory_button.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: black;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: darkred;
                color: white;
            }
        """)
        memory_button.clicked.connect(self.clear_memory_action)
        layout.addWidget(memory_button)

        # Memory Type Dropdown
        engine_layout = QHBoxLayout()
        engine_label = QLabel("Memory Type:")
        self.memory_engine_dropdown = QComboBox()
        self.memory_engine_dropdown.addItems(["Select Type", "Online", "Offline"])
        self.memory_engine_dropdown.currentIndexChanged.connect(self.memory_click_action)
        engine_layout.addWidget(engine_label)
        engine_layout.addWidget(self.memory_engine_dropdown)
        layout.addLayout(engine_layout)

        # Dynamic Configuration Layout
        self.config_button = QVBoxLayout()
        layout.addLayout(self.config_button)

        page.setLayout(layout)
        return page

    def memory_click_action(self, index):
        """Handle memory type selection and show relevant configuration options."""
        self.clear_dynamic_widgets()
        layout = self.config_button

        if index == 1:  # Online Memory
            api_key = ""
            try:
                with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
                    data = json.load(f)
                if "email" in data:
                    users = Users.get_user_by_email(data["email"])
                    if users and users.settings:
                        api_key = json.loads(users.settings.json()).get("memory", {}).get("api_key", "")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load API key: {e}")

            # API Key Input
            api_layout = QHBoxLayout()
            api_label = QLabel("API Key:")
            self.api_input = QLineEdit(api_key)
            self.api_input.setPlaceholderText("Enter Memo Client API Key")
            api_layout.addWidget(api_label)
            api_layout.addWidget(self.api_input)
            layout.addLayout(api_layout)

            # Save Button
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.memory_save_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)

    def memory_save_configuration(self):
        """Save the memory API key configuration."""
        api_key = self.api_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Save Failed", "API Key is required!")
            return

        try:
            # Save configuration to the database
            config = {"memo_engine": "online", "api_key": api_key}
            with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
                data = json.load(f)
            if "email" in data:
                users = Users.get_user_by_email(data["email"])
                if users:
                    settings = users.settings.json() if users.settings else {}
                    settings = json.loads(settings)
                    settings["memory"] = config
                    Users.update_user_by_id(id=users.id, updated={"settings": settings})

            QMessageBox.information(self, "Saved", "Memory configuration saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")

    def clear_memory_action(self):
        """Clear memory for the current user."""
        try:
            memory_settings = MemorySettings()
            memory_settings.clear_memory()
            QMessageBox.information(self, "Memory Cleared", "All memory data has been cleared successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear memory: {e}")

    def create_llm_settings_page(self):
        """Create the LLM Settings page."""
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.main_page))
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Add Connection Toggle
        connection_row = self.create_toggle_row("Connection")
        connection_row.itemAt(0).widget().clicked.connect(lambda: self.go_to_detail_page("Connection"))
        layout.addLayout(connection_row)

        # Add HuggingFace Toggle
        connection_row = self.create_toggle_row("HuggingFace")
        connection_row.itemAt(0).widget().clicked.connect(lambda: self.go_to_detail_page("HuggingFace"))
        layout.addLayout(connection_row)

        # Add Model Toggle
        connection_row = self.create_toggle_row("LLM")
        connection_row.itemAt(0).widget().clicked.connect(lambda: self.go_to_detail_page("LLM"))
        layout.addLayout(connection_row)

        # Add Model Toggle
        connection_row = self.create_toggle_row("Vision")
        connection_row.itemAt(0).widget().clicked.connect(lambda: self.go_to_detail_page("Vision"))
        layout.addLayout(connection_row)

        self.llm_settings_page.setLayout(layout)

    def get_model(self,models:list):
        """
        :return:
        """
        session_json = os.path.join(SESSION_PATH, "session.json")
        if os.path.exists(os.path.join(SESSION_PATH, "session.json")):
            with open(session_json, "r") as f:
                data = json.load(f)
            if "email" in data:
                users = Users.get_user_by_email(data.get("email"))
                if users:
                    if users.settings:
                        settings = json.loads(users.settings.json())
                        if "openai" in settings:
                            openai = settings['openai']
                            for i in openai:
                                model=self.get_all_models_raw(i["base_url"],i["api_key"])['data']
                                for j in model:
                                    models.append(Model(**{
                                            "name":j.get('name',j['id']),
                                            "type":"openai",
                                            "url":i['base_url'],
                                            "api_key":i["api_key"]
                                            }
                                        )
                                    )

    def create_llm_model_page(self):
        """
        Create the LLM settings page with improved UI and search functionality.
        """
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.setStyleSheet("background-color: #f44336; color: white; padding: 10px; border-radius: 5px;")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.llm_settings_page))
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Model Selection
        model_label = QLabel("Select LLM:")
        model_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(model_label)

        # Searchable dropdown
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search models...")
        search_box.setStyleSheet("padding: 8px; font-size: 14px; border-radius: 5px;")
        layout.addWidget(search_box)

        model_dropdown = QComboBox()
        model_dropdown.setEditable(True)
        model_dropdown.setStyleSheet("padding: 8px; font-size: 14px; border-radius: 5px;")
        model_dropdown.setInsertPolicy(QComboBox.NoInsert)

        models = []
        models_list = []
        self.get_model(models)

        if models:
            for model in models:
                models_list.append(model.name)
            model_dropdown.addItems(models_list)
        else:
            model_dropdown.addItem("No models found")

        layout.addWidget(model_dropdown)

        # Filter function for search box
        def filter_models():
            filter_text = search_box.text().lower()
            model_dropdown.clear()
            filtered_models = [m for m in models_list if filter_text in m.lower()]
            if filtered_models:
                model_dropdown.addItems(filtered_models)
            else:
                model_dropdown.addItem("No matching models")

        search_box.textChanged.connect(filter_models)

        # Save Button
        save_button = QPushButton("Save Model")
        save_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px;")
        save_button.clicked.connect(lambda: self.save_model_selection( model_dropdown.currentText()))
        layout.addWidget(save_button)

        self.llm_model_settings_page.setLayout(layout)

    def save_model_selection(self, model_name):
        """
        Save selected model information to a JSON file.
        """
        try:
            session_file = os.path.join(SESSION_PATH, "session.json")
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}
            if "email" in data:
                users = Users.get_user_by_email(data["email"])
                if users:
                    if users.settings is None:
                        users.settings = {}

                    if not isinstance(users.settings.json(), dict):
                        users.settings = json.loads(users.settings.json())
                    models = []
                    self.get_model(models)
                    urls_api_key = {}
                    for m in models:
                        if model_name in m.name:
                            urls_api_key.update(
                                {"url": m.url, "name": model_name, "type": "openai", "api_key": m.api_key}
                            )
                    users.settings["model"] = urls_api_key
                    Users.update_user_by_id(id=users.id, updated={"settings": users.settings})
                    QMessageBox.information(self, "LLM", f"Model Selected successfully!")
        except Exception as e:
            QMessageBox.critical(self,"LLM",f"Error saving model selection: {e}")

    def create_vision_model_page(self):
        """
        Create the LLM settings page with improved UI and search functionality.
        """
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.setStyleSheet("background-color: #f44336; color: white; padding: 10px; border-radius: 5px;")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.llm_settings_page))
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Model Selection
        model_label = QLabel("Select Vision Model:")
        model_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(model_label)

        # Searchable dropdown
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search models...")
        search_box.setStyleSheet("padding: 8px; font-size: 14px; border-radius: 5px;")
        layout.addWidget(search_box)

        model_dropdown = QComboBox()
        model_dropdown.setEditable(True)
        model_dropdown.setStyleSheet("padding: 8px; font-size: 14px; border-radius: 5px;")
        model_dropdown.setInsertPolicy(QComboBox.NoInsert)

        models = []
        models_list = []
        self.get_model(models)

        if models:
            for model in models:
                models_list.append(model.name)
            model_dropdown.addItems(models_list)
        else:
            model_dropdown.addItem("No models found")

        layout.addWidget(model_dropdown)

        # Filter function for search box
        def filter_models():
            filter_text = search_box.text().lower()
            model_dropdown.clear()
            filtered_models = [m for m in models_list if filter_text in m.lower()]
            if filtered_models:
                model_dropdown.addItems(filtered_models)
            else:
                model_dropdown.addItem("No matching models")

        search_box.textChanged.connect(filter_models)

        # Save Button
        save_button = QPushButton("Save Model")
        save_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px;")
        save_button.clicked.connect(lambda: self.save_vision_model_selection(model_dropdown.currentText()))
        layout.addWidget(save_button)

        self.vision_model_settings_page.setLayout(layout)

    def save_vision_model_selection(self, model_name):
        """
        Save selected model information to a JSON file.
        """
        try:
            session_file = os.path.join(SESSION_PATH, "session.json")
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}
            if "email" in data:
                users = Users.get_user_by_email(data["email"])
                if users:
                    if users.settings is None:
                        users.settings = {}

                    if not isinstance(users.settings.json(), dict):
                        users.settings = json.loads(users.settings.json())
                    models = []
                    self.get_model(models)
                    urls_api_key = {}
                    for m in models:
                        if model_name in m.name:
                            urls_api_key.update(
                                {"url": m.url, "name": model_name, "type": "openai", "api_key": m.api_key}
                            )
                    users.settings["vision"] = urls_api_key
                    Users.update_user_by_id(id=users.id, updated={"settings": users.settings})
                    QMessageBox.information(self, "Vision LLM", f"Model Selected successfully!")
        except Exception as e:
            QMessageBox.critical(self,"Vision LLM",f"Error saving model selection: {e}")
    def create_huggingface_page(self):
        """
        Create the Hugging Face settings page.
        """
        # Initialize the page widget if not already done
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.llm_settings_page))
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # API Key Input
        api_key_label = QLabel("HuggingFace API Key:")
        layout.addWidget(api_key_label)
        api_key=""
        try:
            session_file = os.path.join(SESSION_PATH, "session.json")
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}
            if "email" in data:
                users = Users.get_user_by_email(data["email"])
                if users:
                    if users.settings is None:
                        users.settings = {}

                    if not isinstance(users.settings.json(), dict):
                        users.settings = json.loads(users.settings.json())
                    api_key=users.settings["huggingface_token"]
        except Exception as e:
            pass
        hf_api_key_input = QLineEdit(api_key)
        hf_api_key_input.setPlaceholderText("Enter HuggingFace API Key")
        hf_api_key_input.setEchoMode(QLineEdit.Password)  # Hide API Key by default
        layout.addWidget(hf_api_key_input)

        # Show/Hide API Key toggle
        toggle_visibility = QCheckBox("Show Key")
        toggle_visibility.stateChanged.connect(
            lambda state, textbox=hf_api_key_input: textbox.setEchoMode(
                QLineEdit.Normal if state == Qt.Checked else QLineEdit.Password
            )
        )
        layout.addWidget(toggle_visibility)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda :self.save_huggingface_api_key(hf_api_key_input.text()))
        layout.addWidget(save_button, alignment=Qt.AlignCenter)

        # Set layout for the Hugging Face settings page
        self.huggingface_settings_page.setLayout(layout)

    def save_huggingface_api_key(self,api_key):
        """
        Save the Hugging Face API key securely.
        """
        if not api_key:
            QMessageBox.warning(self, "Error", "API Key cannot be empty!")
            return

        try:
            session_file = os.path.join(SESSION_PATH, "session.json")
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}
            if "email" in data:
                users = Users.get_user_by_email(data["email"])
                if users:
                    if users.settings is None:
                        users.settings = {}

                    if not isinstance(users.settings.json(), dict):
                        users.settings = json.loads(users.settings.json())
                    users.settings["huggingface_token"] = api_key
                    Users.update_user_by_id(id=users.id, updated={"settings": users.settings})
                    QMessageBox.information(self, "HuggingFace", f"API Key saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save API Key: {e}")

    def fetch_url(self,url, key):
        import requests
        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }

            response = requests.get(url, headers=headers)
            if response.status_code!=200:
                QMessageBox.warning(self, "Connection Error", f"Connection error: {response.reason}")
                return
            return response.json()
        except Exception as e:
            # Handle connection error here
            QMessageBox.warning(self,"Connection Error",f"Connection error: {e}")
            return None

    def get_all_models_raw(self,base_url_input, api_key_input):
        tasks = self.fetch_url(f"{base_url_input}/models", api_key_input)
        return tasks

    def create_connection_page(self):
        """Create the Connection settings page."""
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.llm_settings_page))
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Scroll Area for Dynamic Layout
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # Dynamic Layout for Base URL and API Key
        self.dynamic_connection_widget = QWidget()
        self.dynamic_connection_layout = QVBoxLayout(self.dynamic_connection_widget)
        self.dynamic_connection_layout.setSpacing(5)
        self.dynamic_connection_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.dynamic_connection_widget)

        # Load initial data from the database
        self.load_initial_data()

        # Add Scroll Area to Main Layout
        layout.addWidget(self.scroll_area)

        # Add Plus Button
        plus_button = QPushButton()
        plus_button.clicked.connect(lambda : self.add_connections_form())
        plus_button.setIcon(QIcon(os.path.join(JARVIS_DIR,"icons","plus.svg")))
        layout.addWidget(plus_button)

        # Set layout for the connection page
        self.connection_page.setLayout(layout)

    def load_initial_data(self):
        """Load initial Base URL and API Key pairs from the database."""
        try:
            session_file = os.path.join(SESSION_PATH, "session.json")
            with open(session_file, "r") as f:
                data = json.load(f)
            connections = []
            if "email" in data:
                users = Users.get_user_by_email(data["email"])
                if users and users.settings:
                    connections = json.loads(users.settings.json()).get("openai", [])

            if connections:
                for connection in connections:
                    self.add_connection_fields(connection.get("base_url"), connection.get("api_key"))

        except Exception as e:
            print(f"Failed to load initial data: {e}")

    def add_connections_form(self):
        """Show the form to add a new core."""
        form_dialog = QDialog(self)
        form_dialog.setWindowTitle("Add New Connections")
        form_layout = QVBoxLayout()

        # Base Url
        name_label = QLabel("Base Url:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter Base url:")
        form_layout.addWidget(name_label)
        form_layout.addWidget(name_input)

        # API Key
        description_label = QLabel("API Key:")
        description_input = QLineEdit()
        description_input.setPlaceholderText("Enter API Key")
        form_layout.addWidget(description_label)
        form_layout.addWidget(description_input)

        # Toggle Visibility Button (Eye Icon)
        eye_svg = os.path.join(JARVIS_DIR, "icons", "eye-off.svg")
        eye_off_svg = os.path.join(JARVIS_DIR, "icons", "eye.svg")

        toggle_visibility_button = QPushButton()
        toggle_visibility_button.setFixedSize(30, 30)

        def toggle_password_visibility():
            """Toggle API Key visibility and update icon."""
            if description_input.echoMode() == QLineEdit.Password:
                description_input.setEchoMode(QLineEdit.Normal)
                toggle_visibility_button.setIcon(QIcon(eye_off_svg))
            else:
                description_input.setEchoMode(QLineEdit.Password)
                toggle_visibility_button.setIcon(QIcon(eye_svg))

        toggle_visibility_button.setIcon(QIcon(eye_svg))
        toggle_visibility_button.clicked.connect(toggle_password_visibility)
        form_layout.addWidget(toggle_visibility_button)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(
            lambda: self.save_all_connections(api_key_in2=description_input.text(),base_url_in2=name_input.text())
        )
        form_layout.addWidget(save_button, alignment=Qt.AlignCenter)

        form_dialog.setLayout(form_layout)
        form_dialog.exec_()

    def add_connection_fields(self,  base_url: str = None, api_key: str = None):
        """Add a new pair of Base URL and API Key textboxes to the GUI."""
        connection_layout = QHBoxLayout()

        # Base URL Input
        base_url_input = QLabel(base_url)
        connection_layout.addWidget(base_url_input)

        # API Key Input
        api_key_input = QLineEdit(api_key)
        api_key_input.setEchoMode(QLineEdit.Password)
        connection_layout.addWidget(api_key_input)

        # Toggle Visibility Button (Eye Icon)
        eye_svg = os.path.join(JARVIS_DIR, "icons", "eye-off.svg")
        eye_off_svg = os.path.join(JARVIS_DIR, "icons", "eye.svg")

        toggle_visibility_button = QPushButton()
        toggle_visibility_button.setFixedSize(30, 30)

        def toggle_password_visibility():
            """Toggle API Key visibility and update icon."""
            if api_key_input.echoMode() == QLineEdit.Password:
                api_key_input.setEchoMode(QLineEdit.Normal)
                toggle_visibility_button.setIcon(QIcon(eye_off_svg))
            else:
                api_key_input.setEchoMode(QLineEdit.Password)
                toggle_visibility_button.setIcon(QIcon(eye_svg))

        toggle_visibility_button.setIcon(QIcon(eye_svg))
        toggle_visibility_button.clicked.connect(toggle_password_visibility)
        connection_layout.addWidget(toggle_visibility_button)

        # Remove Button (Minus Icon)
        minus_svg = os.path.join(JARVIS_DIR, "icons", "minus.svg")
        remove_button = QPushButton()
        remove_button.setIcon(QIcon(minus_svg))
        remove_button.setFixedSize(30, 30)
        remove_button.clicked.connect(lambda: self.remove_connection_fields(connection_layout,base_url_input,api_key_input))
        connection_layout.addWidget(remove_button)

        # Refresh Button (Repeat Icon)
        refresh_svg = os.path.join(JARVIS_DIR, "icons", "repeat.svg")
        refresh_button = QPushButton()
        refresh_button.setIcon(QIcon(refresh_svg))
        refresh_button.setFixedSize(30, 30)
        refresh_button.clicked.connect(lambda: self.get_all_models_raw(base_url_input, api_key_input))
        connection_layout.addWidget(refresh_button)

        # Add the layout to the dynamic layout
        self.dynamic_connection_layout.addLayout(connection_layout)


    def remove_connection_fields(self, connection_layout, base_url_input, api_key_input):
        """
        Remove a specific pair of Base URL and API Key.
        """
        base_url = base_url_input.text().strip()
        api_key = api_key_input.text().strip()

        # Check if the inputs are valid before proceeding
        if not base_url or not api_key:
            QMessageBox.warning(self, "Error", "Base URL or API Key is missing!")
            return

        try:
            # Read the session file
            session_file = os.path.join(SESSION_PATH, "session.json")
            with open(session_file, "r") as f:
                data = json.load(f)

            # Update the database/settings if "email" exists
            if "email" in data:
                users = Users.get_user_by_email(data["email"])
                if users:
                    settings = json.loads(users.settings.json())
                    if "openai" in settings:
                        # Remove the connection from settings
                        updated_connections = [
                            conn for conn in settings["openai"]
                            if conn["base_url"] != base_url or conn["api_key"] != api_key
                        ]
                        settings["openai"] = updated_connections
                        # Save the updated settings back to the database
                        Users.update_user_by_id(
                            id=users.id,
                            updated={"settings": settings}
                        )
                        QMessageBox.information(
                            self,
                            "Success",
                            f"Connection for {base_url} removed successfully!"
                        )
                    else:
                        QMessageBox.warning(self, "Error", "No connections found to remove.")

            # Remove the row from the GUI
            while connection_layout.count():
                widget = connection_layout.takeAt(0).widget()
                if widget:
                    widget.deleteLater()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"An error occurred while removing the connection: {e}"
            )

    def save_all_connections(self,base_url_in2:str=None,api_key_in2:str=None):
        """Save all Base URL and API Key pairs to the database."""
        connections = []
        session_file = os.path.join(SESSION_PATH, "session.json")
        if os.path.exists(session_file):
            with open(session_file, "r") as f:
                data = json.load(f)
        else:
            data = {}
        if "email" in data:
            users = Users.get_user_by_email(data["email"])
            if users:
                if users.settings is None:
                    users.settings = {}
                try:
                    if not isinstance(users.settings.json(), dict):
                        users.settings = json.loads(users.settings.json())
                except AttributeError as e:
                    pass
                connections=[]
                if "openai" in users.settings:
                    connections=users.settings["openai"]

        if base_url_in2 and api_key_in2:
            connections.append({"base_url": base_url_in2, "api_key": api_key_in2})
        # If no connections were found, warn the user
        if base_url_in2 is None or api_key_in2 is None or not connections:
            QMessageBox.warning(self.connection_page, "Warning", "No connections found to save!")
            return

        try:
            session_file = os.path.join(SESSION_PATH, "session.json")
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}
            if "email" in data:
                users = Users.get_user_by_email(data["email"])
                if users:
                    if users.settings is None:
                        users.settings = {}
                    try:
                        if not isinstance(users.settings.json(), dict):
                            users.settings = json.loads(users.settings.json())
                    except Exception as e:
                        pass
                    users.settings["openai"] = connections
                    Users.update_user_by_id(id=users.id, updated={"settings": users.settings})

            QMessageBox.information(self.connection_page, "Success", "All connections saved successfully!")

        except Exception as e:
            QMessageBox.critical(self.connection_page, "Error", f"Failed to save connections: {e}")

    def create_agents_page(self):
        """Create the Agents settings page."""
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.main_page))
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Scroll Area for Dynamic Layout
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # Dynamic Layout for Agents List
        self.agents_widget = QWidget()
        self.agents_layout = QVBoxLayout(self.agents_widget)
        self.agents_layout.setSpacing(10)  # Space between rows
        self.agents_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.agents_widget)
        layout.addWidget(self.scroll_area)

        # Add Plus Button
        add_button = QPushButton("+ Add Agent")
        add_button.clicked.connect(self.add_agent_form)
        layout.addWidget(add_button, alignment=Qt.AlignCenter)

        # Set layout for the core page
        self.agents_page = QWidget()
        self.agents_page.setLayout(layout)
        self.stacked_widget.addWidget(self.agents_page)
        self.stacked_widget.setCurrentWidget(self.agents_page)

        # Load existing core
        self.load_agents()

    def load_agents(self):
        """Load core from the database."""
        # Simulated database query

        agents = Agent.get_agents()
        for agent in agents:
            self.add_agent_row(editable=True,id=agent.id,name=agent.name,description=agent.description)

    def add_agent_row(self, name, description, editable=False,id:str=None):
        """Add a row displaying an core."""
        row_layout = QHBoxLayout()

        # Agent Name
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        row_layout.addWidget(name_label)

        # Agent Description
        description_label = QLabel(description)
        description_label.setStyleSheet("font-size: 12px; color: gray;")
        row_layout.addWidget(description_label)

        # Edit Button
        if editable:
            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(lambda: self.edit_agent(id=id))
            row_layout.addWidget(edit_button)

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda: self.delete_agent(id=id))
            row_layout.addWidget(delete_button)

        # Add the row layout to the core layout
        self.agents_layout.addLayout(row_layout)

    def add_agent_form(self):
        """Show the form to add a new core."""
        form_dialog = QDialog(self)
        form_dialog.setWindowTitle("Add New Agent")
        form_layout = QVBoxLayout()

        # Agent Name
        name_label = QLabel("Agent Name:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter core name")
        form_layout.addWidget(name_label)
        form_layout.addWidget(name_input)

        # Agent Description
        description_label = QLabel("Description:")
        description_input = QLineEdit()
        description_input.setPlaceholderText("Enter core description")
        form_layout.addWidget(description_label)
        form_layout.addWidget(description_input)

        # File Upload
        file_label = QLabel("Upload File:")
        file_input = QLineEdit()
        file_input.setPlaceholderText("No file selected")
        file_button = QPushButton("Browse")
        file_button.clicked.connect(lambda: self.browse_file(file_input))
        file_layout = QHBoxLayout()
        file_layout.addWidget(file_label)
        file_layout.addWidget(file_input)
        file_layout.addWidget(file_button)
        form_layout.addLayout(file_layout)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(
            lambda: self.save_agent(name_input.text(), description_input.text(), file_input.text(), form_dialog)
        )
        form_layout.addWidget(save_button, alignment=Qt.AlignCenter)

        form_dialog.setLayout(form_layout)
        form_dialog.exec_()

    def browse_file(self, file_input):
        """Open a file dialog to select a file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Autogen Agent  Files (*.json)")
        if file_path:
            file_input.setText(file_path)

    def save_agent(self, name, description, file_path, dialog):
        """Save the new core to the database."""
        if not name or not description or not file_path:
            QMessageBox.warning(self, "Error", "All fields are required!")
            return

        id=str(uuid.uuid4())
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            # Save to the database
            file_name=os.path.basename(file_path)
            if not os.path.exists(os.path.join(JARVIS_DIR,"data","core")):
                os.makedirs(os.path.join(JARVIS_DIR,"data","core"),exist_ok=True)
            shutil.copyfile(file_path,os.path.join(JARVIS_DIR,"data","core",file_name))
            datas={
                "file_name":file_name,
                "data":data
            }
            Agent.insert_new_agent(id=id,name=name,description=description,file=datas)  # Replace with actual database save logic
            self.add_agent_row(name, description, editable=True,id=id)
            dialog.accept()
            QMessageBox.information(self, "Saved", f"Agent '{name}' has been saved successfully!")
        except Exception as e:
            QMessageBox.warning(self,"Error","Error in it")

    def delete_agent(self,id):
        agents=Agent.get_agent_by_id(id)
        agent_path=os.path.join(JARVIS_DIR,"data","core",agents.file.get("file_name"))
        Agent.delete_agent_by_id(id)
        if os.path.exists(agent_path):
            os.remove(agent_path)
        QMessageBox.information(self,"Delete Agent",'Deleted  Successfully!')
        self.refresh_agents_list()

    def edit_agent(self, id):
        """Edit an existing core."""
        # Fetch the core details by ID
        agent = Agent.get_agent_by_id(id)
        if not agent:
            QMessageBox.critical(self, "Error", "Agent not found!")
            return

        # Create the dialog
        form_dialog = QDialog(self)
        form_dialog.setWindowTitle("Edit Agent")
        form_layout = QVBoxLayout()

        # Agent Name
        name_label = QLabel("Agent Name:")
        name_input = QLineEdit(agent.name)  # Populate with current name
        name_input.setPlaceholderText("Enter core name")
        form_layout.addWidget(name_label)
        form_layout.addWidget(name_input)

        # Agent Description
        description_label = QLabel("Description:")
        description_input = QLineEdit(agent.description)  # Populate with current description
        description_input.setPlaceholderText("Enter core description")
        form_layout.addWidget(description_label)
        form_layout.addWidget(description_input)

        # File Upload
        file_label = QLabel("Upload File:")
        file_input = QLineEdit(agent.file.get("file_name"))
        file_input.setPlaceholderText("No file selected")
        file_button = QPushButton("Browse")
        file_button.clicked.connect(lambda: self.browse_file(file_input))
        file_layout = QHBoxLayout()
        file_layout.addWidget(file_label)
        file_layout.addWidget(file_input)
        file_layout.addWidget(file_button)
        form_layout.addLayout(file_layout)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(
            lambda: self.save_edited_agent(
                id=id,
                name=name_input.text(),
                description=description_input.text(),
                file=file_input.text(),
                dialog=form_dialog
            )
        )
        form_layout.addWidget(save_button, alignment=Qt.AlignCenter)

        # Set layout and show dialog
        form_dialog.setLayout(form_layout)
        form_dialog.exec_()

    def save_edited_agent(self, id, name, description, file, dialog):
        """Save the edited core to the database."""
        if not name or not description or not file:
            QMessageBox.warning(self, "Error", "All fields are required!")
            return

        # Update the core in the database
        success = Agent.update_agent_by_id(
            id=id,
            updated={
                "name": name,
                "description": description,
                "file": file
            }
        )

        if success:
            QMessageBox.information(self, "Success", f"Agent '{name}' has been updated successfully!")
            dialog.accept()
            self.refresh_agents_list()  # Refresh the core list in the GUI
        else:
            QMessageBox.critical(self, "Error", "Failed to update the core!")

    def refresh_agents_list(self):
        """Refresh the list of core in the GUI."""
        for i in reversed(range(self.agents_layout.count())):
            item = self.agents_layout.takeAt(i)
            if item.widget():
                item.widget().deleteLater()

        self.load_agents()

    def go_to_detail_page(self, setting_name):
        """Navigate to the detail page for a specific setting."""
        if "Logout" in setting_name:
            confirmation = QMessageBox.question(
                self,
                "Logout Confirmation",
                "Are you sure you want to log out?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if confirmation == QMessageBox.Yes:
                session_file = os.path.join(SESSION_PATH, "session.json")
                if os.path.exists(session_file):
                    os.remove(session_file)

                QMessageBox.information(self, "Logged Out", "You have been logged out successfully.")
                self.close()  # Closes the settings dialog
        elif "Wake Word Settings" in setting_name:
            wakeword_page = self.create_wakeword_page()
            self.stacked_widget.addWidget(wakeword_page)
            self.stacked_widget.setCurrentWidget(wakeword_page)
        elif "Memory" in setting_name:
            memory_page = self.create_memory_page()
            self.stacked_widget.addWidget(memory_page)
            self.stacked_widget.setCurrentWidget(memory_page)
        elif setting_name == "LLM Settings":
            self.create_llm_settings_page()
            self.stacked_widget.setCurrentWidget(self.llm_settings_page)
        elif setting_name == "Connection":
            self.create_connection_page()
            self.stacked_widget.setCurrentWidget(self.connection_page)
        elif setting_name == "Agent":
            self.create_agents_page()
        elif setting_name=="HuggingFace":
            self.create_huggingface_page()
            self.stacked_widget.setCurrentWidget(self.huggingface_settings_page)
        elif "LLM" == setting_name:
            self.create_llm_model_page()
            self.stacked_widget.setCurrentWidget(self.llm_model_settings_page)
        elif "Vision" == setting_name:
            self.create_vision_model_page()
            self.stacked_widget.setCurrentWidget(self.vision_model_settings_page)

    def go_back(self):
        """Navigate back to the main page."""
        self.stacked_widget.setCurrentWidget(self.main_page)

    def filter_settings(self, text):
        """Filter settings based on search input."""
        visible_count = 0
        for i in range(self.main_layout.count() - 1):  # Exclude the "No Setting Available" label
            item = self.main_layout.itemAt(i)
            if isinstance(item, QHBoxLayout):  # Check if it's a toggle row
                label = item.itemAt(0).widget()
                if isinstance(label, ClickableLabel):
                    is_match = text.lower() in label.text().lower()
                    label.setVisible(is_match)
                    item.itemAt(1).widget().setVisible(is_match)  # Toggle visibility
                    visible_count += is_match
            elif isinstance(item, QLabel):  # Check if it's a section label
                is_match = text.lower() in item.text().lower()
                item.widget().setVisible(is_match)
                visible_count += is_match
        # Show or hide "No Setting Available" message
        self.no_setting_label.setVisible(visible_count == 0)