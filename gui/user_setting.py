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
    QPushButton,
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QWidget,
    QHeaderView,
    QFormLayout,
)
from PyQt5.QtGui import QColor,QIcon
from PyQt5.QtCore import Qt
from jarvis_integration.models.users import Users

import uuid
import os
from config import JARVIS_DIR


svg = os.path.join(JARVIS_DIR, "icons")
class UserDialog(QDialog):
    """Popup Dialog for managing users."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Settings")
        self.setGeometry(100, 100, 800, 600)
        self.db = Users

        layout = QVBoxLayout()

        # Table for user data
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID","Name", "Role", "Email", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                font-family: Arial, sans-serif;
                font-size: 14px;
                background-color: #f4f4f4;
                color: #333;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #5C6BC0;
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 8px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QComboBox {
                min-width: 100px;
            }
            QComboBox QAbstractItemView {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
            }
        """)
        self.refresh_table()
        self.table.cellClicked.connect(self.handle_cell_click)
        # Button to add a new user
        self.add_user_button = QPushButton("Add User")
        self.add_user_button.clicked.connect(self.add_user_dialog)

        layout.addWidget(self.table)
        layout.addWidget(self.add_user_button)

        self.setLayout(layout)

    def refresh_table(self):
        """Refresh the table with data from the database."""
        try:
            self.table.setRowCount(self.db.get_num_users())
            for row, user in enumerate(self.db.get_users()):
                # Non-editable ID cell
                id_item = QTableWidgetItem(user.id)
                id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 0, id_item)

                # Non-editable Name cell
                name_item = QTableWidgetItem(user.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 1, name_item)

                # Role cell logic
                role_item = QTableWidgetItem(user.role)
                role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)  # Make role uneditable by default

                if user.role.lower() == "admin":
                    role_item.setBackground(QColor(144, 238, 144))  # Light green
                    role_item.setForeground(QColor(34, 139, 34))  # Dark green
                    if self.db.get_num_users() <= 1:  # If only one user, it's the first admin
                        role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)  # Make role permanently uneditable
                elif user.role.lower() == "user":
                    role_item.setBackground(QColor(255, 182, 193))  # Light red (Pink)
                    role_item.setForeground(QColor(178, 34, 34))  # Dark red

                self.table.setItem(row, 2, role_item)

                # Non-editable Email cell
                email_item = QTableWidgetItem(user.email)
                email_item.setFlags(email_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 3, email_item)

                # Action buttons (Edit and Delete)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout()
                actions_layout.setContentsMargins(0, 0, 0, 0)
                actions_layout.setSpacing(5)

                # Edit button
                edit_button = QPushButton()
                edit_button.setIcon(QIcon(os.path.join(svg,"edit.svg")))
                edit_button.setToolTip("Edit User")
                edit_button.clicked.connect(lambda _, r=row: self.edit_user_dialog(self.table.item(r, 0).text()))
                actions_layout.addWidget(edit_button)

                # Delete button
                delete_button = QPushButton()
                delete_button.setIcon(QIcon(os.path.join(svg,"delete.svg")))
                delete_button.setStyleSheet("""
                *{
                    background-color:red;
                }
                """)
                delete_button.setToolTip("Delete User")
                delete_button.clicked.connect(lambda _, r=row: self.delete_user(self.table.item(r, 0).text()))
                actions_layout.addWidget(delete_button)

                actions_widget.setLayout(actions_layout)
                self.table.setCellWidget(row, 4, actions_widget)

            # Set table headers
            self.table.setHorizontalHeaderLabels(["ID", "Name", "Role", "Email", "Actions"])

        except Exception as e:
            pass

    def edit_user_dialog(self, user_id):
        """Dialog to edit a user's details."""
        user = next((u for u in self.db.get_users() if u.id == user_id), None)
        if not user:
            QMessageBox.warning(self, "Error", "User not found!")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit User")
        dialog.setGeometry(150, 150, 300, 200)
        dialog.setStyleSheet("""
                    QTableWidget {
                        font-family: Arial, sans-serif;
                        font-size: 14px;
                        background-color: #f4f4f4;
                        color: #333;
                    }
                    QTableWidget::item {
                        padding: 10px;
                    }
                    QHeaderView::section {
                        background-color: #5C6BC0;
                        color: white;
                        font-weight: bold;
                        font-size: 16px;
                        padding: 8px;
                    }
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border-radius: 5px;
                        padding: 10px 20px;
                        font-size: 14px;
                        font-weight: bold;
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QComboBox {
                        min-width: 100px;
                    }
                    QComboBox QAbstractItemView {
                        background-color: #f0f0f0;
                        border: 1px solid #ccc;
                    }
                """)
        layout = QVBoxLayout()

        name_input = QLineEdit(user.name)
        role = user.role
        role_dropdown = None
        if self.db.get_num_users() > 0:
            role_dropdown = QComboBox()
            if role=="user":
                role_dropdown.addItems(["User", "Admin"])
            else:
                role_dropdown.addItems(['Admin','User'])
            role = role_dropdown.currentText()
        email_input = QLineEdit(user.email)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_edited_user(dialog, user_id, name_input.text(), role, email_input.text()))

        layout.addWidget(QLabel("Name:"))
        layout.addWidget(name_input)
        layout.addWidget(QLabel("Role:"))
        layout.addWidget(role_dropdown)
        layout.addWidget(QLabel("Email:"))
        layout.addWidget(email_input)
        layout.addWidget(save_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def is_valid_email(self, email):
        """Validate the email address format."""
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None

    def save_edited_user(self, dialog, user_id, name, role, email):
        """Save the edited user details."""
        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return
        self.db.update_user_by_id(user_id, {"name": name, "role": role, "email": email})
        self.refresh_table()
        dialog.close()

    def delete_user(self, user_id):
        """Delete a user."""
        from config import SESSION_PATH
        import json
        with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
            data = json.load(f)
        if "email" in data:
            users = Users.get_user_by_email(data['email'])
            if users.id!=user_id:
                self.db.delete_user_by_id(user_id)
                self.refresh_table()
            else:
                QMessageBox.warning(self,"Delete User","Logout the Account then delete the user.")

    def add_user_dialog(self):
        """Dialog to add a new user."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add User")
        dialog.setFixedSize(400, 300)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f9f9f9;
                border-radius: 8px;
            }
            QLabel {
                font-size: 14px;
                font-family: Arial, sans-serif;
                color: #333;
            }
            QLineEdit, QComboBox {
                font-size: 14px;
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                font-size: 14px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        # Layout
        main_layout = QVBoxLayout()

        # Form layout for inputs
        form_layout = QFormLayout()
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(15)

        # Name input
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter the user's full name")
        form_layout.addRow("Name:", name_input)

        # Role dropdown
        role = "Admin"
        role_dropdown = None
        if self.db.get_num_users() > 0:
            role_dropdown = QComboBox()
            role_dropdown.addItems(["User", "Admin"])
            role_dropdown.setToolTip("Select the user's role")
            form_layout.addRow("Role:", role_dropdown)
            role = role_dropdown.currentText()

        # Email input
        email_input = QLineEdit()
        email_input.setPlaceholderText("Enter the user's email address")
        email_input.setToolTip("Provide a valid email address")
        form_layout.addRow("Email:", email_input)

        # Password input
        password_input = QLineEdit()
        password_input.setPlaceholderText("Create a password for the user")
        password_input.setEchoMode(QLineEdit.Password)
        password_input.setToolTip("Password must be at least 8 characters long")
        form_layout.addRow("Password:", password_input)

        # Add form layout to main layout
        main_layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        save_button = QPushButton("Add User")
        save_button.setToolTip("Save user details")
        save_button.clicked.connect(
            lambda: self.validate_and_add_user(
                dialog, name_input.text(), role, email_input.text(), password_input.text(), role_dropdown
            )
        )

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        # Add buttons to main layout
        main_layout.addLayout(button_layout)

        dialog.setLayout(main_layout)
        dialog.exec_()

    def validate_and_add_user(self, dialog, name, role, email, password, role_dropdown=None):
        """Validate and add a new user."""
        if not name.strip():
            QMessageBox.warning(self, "Validation Error", "Name cannot be empty!")
            return
        if role_dropdown:
            role = role_dropdown.currentText()
        if not email.strip():
            QMessageBox.warning(self, "Validation Error", "Email cannot be empty!")
            return
        if not password.strip():
            QMessageBox.warning(self, "Validation Error", "Password cannot be empty!")
            return
        if len(password) < 8:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters long!")
            return

        # Generate a new user ID and add the user
        user_id = str(uuid.uuid4())
        self.add_new_user(dialog, user_id, name, role, email, password)

    def add_new_user(self, dialog, user_id, name, role, email,password):
        """Add a new user."""
        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return
        if self.db.get_num_users()==0:
            role="Admin"
        self.db.insert_new_user(id=user_id, name=name, role=role, email=email,password=password)
        self.refresh_table()
        dialog.close()
    def handle_cell_click(self, row, column):
        """Handle cell clicks."""
        if column == 2:
            current_role = self.table.item(row, column).text()
            new_role = "User" if current_role == "Admin" else "Admin"

            # Update the database
            user_id = self.table.item(row, 0).text()
            self.db.update_user_by_id(user_id, {"role": new_role})

            # Update the table display
            self.refresh_table()