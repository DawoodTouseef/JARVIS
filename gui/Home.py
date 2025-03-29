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
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout,  QLineEdit, QLabel, QScrollArea,
    QPushButton, QWidget, QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from AppOpener import open as open_app, give_appnames
import os
from config import JARVIS_DIR

class HomeDialog(QDialog):
    """Android-style Apps Widget with grid layout for installed applications."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("App Launcher")
        self.setGeometry(100, 100, 700, 800)
        self.setStyleSheet("background-color: white;")  # Android-like white background

        # Retrieve installed applications
        self.applications = self.get_installed_applications()

        # Main Layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.layout)

        # Search Bar
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

        # Scroll Area for Applications
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        # App Grid Widget
        self.apps_widget = QWidget()
        self.apps_layout = QGridLayout(self.apps_widget)
        self.apps_layout.setSpacing(15)
        self.scroll_area.setWidget(self.apps_widget)
        self.layout.addWidget(self.scroll_area)

        # Load Applications
        self.load_applications()

    def get_installed_applications(self):
        """
        Retrieve a list of installed applications using AppOpener.
        Returns a list of dictionaries containing app names.
        """
        appnames = give_appnames()  # Get available app names
        return [{"name": app, "icon": os.path.join(JARVIS_DIR,"icons","jarvis-logo1.svg")} for app in sorted(appnames)]  # Default icon

    def load_applications(self):
        """Load applications into the grid layout."""
        self.update_grid_layout()

    def update_grid_layout(self):
        """Dynamically adjust grid layout based on window width."""
        # Clear existing layout
        while self.apps_layout.count():
            item = self.apps_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Determine the number of columns dynamically
        available_width = self.scroll_area.width()
        tile_width = 120  # Each tile (app icon + label) takes ~120px
        columns = max(available_width // tile_width, 2)  # Minimum 2 columns

        row, col = 0, 0
        for app in self.applications:
            self.add_application_tile(app["name"], app["icon"], row, col)
            col += 1
            if col >= columns:  # Move to next row when column limit is reached
                col = 0
                row += 1

    def add_application_tile(self, name, icon_path, row, col):
        """Create a clickable tile for each application."""
        app_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # App Icon
        icon_label = QLabel()
        pixmap = QPixmap(icon_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)

        # App Name
        # App Name
        name_label = QLabel(name)
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #333; margin-top: 5px;")

        # Open Button
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

        # Add to layout
        layout.addWidget(launch_button)
        layout.addWidget(name_label)
        app_widget.setLayout(layout)

        # Add to grid layout
        self.apps_layout.addWidget(app_widget, row, col)

    def filter_applications(self):
        """Filter applications dynamically based on search query."""
        query = self.search_bar.text().strip().lower()
        for i in range(self.apps_layout.count()):
            app_widget = self.apps_layout.itemAt(i).widget()
            name_label = app_widget.layout().itemAt(1).widget()  # Get name label
            app_name = name_label.text().lower()
            app_widget.setVisible(query in app_name)

    def open_application(self, app_name):
        """Open the selected application using AppOpener."""
        try:
            open_app(app_name)
        except Exception:
            QMessageBox.warning(self, "Error", f"Failed to open application '{app_name}'")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = HomeDialog()
    window.show()
    sys.exit(app.exec_())
