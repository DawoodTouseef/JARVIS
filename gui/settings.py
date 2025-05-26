
import uuid
import logging
import os
import json
import shutil
import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton,
    QStackedWidget, QWidget, QMessageBox, QComboBox, QFileDialog, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from config import SESSION_PATH, JARVIS_DIR, Model
from jarvis_integration.models.users import Users
from jarvis_integration.models.preferences import Preferences
from core.memory.memory_agent import MemorySettings
from jarvis_integration.models.agents import Agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
        """Initialize the UI components."""
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
        self.connection_page = QWidget()
        self.connection_page.setStyleSheet("border: none;")
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
        self.add_settings_section("General", ["Agent", "Memory", "LLM Settings"])
        self.add_settings_section("Wake Word", ["Wake Word Settings"])
        self.add_settings_section("Integrations", ["NextCloud","Web Search"])
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

        # Toggle Switch
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
                item.widget().deleteLater()
            elif item.layout():
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

        # Load user and preferences
        user_id = self.get_current_user_id()
        if not user_id:
            engine_label = QLabel("Error: No user logged in")
            layout.addWidget(engine_label)
            page.setLayout(layout)
            return page

        # Fetch wake word settings from preferences
        wakeword_prefs = Preferences.get_preferences_by_user_id(user_id)
        wakeword_config = next((pref.setting_value for pref in wakeword_prefs if pref.setting_key == "wakeword"), {})

        # Wake Word Engine Dropdown
        engine_layout = QHBoxLayout()
        engine_label = QLabel(f"Wake Word Engine Selected: {wakeword_config.get('wakeword_engine', 'None')}")
        self.wakeword_engine = QComboBox()
        self.wakeword_engine.addItems(["Select Engine", "pvporcupine", "openwakeword"])
        self.wakeword_engine.setCurrentText(wakeword_config.get("wakeword_engine", "Select Engine"))
        engine_layout.addWidget(engine_label)
        engine_layout.addWidget(self.wakeword_engine, alignment=Qt.AlignCenter)
        self.wakeword_engine.currentIndexChanged.connect(self.wakeword_click_action)
        layout.addLayout(engine_layout)

        # Configure Button
        self.config_button = QVBoxLayout()
        layout.addLayout(self.config_button)

        # Preload settings if available
        if wakeword_config:
            self.wakeword_click_action(self.wakeword_engine.currentIndex())

        page.setLayout(layout)
        return page

    def wakeword_click_action(self, index, row=None):
        """Handle wake word engine selection."""
        self.clear_dynamic_widgets()
        layout = self.config_button

        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        # Load existing wake word settings
        wakeword_prefs = Preferences.get_preferences_by_user_id(user_id)
        wakeword_config = next((pref.setting_value for pref in wakeword_prefs if pref.setting_key == "wakeword"), {})

        if index == 1:  # pvporcupine
            # API Key Input
            api_layout = QHBoxLayout()
            api_label = QLabel("API Key:")
            self.api_input = QLineEdit(wakeword_config.get("api_key", ""))
            self.api_input.setPlaceholderText("Enter pvporcupine API key")
            api_layout.addWidget(api_label)
            api_layout.addWidget(self.api_input)
            layout.addLayout(api_layout)

            # Model File Upload
            model_layout = QHBoxLayout()
            model_label = QLabel("Upload Model (Optional):")
            self.model_input = QLineEdit(wakeword_config.get("model_path", ""))
            self.model_input.setPlaceholderText("No file selected")
            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(self.browse_model_file)
            model_layout.addWidget(model_label)
            model_layout.addWidget(self.model_input)
            model_layout.addWidget(browse_button)
            layout.addLayout(model_layout)

            # Save Button
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.save_wakeword_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)

        elif index == 2:  # openwakeword
            # Model File Upload
            model_layout = QHBoxLayout()
            model_label = QLabel("Upload Model:")
            self.model_input = QLineEdit(wakeword_config.get("model_path", ""))
            self.model_input.setPlaceholderText("No file selected")
            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(self.browse_model_file)
            model_layout.addWidget(model_label)
            model_layout.addWidget(self.model_input)
            model_layout.addWidget(browse_button)
            layout.addLayout(model_layout)

            # Save Button
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.save_wakeword_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)

    def browse_model_file(self):
        """Open a file dialog to select a model file."""
        wakeword_engine = self.wakeword_engine.currentText()
        file_filter = "All Files (*)"  # Default filter

        if wakeword_engine == "pvporcupine":
            file_filter = "Porcupine Model Files (*.ppn)"
        elif wakeword_engine == "openwakeword":
            file_filter = "OpenWakeWord Model Files (*.tflite *.onnx)"

        file_path, _ = QFileDialog.getOpenFileName(self, "Select Wake Word Model File", "", file_filter)
        if file_path:
            self.model_input.setText(file_path)

    def save_wakeword_configuration(self):
        """Save the wake word configuration to the preference table."""
        wakeword_engine = self.wakeword_engine.currentText()
        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        if wakeword_engine == "Select Engine":
            QMessageBox.warning(self, "Save Failed", "Please select a wake word engine!")
            return

        config = {"wakeword_engine": wakeword_engine}
        if wakeword_engine == "pvporcupine":
            api_key = self.api_input.text().strip()
            if not api_key:
                QMessageBox.warning(self, "Save Failed", "API Key is required for pvporcupine!")
                return
            config["api_key"] = api_key

        model_file = self.model_input.text().strip()
        if wakeword_engine == "openwakeword" and not model_file:
            QMessageBox.warning(self, "Save Failed", "Model File is required for openwakeword!")
            return

        if model_file:
            MODEL_SAVE_PATH = os.path.join(SESSION_PATH, "wakeword")
            os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
            model_name = os.path.basename(model_file)
            model_path = os.path.join(MODEL_SAVE_PATH, model_name)
            shutil.copyfile(model_file, model_path)
            config["model_path"] = model_path

        # Save to preference table
        wakeword_prefs = Preferences.get_preferences_by_user_id(user_id)
        existing_pref = next((pref for pref in wakeword_prefs if pref.setting_key == "wakeword"), None)
        if existing_pref:
            Preferences.update_preference_by_id(
                preference_id=existing_pref.preference_id,
                updated={"setting_value": config}
            )
        else:
            Preferences.insert_new_preference(
                preference_id=str(uuid.uuid4()),
                user_id=user_id,
                setting_key="wakeword",
                setting_value=config
            )

        QMessageBox.information(self, "Saved", "Wake word configuration saved successfully!")
    def create_web_search_page(self):
        """Create the web search configuration page."""
        page = QWidget()
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Load user and preferences
        user_id = self.get_current_user_id()
        if not user_id:
            user_id="0091c4ae-7ed3-4763-ad64-9cc1c3b62ee7"
        # Fetch web search settings from preferences
        web_search_prefs = Preferences.get_preferences_by_user_id(user_id)
        web_search_config = next((pref.setting_value for pref in web_search_prefs if pref.setting_key == "web_search"), {})

        # Search Engine Dropdown
        engine_layout = QHBoxLayout()
        engine_label = QLabel(f"Search Engine Selected: {web_search_config.get('search_engine', 'None')}")
        self.search_engine = QComboBox()
        self.search_engine.addItems(["Select Engine", "Brave", "Google", "DuckDuckGo", "Edge"])
        self.search_engine.setCurrentText(web_search_config.get("search_engine", "Select Engine"))
        engine_layout.addWidget(engine_label)
        engine_layout.addWidget(self.search_engine, alignment=Qt.AlignCenter)
        self.search_engine.currentIndexChanged.connect(self.web_search_click_action)
        layout.addLayout(engine_layout)

        # Configure Button
        self.config_button = QVBoxLayout()
        layout.addLayout(self.config_button)

        # Preload settings if available
        if web_search_config:
            self.web_search_click_action(self.search_engine.currentIndex())

        page.setLayout(layout)
        return page

    def web_search_click_action(self, index):
        """Handle web search engine selection."""
        self.clear_dynamic_widgets()
        layout = self.config_button

        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        # Load existing web search settings
        web_search_prefs = Preferences.get_preferences_by_user_id(user_id)
        web_search_config = next((pref.setting_value for pref in web_search_prefs if pref.setting_key == "web_search"), {})

        if index == 1:  # Brave
            # API Key Input
            api_layout = QHBoxLayout()
            api_label = QLabel("API Key:")
            self.api_input = QLineEdit(web_search_config.get("api_key", ""))
            self.api_input.setPlaceholderText("Enter Brave API key")
            api_layout.addWidget(api_label)
            api_layout.addWidget(self.api_input)
            layout.addLayout(api_layout)

            # Save Button
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.save_web_search_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)
        elif index in [2, 3, 4]:  # Google, DuckDuckGo, Edge
            # Save Button (no API key needed)
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.save_web_search_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)


    def save_web_search_configuration(self):
        """Save the web search configuration to the preference table."""
        search_engine = self.search_engine.currentText()
        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        if search_engine == "Select Engine":
            QMessageBox.warning(self, "Save Failed", "Please select a search engine!")
            return

        config = {"search_engine": search_engine}
        if search_engine == "Brave":
            api_key = self.api_input.text().strip()
            if not api_key:
                QMessageBox.warning(self, "Save Failed", "API Key is required for Brave!")
                return
            config["api_key"] = api_key

        # Save to preference table
        web_search_prefs = Preferences.get_preferences_by_user_id(user_id)
        existing_pref = next((pref for pref in web_search_prefs if pref.setting_key == "web_search"), None)
        if existing_pref:
            Preferences.update_preference_by_id(
                preference_id=existing_pref.preference_id,
                updated={"setting_value": config}
            )
        else:
            Preferences.insert_new_preference(
                preference_id=str(uuid.uuid4()),
                user_id=user_id,
                setting_key="web_search",
                setting_value=config
            )

        QMessageBox.information(self, "Saved", "Web search configuration saved successfully!")

    def create_nextcloud_page(self):
        """Create the NextCloud configuration page."""
        page = QWidget()
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # Load user and preferences
        user_id = self.get_current_user_id()
        if not user_id:
            error_label = QLabel("Error: No user logged in")
            layout.addWidget(error_label)
            page.setLayout(layout)
            return page

        # Fetch NextCloud settings from preferences
        nextcloud_prefs = Preferences.get_preferences_by_user_id(user_id)
        nextcloud_config = next((pref.setting_value for pref in nextcloud_prefs if pref.setting_key == "nextcloud"), {})

        # Enable/Disable Toggle
        toggle_layout = QHBoxLayout()
        toggle_label = QLabel("Enable NextCloud:")
        self.nextcloud_toggle = QCheckBox()
        self.nextcloud_toggle.setChecked(nextcloud_config.get("enabled", False))
        toggle_layout.addWidget(toggle_label)
        toggle_layout.addWidget(self.nextcloud_toggle, alignment=Qt.AlignRight)
        self.nextcloud_toggle.stateChanged.connect(self.nextcloud_toggle_action)
        layout.addLayout(toggle_layout)

        # Configure Button (Dynamic Fields)
        self.config_button = QVBoxLayout()
        layout.addLayout(self.config_button)

        # Preload settings if available
        if nextcloud_config.get("enabled", False):
            self.nextcloud_toggle_action(Qt.Checked)

        page.setLayout(layout)
        return page

    def nextcloud_toggle_action(self, state):
        """Handle NextCloud toggle action."""
        self.clear_dynamic_widgets()
        layout = self.config_button

        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        # Load existing NextCloud settings
        nextcloud_prefs = Preferences.get_preferences_by_user_id(user_id)
        nextcloud_config = next((pref.setting_value for pref in nextcloud_prefs if pref.setting_key == "nextcloud"), {})

        if state == Qt.Checked:
            # Base URL Input
            base_url_layout = QHBoxLayout()
            base_url_label = QLabel("Base URL:")
            self.base_url_input = QLineEdit(nextcloud_config.get("base_url", ""))
            self.base_url_input.setPlaceholderText("Enter NextCloud Base URL (e.g., https://cloud.example.com)")
            base_url_layout.addWidget(base_url_label)
            base_url_layout.addWidget(self.base_url_input)
            layout.addLayout(base_url_layout)

            # Username Input
            username_layout = QHBoxLayout()
            username_label = QLabel("Username:")
            self.username_input = QLineEdit(nextcloud_config.get("username", ""))
            self.username_input.setPlaceholderText("Enter NextCloud Username")
            username_layout.addWidget(username_label)
            username_layout.addWidget(self.username_input)
            layout.addLayout(username_layout)

            # Password Input
            password_layout = QHBoxLayout()
            password_label = QLabel("Password:")
            self.password_input = QLineEdit(nextcloud_config.get("password", ""))
            self.password_input.setPlaceholderText("Enter NextCloud Password")
            self.password_input.setEchoMode(QLineEdit.Password)
            password_layout.addWidget(password_label)
            password_layout.addWidget(self.password_input)
            layout.addLayout(password_layout)

            # Save Button
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.save_nextcloud_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)

    def save_nextcloud_configuration(self):
        """Save the NextCloud configuration to the preference table."""
        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        enabled = self.nextcloud_toggle.isChecked()
        config = {"enabled": enabled}

        if enabled:
            base_url = self.base_url_input.text().strip()
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()

            if not base_url or not username or not password:
                QMessageBox.warning(self, "Save Failed",
                                    "All fields (Base URL, Username, Password) are required when NextCloud is enabled!")
                return

            config.update({
                "base_url": base_url,
                "username": username,
                "password": password
            })

        # Save to preference table
        nextcloud_prefs = Preferences.get_preferences_by_user_id(user_id)
        existing_pref = next((pref for pref in nextcloud_prefs if pref.setting_key == "nextcloud"), None)
        if existing_pref:
            Preferences.update_preference_by_id(
                preference_id=existing_pref.preference_id,
                updated={"setting_value": config}
            )
        else:
            Preferences.insert_new_preference(
                preference_id=str(uuid.uuid4()),
                user_id=user_id,
                setting_key="nextcloud",
                setting_value=config
            )

        QMessageBox.information(self, "Saved", "NextCloud configuration saved successfully!")

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
        user_id = self.get_current_user_id()
        memory_prefs = Preferences.get_preferences_by_user_id(user_id)
        memory_config = next((pref.setting_value for pref in memory_prefs if pref.setting_key == "memory"), {})
        self.memory_engine_dropdown.setCurrentText(
                "Online" if memory_config.get("memo_engine") == "online" else "Offline" if memory_config else "Select Type"
        )
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

        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        memory_prefs = Preferences.get_preferences_by_user_id(user_id)
        memory_config = next((pref.setting_value for pref in memory_prefs if pref.setting_key == "memory"), {})

        if index == 1:  # Online Memory
            # API Key Input
            api_layout = QHBoxLayout()
            api_label = QLabel("API Key:")
            self.api_input = QLineEdit(memory_config.get("api_key", ""))
            self.api_input.setPlaceholderText("Enter Memo Client API Key")
            api_layout.addWidget(api_label)
            api_layout.addWidget(self.api_input)
            layout.addLayout(api_layout)

            # Save Button
            save_button = QPushButton("Save")
            save_button.clicked.connect(self.memory_save_configuration)
            layout.addWidget(save_button, alignment=Qt.AlignCenter)

    def memory_save_configuration(self):
        """Save the memory configuration to the preference table."""
        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        api_key = self.api_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Save Failed", "API Key is required!")
            return

        config = {"memo_engine": "online", "api_key": api_key}
        memory_prefs = Preferences.get_preferences_by_user_id(user_id)
        existing_pref = next((pref for pref in memory_prefs if pref.setting_key == "memory"), None)
        if existing_pref:
            Preferences.update_preference_by_id(
                preference_id=existing_pref.preference_id,
                updated={"setting_value": config}
            )
        else:
            Preferences.insert_new_preference(
                preference_id=str(uuid.uuid4()),
                user_id=user_id,
                setting_key="memory",
                setting_value=config
            )

        QMessageBox.information(self, "Saved", "Memory configuration saved successfully!")

    def clear_memory_action(self):
        """Clear memory for the current user."""
        try:
            memory_settings = MemorySettings()
            memory_settings._initialize_memory()
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

    def get_model(self, models: list):
        """Fetch available models from preferences."""
        user_id = self.get_current_user_id()
        if not user_id:
            logger.warning("No user logged in when fetching models")
            return

        openai_prefs = Preferences.get_preferences_by_user_id(user_id)
        openai_config = next((pref.setting_value for pref in openai_prefs if pref.setting_key == "openai"),  [])
        for conn in openai_config:
            try:
                model_data = self.get_all_models_raw(conn["base_url"].replace('"',""), conn["api_key"])['data']
                for j in model_data:
                    models.append(Model(**{
                        "name": j.get('name', j['id']),
                        "type": "openai",
                        "url": conn["base_url"].replace('"',""),
                        "api_key": conn["api_key"]
                    }))
            except Exception as e:
                logger.error(f"Error fetching models for {conn['base_url'].replace('"',"")}: {e}")

    def create_llm_model_page(self):
        """Create the LLM settings page with improved UI and search functionality."""
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
        save_button.clicked.connect(lambda: self.save_model_selection(model_dropdown.currentText()))
        layout.addWidget(save_button)

        self.llm_model_settings_page.setLayout(layout)

    def save_model_selection(self, model_name):
        """Save selected LLM model to the preference table."""
        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        models = []
        self.get_model(models)
        model_config = {}
        for m in models:
            if model_name in m.name:
                model_config = {"url": m.url, "name": model_name, "type": "openai", "api_key": m.api_key}

        if not model_config:
            QMessageBox.warning(self, "Error", "Model not found!")
            return

        llm_prefs = Preferences.get_preferences_by_user_id(user_id)
        existing_pref = next((pref for pref in llm_prefs if pref.setting_key == "llm_model"), None)
        if existing_pref:
            Preferences.update_preference_by_id(
                preference_id=existing_pref.preference_id,
                updated={"setting_value": model_config}
            )
        else:
            Preferences.insert_new_preference(
                preference_id=str(uuid.uuid4()),
                user_id=user_id,
                setting_key="llm_model",
                setting_value=model_config
            )

        QMessageBox.information(self, "LLM", "Model selected successfully!")

    def create_vision_model_page(self):
        """Create the vision model settings page."""
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
        """Save selected vision model to the preference table."""
        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        models = []
        self.get_model(models)
        model_config = {}
        for m in models:
            if model_name in m.name:
                model_config = {"url": m.url, "name": model_name, "type": "openai", "api_key": m.api_key}

        if not model_config:
            QMessageBox.warning(self, "Error", "Model not found!")
            return

        vision_prefs = Preferences.get_preferences_by_user_id(user_id)
        existing_pref = next((pref for pref in vision_prefs if pref.setting_key == "vision_model"), None)
        if existing_pref:
            Preferences.update_preference_by_id(
                preference_id=existing_pref.preference_id,
                updated={"setting_value": model_config}
            )
        else:
            Preferences.insert_new_preference(
                preference_id=str(uuid.uuid4()),
                user_id=user_id,
                setting_key="vision_model",
                setting_value=model_config
            )

        QMessageBox.information(self, "Vision LLM", "Model selected successfully!")

    def create_huggingface_page(self):
        """Create the HuggingFace settings page."""
        layout = QVBoxLayout()

        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.llm_settings_page))
        layout.addWidget(back_button, alignment=Qt.AlignLeft)

        # API Key Input
        api_key_label = QLabel("HuggingFace API Key:")
        layout.addWidget(api_key_label)
        user_id = self.get_current_user_id()
        api_key = ""
        if user_id:
            hf_prefs = Preferences.get_preferences_by_user_id(user_id)
            hf_config = next((pref.setting_value for pref in hf_prefs if pref.setting_key == "huggingface"), {})
            api_key = hf_config.get("api_key", "")
        hf_api_key_input = QLineEdit(api_key)
        hf_api_key_input.setPlaceholderText("Enter HuggingFace API Key")
        hf_api_key_input.setEchoMode(QLineEdit.Password)
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
        save_button.clicked.connect(lambda: self.save_huggingface_api_key(hf_api_key_input.text()))
        layout.addWidget(save_button, alignment=Qt.AlignCenter)

        self.huggingface_settings_page.setLayout(layout)

    def save_huggingface_api_key(self, api_key):
        """Save the HuggingFace API key to the preference table."""
        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        if not api_key:
            QMessageBox.warning(self, "Error", "API Key cannot be empty!")
            return

        config = {"api_key": api_key}
        hf_prefs = Preferences.get_preferences_by_user_id(user_id)
        existing_pref = next((pref for pref in hf_prefs if pref.setting_key == "huggingface"), None)
        if existing_pref:
            Preferences.update_preference_by_id(
                preference_id=existing_pref.preference_id,
                updated={"setting_value": config}
            )
        else:
            Preferences.insert_new_preference(
                preference_id=str(uuid.uuid4()),
                user_id=user_id,
                setting_key="huggingface",
                setting_value=config
            )

        QMessageBox.information(self, "HuggingFace", "API Key saved successfully!")

    def fetch_url(self, url, key):
        """Fetch data from a URL with authorization."""
        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.warning(f"Connection error: {response.reason}")
                QMessageBox.warning(self, "Connection Error", f"Connection error: {response.reason}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Connection error: {e}")
            QMessageBox.warning(self, "Connection Error", f"Connection error: {e}")
            return None

    def get_all_models_raw(self, base_url_input, api_key_input):
        """Fetch all models from the given base URL."""
        if isinstance(base_url_input, QLabel):
            base_url_input = base_url_input.text()
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

        # Add Scroll Area to Layout
        layout.addWidget(self.scroll_area)

        # Load initial data from preferences
        self.load_initial_data()

        # Add Plus Button
        plus_button = QPushButton()
        plus_button.clicked.connect(lambda: self.add_connections_form())
        plus_button.setIcon(QIcon(os.path.join(JARVIS_DIR, "icons", "plus.svg")))
        layout.addWidget(plus_button)

        # Set layout for the connection page
        self.connection_page.setLayout(layout)

    def get_current_user_id(self):
        """Get the current user's ID from session.json."""
        try:
            from config import SessionManager
            session = SessionManager()
            session.load_session()
            data = session.get_email()
            user = Users.get_user_by_email(data)
            return user.id if user else None
        except Exception as e:
            logger.error(f"Error getting current user ID: {e}")
            return None

    def load_initial_data(self):
        """Load initial Base URL and API Key pairs from the preference table."""
        user_id = self.get_current_user_id()
        if not user_id:
            logger.warning("No user logged in when loading initial data")
            return
        openai_prefs = Preferences.get_preferences_by_user_id(user_id)
        openai_config = next((pref.setting_value for pref in openai_prefs if pref.setting_key == "openai"), [])
        for conn in openai_config:
            self.add_connection_fields(conn.get("base_url").replace('"',""), conn.get("api_key"))

    def add_connections_form(self):
        """Show the form to add a new connection."""
        form_dialog = QDialog(self)
        form_dialog.setWindowTitle("Add New Connection")
        form_layout = QVBoxLayout()

        # Base URL
        name_label = QLabel("Base URL:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter Base URL")
        form_layout.addWidget(name_label)
        form_layout.addWidget(name_input)

        # API Key
        description_label = QLabel("API Key:")
        description_input = QLineEdit()
        description_input.setPlaceholderText("Enter API Key")
        description_input.setEchoMode(QLineEdit.Password)
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
            lambda: self.save_all_connections(api_key_in2=description_input.text(), base_url_in2=name_input.text())
        )
        form_layout.addWidget(save_button, alignment=Qt.AlignCenter)

        form_dialog.setLayout(form_layout)
        form_dialog.exec_()

    def add_connection_fields(self, base_url: str = None, api_key: str = None):
        """Add a new pair of Base URL and API Key textboxes to the GUI."""
        connection_layout = QHBoxLayout()

        # Base URL Input
        base_url_input = QLineEdit(base_url or "")
        base_url_input.setPlaceholderText("Enter Base URL")
        connection_layout.addWidget(base_url_input)

        # API Key Input
        api_key_input = QLineEdit(api_key or "")
        api_key_input.setEchoMode(QLineEdit.Password)
        api_key_input.setPlaceholderText("Enter API Key")
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
        remove_button.clicked.connect(lambda: self.remove_connection_fields(connection_layout, base_url_input, api_key_input))
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
        """Remove a specific pair of Base URL and API Key."""
        base_url = base_url_input.text().strip()
        api_key = api_key_input.text().strip()

        if not base_url or not api_key:
            QMessageBox.warning(self, "Error", "Base URL or API Key is missing!")
            return

        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        try:
            openai_prefs = Preferences.get_preferences_by_user_id(user_id)
            openai_config = next((pref.setting_value for pref in openai_prefs if pref.setting_key == "openai"), [])
            updated_connections = [
                conn for conn in openai_config
                if conn["base_url"] != base_url or conn["api_key"] != api_key
            ]
            existing_pref = next((pref for pref in openai_prefs if pref.setting_key == "openai"), None)
            if existing_pref:
                Preferences.update_preference_by_id(
                    preference_id=existing_pref.preference_id,
                    updated={"setting_value":  updated_connections}
                )
            else:
                QMessageBox.warning(self, "Error", "No connections found to remove.")

            # Remove the row from the GUI
            while connection_layout.count():
                widget = connection_layout.takeAt(0).widget()
                if widget:
                    widget.deleteLater()

            QMessageBox.information(self, "Success", f"Connection for {base_url} removed successfully!")
        except Exception as e:
            logger.error(f"Error removing connection: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while removing the connection: {e}")

    def save_all_connections(self, base_url_in2: str = None, api_key_in2: str = None):
        """Save all Base URL and API Key pairs to the preference table."""
        user_id = self.get_current_user_id()
        if not user_id:
            QMessageBox.warning(self, "Error", "No user logged in!")
            return

        openai_prefs = Preferences.get_preferences_by_user_id(user_id)
        connections = next((pref.setting_value for pref in openai_prefs if pref.setting_key == "openai"),  [])
        print(connections)
        if base_url_in2 and api_key_in2:
            connections.append({"base_url": base_url_in2, "api_key": api_key_in2})

        if not connections:
            QMessageBox.warning(self, "Warning", "No connections found to save!")
            return

        existing_pref = next((pref for pref in openai_prefs if pref.setting_key == "openai"), None)
        try:
            if existing_pref:
                Preferences.update_preference_by_id(
                    preference_id=existing_pref.preference_id,
                    updated={"setting_value":  connections}
                )
            else:
                Preferences.insert_new_preference(
                    preference_id=str(uuid.uuid4()),
                    user_id=user_id,
                    setting_key="openai",
                    setting_value=connections
                )
            QMessageBox.information(self, "Success", "All connections saved successfully!")
        except Exception as e:
            logger.error(f"Error saving connections: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save connections: {e}")

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
        self.agents_layout.setSpacing(10)
        self.agents_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.agents_widget)
        layout.addWidget(self.scroll_area)

        # Add Plus Button
        add_button = QPushButton("+ Add Agent")
        add_button.clicked.connect(self.add_agent_form)
        layout.addWidget(add_button, alignment=Qt.AlignCenter)

        # Set layout for the agents page
        self.agents_page = QWidget()
        self.agents_page.setLayout(layout)
        self.stacked_widget.addWidget(self.agents_page)
        self.stacked_widget.setCurrentWidget(self.agents_page)

        # Load existing agents
        self.load_agents()

    def load_agents(self):
        """Load agents from the database."""
        agents = Agent.get_agents()
        for agent in agents:
            self.add_agent_row(editable=True, id=agent.id, name=agent.name, description=agent.description)

    def add_agent_row(self, name, description, editable=False, id: str = None):
        """Add a row displaying an agent."""
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

        # Add the row layout to the agents layout
        self.agents_layout.addLayout(row_layout)

    def add_agent_form(self):
        """Show the form to add a new agent."""
        form_dialog = QDialog(self)
        form_dialog.setWindowTitle("Add New Agent")
        form_layout = QVBoxLayout()

        # Agent Name
        name_label = QLabel("Agent Name:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter agent name")
        form_layout.addWidget(name_label)
        form_layout.addWidget(name_input)

        # Agent Description
        description_label = QLabel("Description:")
        description_input = QLineEdit()
        description_input.setPlaceholderText("Enter agent description")
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
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Autogen Agent Files (*.json)")
        if file_path:
            file_input.setText(file_path)

    def save_agent(self, name, description, file_path, dialog):
        """Save the new agent to the database."""
        if not name or not description or not file_path:
            QMessageBox.warning(self, "Error", "All fields are required!")
            return

        id = str(uuid.uuid4())
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            file_name = os.path.basename(file_path)
            os.makedirs(os.path.join(JARVIS_DIR, "data", "agents"), exist_ok=True)
            shutil.copyfile(file_path, os.path.join(JARVIS_DIR, "data", "agents", file_name))
            datas = {"file_name": file_name, "data": data}
            Agent.insert_new_agent(id=id, name=name, description=description, file=datas)
            self.add_agent_row(name, description, editable=True, id=id)
            dialog.accept()
            QMessageBox.information(self, "Saved", f"Agent '{name}' has been saved successfully!")
        except Exception as e:
            logger.error(f"Error saving agent: {e}")
            QMessageBox.warning(self, "Error", f"Error saving agent: {e}")

    def delete_agent(self, id):
        """Delete an agent from the database."""
        try:
            agent = Agent.get_agent_by_id(id)
            agent_path = os.path.join(JARVIS_DIR, "data", "agents", agent.file.get("file_name"))
            Agent.delete_agent_by_id(id)
            if os.path.exists(agent_path):
                os.remove(agent_path)
            QMessageBox.information(self, "Delete Agent", "Deleted Successfully!")
            self.refresh_agents_list()
        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete agent: {e}")

    def edit_agent(self, id):
        """Edit an existing agent."""
        agent = Agent.get_agent_by_id(id)
        if not agent:
            QMessageBox.critical(self, "Error", "Agent not found!")
            return

        form_dialog = QDialog(self)
        form_dialog.setWindowTitle("Edit Agent")
        form_layout = QVBoxLayout()

        # Agent Name
        name_label = QLabel("Agent Name:")
        name_input = QLineEdit(agent.name)
        name_input.setPlaceholderText("Enter agent name")
        form_layout.addWidget(name_label)
        form_layout.addWidget(name_input)

        # Agent Description
        description_label = QLabel("Description:")
        description_input = QLineEdit(agent.description)
        description_input.setPlaceholderText("Enter agent description")
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

        form_dialog.setLayout(form_layout)
        form_dialog.exec_()

    def save_edited_agent(self, id, name, description, file, dialog):
        """Save the edited agent to the database."""
        if not name or not description or not file:
            QMessageBox.warning(self, "Error", "All fields are required!")
            return

        try:
            success = Agent.update_agent_by_id(
                id=id,
                updated={
                    "name": name,
                    "description": description,
                    "file": {"file_name": file}
                }
            )
            if success:
                QMessageBox.information(self, "Success", f"Agent '{name}' has been updated successfully!")
                dialog.accept()
                self.refresh_agents_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to update the agent!")
        except Exception as e:
            logger.error(f"Error updating agent: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update agent: {e}")

    def refresh_agents_list(self):
        """Refresh the list of agents in the GUI."""
        for i in reversed(range(self.agents_layout.count())):
            item = self.agents_layout.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
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
                from config import SessionManager
                session = SessionManager()
                session.clear_session()
                QMessageBox.information(self, "Logged Out", "You have been logged out successfully.")
                self.close()
        elif "Wake Word Settings" in setting_name:
            wakeword_page = self.create_wakeword_page()
            self.stacked_widget.addWidget(wakeword_page)
            self.stacked_widget.setCurrentWidget(wakeword_page)
        elif "Memory" in setting_name:
            memory_page = self.create_memory_page()
            self.stacked_widget.addWidget(memory_page)
            self.stacked_widget.setCurrentWidget(memory_page)
        elif setting_name == "Web Search":
            web_search_page = self.create_web_search_page()
            self.stacked_widget.addWidget(web_search_page)
            self.stacked_widget.setCurrentWidget(web_search_page)
        elif setting_name == "NextCloud":
            nextcloud_page = self.create_nextcloud_page()
            self.stacked_widget.addWidget(nextcloud_page)
            self.stacked_widget.setCurrentWidget(nextcloud_page)

        elif setting_name == "LLM Settings":
            self.create_llm_settings_page()
            self.stacked_widget.setCurrentWidget(self.llm_settings_page)
        elif setting_name == "Connection":
            self.create_connection_page()
            self.stacked_widget.setCurrentWidget(self.connection_page)
        elif setting_name == "Agent":
            self.create_agents_page()
        elif setting_name == "HuggingFace":
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
            if isinstance(item, QHBoxLayout):
                label = item.itemAt(0).widget()
                if isinstance(label, ClickableLabel):
                    is_match = text.lower() in label.text().lower()
                    label.setVisible(is_match)
                    item.itemAt(1).widget().setVisible(is_match)
                    visible_count += is_match
            elif isinstance(item, QLabel):
                is_match = text.lower() in item.text().lower()
                item.widget().setVisible(is_match)
                visible_count += is_match
        self.no_setting_label.setVisible(visible_count == 0)

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from jarvis_integration.internals.db import create_tables
    create_tables()
    app = QApplication(sys.argv)
    c = AndroidSettingsDialog()
    c.show()
    sys.exit(app.exec_())