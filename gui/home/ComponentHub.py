# Copyright 2025 Dawood Thouseef
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import logging
import sys

import requests
import git
import yaml
import inspect
import traceback
import time

from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget,
    QLabel, QPushButton, QWidget, QMessageBox, QProgressBar, QLineEdit,
    QComboBox, QTabWidget, QFormLayout, QDialogButtonBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from config import JARVIS_DIR, loggers
from jarvis_integration.models.preferences import Preferences
from jarvis_integration.audio.stt_providers.BaseSTT import BaseSpeech2Text
from jarvis_integration.alert_plugins.base import BaseAlertPlugin
from gui.home.BaseComponent import BaseComponent
from uuid import uuid4

# Configure logging
logger = loggers['COMPONENT_HUB']

COMPONENTS_DIR = os.path.join(JARVIS_DIR,"data", "components")
CONFIG_FILE = os.path.join(JARVIS_DIR, "data","component_hub.json")
UPDATE_CHECK_INTERVAL = 24 * 60 * 60 * 1000  # 24 hours in milliseconds


class ConfigureComponentDialog(QDialog):
    """Dialog to configure component settings based on config.yaml."""

    def __init__(self, component, user_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configure {component['metadata']['name']}")
        self.setGeometry(200, 200, 400, 300)
        self.component = component
        self.user_id = user_id
        self.inputs = {}

        layout = QVBoxLayout()
        self.setLayout(layout)

        form_layout = QFormLayout()
        for field in component.get("config_fields", []):
            label = field.get("label", field["name"])
            input_type = field.get("type", "text")
            default = field.get("default", "")

            if input_type == "text":
                input_widget = QLineEdit()
                input_widget.setText(str(default))
            elif input_type == "select":
                input_widget = QComboBox()
                input_widget.addItems(field.get("options", []))
                if default:
                    input_widget.setCurrentText(str(default))
            else:
                input_widget = QLineEdit()
                input_widget.setText(str(default))

            self.inputs[field["name"]] = input_widget
            form_layout.addRow(label, input_widget)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_config)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_config(self):
        """Save configuration to database."""
        try:
            config = {name: widget.text() if isinstance(widget, QLineEdit) else widget.currentText()
                      for name, widget in self.inputs.items()}
            setting_key = f"component_hub_config_{self.component['type']}_{self.component['metadata']['name']}"
            preference_id = f"{self.user_id}_{setting_key}_{uuid4()}"

            preferences = Preferences.get_preferences_by_user_id(self.user_id)
            existing_pref = next((p for p in preferences if p.setting_key == setting_key), None)
            if existing_pref:
                Preferences.update_preference_by_id(existing_pref.preference_id, {"setting_value": config})
            else:
                Preferences.insert_new_preference(
                    preference_id=preference_id,
                    user_id=self.user_id,
                    setting_key=setting_key,
                    setting_value=config
                )
            logger.info(f"Saved configuration for {self.component['metadata']['name']}")
            QMessageBox.information(self, "Success", "Configuration saved")
            self.accept()
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Error", f"Failed to save configuration: {e}")


class RepoDownloadDialog(QDialog):
    """Dialog to input and download a component repository."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Repository")
        self.setGeometry(200, 200, 400, 200)
        self.setStyleSheet("background-color: white;")

        layout = QVBoxLayout()
        self.setLayout(layout)

        form_layout = QHBoxLayout()
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("Enter repository (e.g., user/repo)")
        form_layout.addWidget(QLabel("Repository:"))
        form_layout.addWidget(self.repo_input)
        layout.addLayout(form_layout)

        self.auth_token = QLineEdit()
        self.auth_token.setPlaceholderText("GitHub token (optional)")
        self.auth_token.setEchoMode(QLineEdit.Password)
        layout.addWidget(QLabel("Auth Token:"))
        layout.addWidget(self.auth_token)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.download_repo)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def validate_repo(self, repo_name):
        """Validate the repository via GitHub API with retry."""
        for attempt in range(3):
            try:
                headers = {}
                if self.auth_token.text().strip():
                    headers["Authorization"] = f"token {self.auth_token.text().strip()}"
                response = requests.get(f"https://api.github.com/repos/{repo_name}", headers=headers, timeout=5)
                if response.status_code == 200:
                    return True
                logger.warning(f"Repository validation failed (attempt {attempt + 1}): {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to validate repository {repo_name} (attempt {attempt + 1}): {e}")
            time.sleep(2)
        return False

    def download_repo(self):
        """Download a repository and validate its contents."""
        repo_name = self.repo_input.text().strip()
        if not repo_name:
            self.status_label.setText("Repository name cannot be empty")
            return
        if len(repo_name) > 100 or not all(c.isalnum() or c in '/-_' for c in repo_name):
            self.status_label.setText("Invalid repository name")
            return

        self.status_label.setText("Validating repository...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        try:
            if not self.validate_repo(repo_name):
                self.status_label.setText("Invalid or inaccessible repository")
                self.progress_bar.setVisible(False)
                return

            repo_url = f"https://github.com/{repo_name}.git"
            repo_dir = os.path.join(COMPONENTS_DIR, repo_name.replace('/', '_'))
            os.makedirs(COMPONENTS_DIR, exist_ok=True)

            auth = None
            if self.auth_token.text().strip():
                auth = f"token {self.auth_token.text().strip()}:x-oauth-basic"
                repo_url = f"https://{auth}@github.com/{repo_name}.git"
            repo = git.Repo.clone_from(repo_url, repo_dir)
            self.progress_bar.setValue(50)

            main_py = os.path.join(repo_dir, "main.py")
            if not os.path.exists(main_py):
                self.status_label.setText("Repository missing main.py")
                repo.close()
                os.system(f"rm -rf {repo_dir}")
                self.progress_bar.setVisible(False)
                return

            # Validate class hierarchy
            with open(main_py, 'r') as f:
                code = f.read()
            module = {}
            exec(code, module)
            component_type = None
            component_class = None
            for name, obj in module.items():
                if inspect.isclass(obj):
                    if issubclass(obj, BaseSpeech2Text) and obj != BaseSpeech2Text:
                        component_type = "speech"
                        component_class = obj
                    elif issubclass(obj, BaseAlertPlugin) and obj != BaseAlertPlugin:
                        component_type = "alert"
                        component_class = obj
                    elif issubclass(obj, BaseComponent) and obj != BaseComponent:
                        component_type = "other"
                        component_class = obj
                    if component_type:
                        break

            if not component_type:
                self.status_label.setText(
                    "main.py does not contain a valid component class (must subclass BaseSpeech2Text, BaseAlertPlugin, or BaseComponent)")
                repo.close()
                os.system(f"rm -rf {repo_dir}")
                self.progress_bar.setVisible(False)
                return

            # Move to appropriate subdirectory
            target_dir = os.path.join(COMPONENTS_DIR, component_type, repo_name.split('/')[-1])
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)
            os.system(f"mv {repo_dir} {target_dir}")
            repo_dir = target_dir

            metadata = {"name": repo_name.split('/')[-1], "version": "1.0", "description": "", "type": component_type}
            metadata_json = os.path.join(repo_dir, "metadata.json")
            if os.path.exists(metadata_json):
                with open(metadata_json, 'r') as f:
                    metadata.update(json.load(f))
            config_yaml = os.path.join(repo_dir, "config.yaml")
            config_fields = []
            if os.path.exists(config_yaml):
                with open(config_yaml, 'r') as f:
                    config_data = yaml.safe_load(f)
                    config_fields = config_data.get("config_fields", [])

            metadata_file = os.path.join(COMPONENTS_DIR, component_type, f"{repo_name.replace('/', '_')}.json")
            os.makedirs(os.path.dirname(metadata_file), exist_ok=True)
            with open(metadata_file, 'w') as f:
                json.dump({
                    "repo": repo_name,
                    "path": repo_dir,
                    "type": component_type,
                    "metadata": metadata,
                    "config_fields": config_fields,
                    "commit_hash": repo.head.commit.hexsha
                }, f)

            self.progress_bar.setValue(100)
            self.status_label.setText(f"Downloaded {repo_name}")
            logger.info(f"Downloaded {component_type} component: {repo_name}")
            self.accept()
        except Exception as e:
            logger.error(f"Failed to download repository {repo_name}: {e}\n{traceback.format_exc()}")
            self.status_label.setText(f"Failed to download: {e}")
            self.progress_bar.setVisible(False)
            if os.path.exists(repo_dir):
                os.system(f"rm -rf {repo_dir}")


class ComponentHub(QDialog):
    """Centralized hub for managing community-developed components in the virtual assistant."""
    update_available = pyqtSignal(list)  # Signal for update notifications
    speech_provider_added = pyqtSignal(str)  # Signal for new speech providers

    def __init__(self, parent=None, user_id=None, alert_checker=None):
        super().__init__(parent)
        self.setWindowTitle("Component Hub")
        self.setGeometry(150, 150, 800, 500)
        self.user_id = user_id or "default_user"
        self.alert_checker = alert_checker
        self.config = self.load_config()
        self.pending_updates = []
        logger.info(f"Initializing ComponentHub for user_id: {self.user_id}")

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_updates)
        self.update_timer.start(UPDATE_CHECK_INTERVAL)

        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.main_layout)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(150)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border-right: 1px solid lightgray;
                font-size: 14px;
                color: black;
            }
            QListWidget::item {
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        self.sidebar.addItem("Installed")
        self.sidebar.addItem("Store")
        self.sidebar.currentRowChanged.connect(self.switch_page)
        self.main_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        self.installed_page = self.create_installed_page()
        self.store_page = self.create_store_page()
        self.stack.addWidget(self.installed_page)
        self.stack.addWidget(self.store_page)
        self.sidebar.setCurrentRow(0)
        self.scan_components()
        self.check_updates()

    def load_config(self):
        """Load component configuration from JSON file and database."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            else:
                config = {
                    "installed_components": [],
                    "available_components": []
                }

            if self.user_id:
                preferences = Preferences.get_preferences_by_user_id(self.user_id)
                for pref in preferences:
                    if pref.setting_key.startswith("component_hub_") and not pref.setting_key.startswith(
                            "component_hub_config_"):
                        component_type, name = pref.setting_key.split("_", 2)[1:]
                        config["installed_components"].append({
                            "name": name,
                            "type": component_type,
                            "metadata": pref.setting_value.get("metadata", {}),
                            "path": pref.setting_value.get("path", ""),
                            "config_fields": pref.setting_value.get("config_fields", []),
                            "commit_hash": pref.setting_value.get("commit_hash", ""),
                            "repo": pref.setting_value.get("repo", name)
                        })
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}\n{traceback.format_exc()}")
            return {"installed_components": [], "available_components": []}

    def save_config(self):
        """Save component configuration to JSON file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}\n{traceback.format_exc()}")

    def scan_components(self):
        """Scan COMPONENTS_DIR for installed components."""
        try:
            os.makedirs(COMPONENTS_DIR, exist_ok=True)
            for category in ["speech", "alert", "other"]:
                category_dir = os.path.join(COMPONENTS_DIR, category)
                if not os.path.exists(category_dir):
                    continue
                for file in os.listdir(category_dir):
                    if file.endswith(".json"):
                        try:
                            with open(os.path.join(category_dir, file), 'r') as f:
                                data = json.load(f)
                            component_name = data.get("repo", "").split('/')[-1]
                            if component_name and component_name not in [c["name"] for c in
                                                                         self.config["installed_components"]]:
                                self.config["installed_components"].append({
                                    "name": component_name,
                                    "type": data["type"],
                                    "path": data["path"],
                                    "metadata": data["metadata"],
                                    "config_fields": data.get("config_fields", []),
                                    "commit_hash": data.get("commit_hash", ""),
                                    "repo": data["repo"]
                                })
                        except Exception as e:
                            logger.warning(f"Skipping invalid component metadata {file}: {e}")
            self.save_config()
            logger.info("Scanned installed components")
        except Exception as e:
            logger.error(f"Failed to scan components: {e}\n{traceback.format_exc()}")

    def check_updates(self):
        """Check for updates to installed components."""
        self.pending_updates = []
        try:
            headers = {}
            auth_token = os.getenv("GITHUB_TOKEN", "")
            if auth_token:
                headers["Authorization"] = f"token {auth_token}"

            for component in self.config["installed_components"]:
                repo_name = component.get("repo", "")
                if not repo_name:
                    continue
                try:
                    response = requests.get(f"https://api.github.com/repos/{repo_name}/commits/main",
                                            headers=headers, timeout=5)
                    if response.status_code == 200:
                        latest_commit = response.json()["sha"]
                        current_commit = component.get("commit_hash", "")
                        if latest_commit != current_commit:
                            self.pending_updates.append(component["name"])
                            logger.info(f"Update available for {component['name']}: {latest_commit}")
                            if self.alert_checker:
                                self.update_available.emit([f"Update available for component {component['name']}"])
                except Exception as e:
                    logger.warning(f"Failed to check update for {component['name']}: {e}")

            installed_item = self.sidebar.item(0)
            installed_item.setText(
                f"Installed{' (' + str(len(self.pending_updates)) + ')' if self.pending_updates else ''}")
        except Exception as e:
            logger.error(f"Update check failed: {e}\n{traceback.format_exc()}")

    def create_installed_page(self):
        """Create page for installed components."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title = QLabel("Installed Components")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)

        tabs = QTabWidget()
        for category in ["speech", "alert", "other"]:
            tab_widget = QWidget()
            tab_layout = QVBoxLayout()
            tab_widget.setLayout(tab_layout)

            for component in [c for c in self.config["installed_components"] if c["type"] == category]:
                comp_widget = QWidget()
                comp_layout = QHBoxLayout()
                comp_widget.setLayout(comp_layout)

                comp_button = QPushButton(
                    f"{component['name']}{' (Update)' if component['name'] in self.pending_updates else ''}")
                comp_button.setStyleSheet("""
                    QPushButton {
                        font-size: 14px;
                        color: #333;
                        background: transparent;
                        border: none;
                        text-align: left;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #E8F0FE;
                    }
                """)
                comp_button.clicked.connect(lambda _, c=component["name"]: self.show_component_details(c))
                comp_layout.addWidget(comp_button)

                configure_button = QPushButton("Configure")
                configure_button.setStyleSheet("""
                    QPushButton {
                        background-color: #FFC107;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #FFA000;
                    }
                """)
                configure_button.clicked.connect(lambda _, c=component: self.configure_component(c))
                comp_layout.addWidget(configure_button)

                if component["name"] in self.pending_updates:
                    update_button = QPushButton("Update")
                    update_button.setStyleSheet("""
                        QPushButton {
                            background-color: #2196F3;
                            color: white;
                            padding: 5px 10px;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #1976D2;
                        }
                    """)
                    update_button.clicked.connect(lambda _, c=component["name"]: self.update_component(c))
                    comp_layout.addWidget(update_button)

                uninstall_button = QPushButton("Uninstall")
                uninstall_button.setStyleSheet("""
                    QPushButton {
                        background-color: #F44336;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #D32F2F;
                    }
                """)
                uninstall_button.clicked.connect(lambda _, c=component["name"]: self.uninstall_component(c))
                comp_layout.addWidget(uninstall_button)

                tab_layout.addWidget(comp_widget)

            tabs.addTab(tab_widget, category.capitalize())
        layout.addWidget(tabs)
        return widget

    def create_store_page(self):
        """Create store page for discovering components."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        title_layout = QHBoxLayout()
        title = QLabel("Component Store")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title_layout.addWidget(title)

        add_repo_button = QPushButton("Add Repository")
        add_repo_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        add_repo_button.clicked.connect(self.open_repo_dialog)
        title_layout.addStretch()
        title_layout.addWidget(add_repo_button)
        layout.addLayout(title_layout)

        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search components...")
        self.search_bar.textChanged.connect(self.filter_components)
        search_layout.addWidget(self.search_bar)

        self.category_filter = QComboBox()
        self.category_filter.addItems(["All", "Speech", "Alert", "Other"])
        self.category_filter.currentTextChanged.connect(self.filter_components)
        search_layout.addWidget(self.category_filter)
        layout.addLayout(search_layout)

        self.components_widget = QWidget()
        self.components_layout = QVBoxLayout()
        self.components_widget.setLayout(self.components_layout)
        layout.addWidget(self.components_widget)

        self.update_store_components()
        return widget

    def update_store_components(self):
        """Update the list of available components."""
        while self.components_layout.count():
            item = self.components_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for component in self.config["available_components"]:
            comp_widget = QWidget()
            comp_layout = QHBoxLayout()
            comp_widget.setLayout(comp_layout)

            comp_button = QPushButton(component["name"])
            comp_button.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    color: #333;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #E8F0FE;
                }
            """)
            comp_button.clicked.connect(lambda _, c=component["name"]: self.show_component_details(c))
            comp_layout.addWidget(comp_button)

            install_button = QPushButton("Install")
            install_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #388E3C;
                }
            """)
            install_button.clicked.connect(lambda _, c=component["name"]: self.install_component(c))
            comp_layout.addWidget(install_button)

            self.components_layout.addWidget(comp_widget)

    def filter_components(self):
        """Filter components based on search and category."""
        query = self.search_bar.text().strip().lower()
        category = self.category_filter.currentText().lower()
        filtered_components = [
            c for c in self.config["available_components"]
            if query in c["name"].lower() and (category == "all" or c["type"] == category)
        ]
        self.config["available_components"] = filtered_components
        self.update_store_components()

    def open_repo_dialog(self):
        """Open dialog to add a repository."""
        dialog = RepoDownloadDialog(self)
        if dialog.exec_():
            repo_name = dialog.repo_input.text().strip()
            component_name = repo_name.split('/')[-1]
            metadata_file = os.path.join(COMPONENTS_DIR, dialog.status_label.text().split()[1],
                                         f"{repo_name.replace('/', '_')}.json")
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            self.config["available_components"].append({
                "name": component_name,
                "type": data["type"],
                "repo": repo_name
            })
            self.save_config()
            self.update_store_components()
            logger.info(f"Added repository: {repo_name}")

    def switch_page(self, index):
        """Switch between installed and store pages."""
        self.stack.setCurrentIndex(index)

    def show_component_details(self, component_name):
        """Show details for a component."""
        component = next((c for c in self.config["installed_components"] + self.config["available_components"]
                          if c["name"] == component_name), None)
        if component:
            details = f"Name: {component['name']}\nType: {component['type'].capitalize()}\n"
            details += f"Version: {component['metadata'].get('version', 'Unknown')}\n"
            details += f"Description: {component['metadata'].get('description', 'No description')}"
            QMessageBox.information(self, "Component Details", details)
        else:
            QMessageBox.warning(self, "Error", f"Component {component_name} not found")

    def configure_component(self, component):
        """Open configuration dialog for a component."""
        if not component.get("config_fields"):
            QMessageBox.information(self, "Info", "No configuration options available")
            return
        dialog = ConfigureComponentDialog(component, self.user_id, self)
        dialog.exec_()

    def install_component(self, component_name):
        """Install a component and save to database."""
        try:
            component = next((c for c in self.config["available_components"] if c["name"] == component_name), None)
            if not component:
                raise ValueError("Component not found")

            component_metadata = {
                "name": component_name,
                "type": component["type"],
                "path": os.path.join(COMPONENTS_DIR, component["type"], component_name),
                "metadata": {"name": component_name, "version": "1.0", "description": ""},
                "config_fields": [],
                "commit_hash": "",
                "repo": component["repo"]
            }
            metadata_file = os.path.join(COMPONENTS_DIR, component["type"],
                                         f"{component['repo'].replace('/', '_')}.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                component_metadata.update({
                    "metadata": data["metadata"],
                    "config_fields": data["config_fields"],
                    "commit_hash": data["commit_hash"],
                    "path": data["path"]
                })

            self.config["installed_components"].append(component_metadata)
            self.config["available_components"].remove(component)
            self.save_config()

            setting_key = f"component_hub_{component['type']}_{component_name}"
            preference_id = f"{self.user_id}_{setting_key}_{uuid4()}"
            Preferences.insert_new_preference(
                preference_id=preference_id,
                user_id=self.user_id,
                setting_key=setting_key,
                setting_value=component_metadata
            )
            logger.info(f"Installed component: {component_name}")

            if component["type"] == "speech":
                self.speech_provider_added.emit(component_name)
            elif component["type"] == "alert" and self.alert_checker:
                self.alert_checker.load_plugins()

            self.refresh_ui()
            QMessageBox.information(self, "Success", f"Installed {component_name}")
        except Exception as e:
            logger.error(f"Failed to install component {component_name}: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Error", f"Failed to install {component_name}: {e}")

    def update_component(self, component_name):
        """Update a component to the latest version."""
        try:
            component = next((c for c in self.config["installed_components"] if c["name"] == component_name), None)
            if not component:
                raise ValueError("Component not found")

            repo_name = component.get("repo", "")
            repo_dir = component["path"]
            if not os.path.exists(repo_dir):
                raise ValueError("Component directory missing")

            repo = git.Repo(repo_dir)
            origin = repo.remotes.origin
            auth_token = os.getenv("GITHUB_TOKEN", "")
            if auth_token:
                origin.url = f"https://token {auth_token}:x-oauth-basic@github.com/{repo_name}.git"
            origin.pull()
            new_commit = repo.head.commit.hexsha

            metadata_file = os.path.join(COMPONENTS_DIR, component["type"], f"{repo_name.replace('/', '_')}.json")
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            data["commit_hash"] = new_commit
            metadata_json = os.path.join(repo_dir, "metadata.json")
            if os.path.exists(metadata_json):
                with open(metadata_json, 'r') as f:
                    data["metadata"].update(json.load(f))
            with open(metadata_file, 'w') as f:
                json.dump(data, f)

            setting_key = f"component_hub_{component['type']}_{component_name}"
            preferences = Preferences.get_preferences_by_user_id(self.user_id)
            existing_pref = next((p for p in preferences if p.setting_key == setting_key), None)
            if existing_pref:
                Preferences.update_preference_by_id(existing_pref.preference_id, {
                    "setting_value": {
                        "name": component_name,
                        "type": component["type"],
                        "path": component["path"],
                        "metadata": data["metadata"],
                        "config_fields": data["config_fields"],
                        "commit_hash": new_commit,
                        "repo": repo_name
                    }
                })

            self.pending_updates.remove(component_name)
            self.config["installed_components"] = [
                c if c["name"] != component_name else {
                    "name": component_name,
                    "type": component["type"],
                    "path": component["path"],
                    "metadata": data["metadata"],
                    "config_fields": data["config_fields"],
                    "commit_hash": new_commit,
                    "repo": repo_name
                } for c in self.config["installed_components"]
            ]
            self.save_config()

            if component["type"] == "speech":
                self.speech_provider_added.emit(component_name)
            elif component["type"] == "alert" and self.alert_checker:
                self.alert_checker.load_plugins()
            if self.alert_checker:
                self.update_available.emit([f"Component {component_name} updated"])

            self.refresh_ui()
            logger.info(f"Updated component: {component_name}")
            QMessageBox.information(self, "Success", f"Updated {component_name}")
        except Exception as e:
            logger.error(f"Failed to update component {component_name}: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Error", f"Failed to update {component_name}: {e}")

    def uninstall_component(self, component_name):
        """Uninstall a component and remove from database."""
        try:
            component = next((c for c in self.config["installed_components"] if c["name"] == component_name), None)
            if not component:
                raise ValueError("Component not found")

            repo_dir = component.get("path")
            if repo_dir and os.path.exists(repo_dir):
                os.system(f"rm -rf {repo_dir}")
            metadata_file = os.path.join(COMPONENTS_DIR, component["type"], f"{component['name']}.json")
            if os.path.exists(metadata_file):
                os.remove(metadata_file)

            self.config["installed_components"].remove(component)
            self.config["available_components"].append({
                "name": component_name,
                "type": component["type"],
                "repo": component.get("repo", component_name)
            })
            self.save_config()

            setting_key = f"component_hub_{component['type']}_{component_name}"
            config_key = f"component_hub_config_{component['type']}_{component_name}"
            preferences = Preferences.get_preferences_by_user_id(self.user_id)
            for pref in preferences:
                if pref.setting_key in [setting_key, config_key]:
                    Preferences.delete_preference_by_id(pref.preference_id)

            if component["type"] == "alert" and self.alert_checker:
                self.alert_checker.load_plugins()
            elif component["type"] == "speech":
                self.speech_provider_added.emit(component_name)

            self.refresh_ui()
            logger.info(f"Uninstalled component: {component_name}")
            QMessageBox.information(self, "Success", f"Uninstalled {component_name}")
        except Exception as e:
            logger.error(f"Failed to uninstall component {component_name}: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Error", f"Failed to uninstall {component_name}: {e}")

    def refresh_ui(self):
        """Refresh the UI after changes."""
        self.stack.removeWidget(self.installed_page)
        self.stack.removeWidget(self.store_page)
        self.installed_page = self.create_installed_page()
        self.store_page = self.create_store_page()
        self.stack.insertWidget(0, self.installed_page)
        self.stack.insertWidget(1, self.store_page)
        self.stack.setCurrentIndex(0)
        installed_item = self.sidebar.item(0)
        installed_item.setText(
            f"Installed{' (' + str(len(self.pending_updates)) + ')' if self.pending_updates else ''}")


if __name__=="__main__":
    app=QApplication(sys.argv)
    c=ComponentHub()
    c.show()
    sys.exit(app.exec_())