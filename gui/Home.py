from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QLabel, QScrollArea,
    QPushButton, QWidget, QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
import os
from config import JARVIS_DIR
from gui.settings import AndroidSettingsDialog
from gui.terminal.terminal_dialog import TerminalDialog
from gui.home.ComponentHub import ComponentHub
from gui.Objects.AlertChecker import AlertCheck
from core.agents.personal_assistant import YahooFinanceTool, DatabaseTool


class HomeDialog(QDialog):
    """Android-style Apps Widget with grid layout for installed applications."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("App Launcher")
        self.setGeometry(100, 100, 700, 800)
        self.setStyleSheet("background-color: white;")
        self.user_id =  "default_user"
        self.db_tool = DatabaseTool()
        self.yahoo_tool = YahooFinanceTool()
        self.alert_checker = AlertCheck(self.db_tool, self.yahoo_tool,self)
        self.component_hub = None  # Store ComponentHub instance for signal connections

        self.applications = self.get_installed_applications()

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.layout)

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search applications...")
        self.search_bar.textChanged.connect(self.filter_applications)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 16px;
                border: 2px solid lightgray;
                border-radius: 10px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
        """)
        self.layout.addWidget(self.search_bar)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        self.apps_widget = QWidget()
        self.apps_layout = QGridLayout(self.apps_widget)
        self.apps_layout.setSpacing(15)
        self.scroll_area.setWidget(self.apps_widget)
        self.layout.addWidget(self.scroll_area)

        self.load_applications()

    def get_installed_applications(self):
        """Retrieve a list of installed applications."""
        apps = [
            {
                "name": "Virtual Assistant Terminal",
                "icon": os.path.join(JARVIS_DIR, "icons", "terminal.svg") if os.path.exists(os.path.join(JARVIS_DIR, "icons", "terminal.svg")) else os.path.join(JARVIS_DIR, "icons", "jarvis-logo1.svg")
            },
            {
                "name": "Settings",
                "icon": os.path.join(JARVIS_DIR, "icons", "settings.svg") if os.path.exists(os.path.join(JARVIS_DIR, "icons", "settings.svg")) else os.path.join(JARVIS_DIR, "icons", "jarvis-logo1.svg")
            },
            {
                "name": "Component Hub",
                "icon": os.path.join(JARVIS_DIR, "icons", "hub.svg") if os.path.exists(os.path.join(JARVIS_DIR, "icons", "hub.svg")) else os.path.join(JARVIS_DIR, "icons", "jarvis-logo1.svg")
            }
        ]
        return apps

    def load_applications(self):
        """Load applications into the grid layout."""
        self.update_grid_layout()

    def update_grid_layout(self):
        """Dynamically adjust grid layout based on window width."""
        while self.apps_layout.count():
            item = self.apps_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        available_width = self.scroll_area.width()
        tile_width = 120
        columns = max(available_width // tile_width, 2)

        row, col = 0, 0
        for app in self.applications:
            self.add_application_tile(app["name"], app["icon"], row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

    def add_application_tile(self, name, icon_path, row, col):
        """Create a clickable tile for each application."""
        app_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        pixmap = QPixmap(icon_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)

        name_label = QLabel(name)
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #333; margin-top: 5px;")

        launch_button = QPushButton()
        launch_button.setIcon(QIcon(icon_path))
        launch_button.setIconSize(pixmap.size())
        launch_button.setFixedSize(80, 80)
        launch_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #DDDDDD;
                border-radius: 15px;
                background-color: white;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #E8F0FE;
                border-color: #2196F3;
            }
            QPushButton:pressed {
                background-color: #BBDEFB;
            }
        """)
        launch_button.clicked.connect(lambda: self.open_application(name))

        layout.addWidget(launch_button)
        layout.addWidget(name_label)
        app_widget.setLayout(layout)
        self.apps_layout.addWidget(app_widget, row, col)

    def filter_applications(self):
        """Filter applications dynamically based on search query."""
        query = self.search_bar.text().strip().lower()
        for i in range(self.apps_layout.count()):
            app_widget = self.apps_layout.itemAt(i).widget()
            name_label = app_widget.layout().itemAt(1).widget()
            app_name = name_label.text().lower()
            app_widget.setVisible(query in app_name)

    def open_application(self, app_name):
        """Open the selected application."""
        try:
            if app_name == "Virtual Assistant Terminal":
                terminal_dialog = TerminalDialog(self)
                terminal_dialog.exec_()
            elif app_name == "Settings":
                settings_dialog = AndroidSettingsDialog(self)
                settings_dialog.exec_()
            elif app_name == "Component Hub":
                self.component_hub = ComponentHub(self, user_id=self.user_id, alert_checker=self.alert_checker)
                self.component_hub.update_available.connect(self.alert_checker.alert_triggered.emit)
                self.component_hub.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open application '{app_name}': {e}")

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = HomeDialog()
    window.show()
    sys.exit(app.exec_())