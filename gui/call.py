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
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QListWidget, QMessageBox, QStackedWidget, QWidget, QComboBox, QCheckBox
)
from PyQt5.QtGui import QFont
from twilio.rest import Client
import datetime
from jarvis_integration.models.contact import Contact,PhoneNumber,TwilioSettings,CallHistory
from jarvis_integration.internals.db import get_db


class CallDialerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Call Dialer")
        self.setGeometry(100, 100, 400, 700)

        # Stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: white;
            }
            QLabel {
                font-size: 16px;
            }
            QPushButton {
                background-color: #34495e;
                color: white;
                font-size: 14px;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1abc9c;
            }
            QListWidget {
                background-color: #34495e;
                border: 1px solid #1abc9c;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #34495e;
                border: 1px solid #1abc9c;
                border-radius: 8px;
                color: white;
                padding: 5px;
            }
            QCheckBox {
                font-size: 14px;
            }
            QComboBox {
                background-color: #34495e;
                color: white;
                border: 1px solid #1abc9c;
                border-radius: 8px;
                padding: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #34495e;
                selection-background-color: #1abc9c;
            }
        """)

        self.twilio_settings = self.load_twilio_settings()

        # Main Layout with StackedWidget
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        self.contact_page = QWidget()
        self.history_page = QWidget()
        self.contact_detail_page = QWidget()

        self.setup_contact_page()
        self.setup_history_page()
        self.setup_contact_detail_page()

        self.stack.addWidget(self.contact_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.contact_detail_page)

        # Navigation Buttons
        navigation_layout = QHBoxLayout()
        self.contact_button = QPushButton("Contacts")
        self.contact_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.contact_page))
        self.history_button = QPushButton("History")
        self.history_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.history_page))
        navigation_layout.addWidget(self.contact_button)
        navigation_layout.addWidget(self.history_button)
        navigation_layout.setSpacing(10)

        # Add navigation layout to main layout
        self.layout.addLayout(navigation_layout)

        # Load Initial Data
        self.load_contacts()
        self.load_history()

    def setup_contact_page(self):
        layout = QVBoxLayout(self.contact_page)
        title_label = QLabel("Contacts")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title_label)

        self.contact_list_widget = QListWidget()
        self.contact_list_widget.itemClicked.connect(self.show_contact_detail)
        layout.addWidget(self.contact_list_widget)

        add_contact_button = QPushButton("Add Contact")
        add_contact_button.clicked.connect(self.create_contact)
        layout.addWidget(add_contact_button)

    def setup_history_page(self):
        layout = QVBoxLayout(self.history_page)
        title_label = QLabel("Call History")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title_label)

        self.history_filter = QComboBox()
        self.history_filter.addItems(["All", "Missed", "Outgoing", "Incoming"])
        self.history_filter.currentIndexChanged.connect(self.load_history)
        layout.addWidget(self.history_filter)

        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search History...")
        self.history_search.textChanged.connect(self.load_history)
        layout.addWidget(self.history_search)

        self.history_list_widget = QListWidget()
        layout.addWidget(self.history_list_widget)

    def setup_contact_detail_page(self):
        layout = QVBoxLayout(self.contact_detail_page)
        self.detail_name_label = QLabel("Name:")
        self.detail_name_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.detail_name_label)

        self.detail_phone_list = QListWidget()
        self.detail_phone_list.itemClicked.connect(self.make_call)
        layout.addWidget(self.detail_phone_list)

        self.favorite_checkbox = QCheckBox("Mark as Favorite")
        self.favorite_checkbox.stateChanged.connect(self.toggle_favorite)
        layout.addWidget(self.favorite_checkbox)

        edit_button = QPushButton("Edit Contact")
        edit_button.clicked.connect(self.edit_contact)
        layout.addWidget(edit_button)

        delete_button = QPushButton("Delete Contact")
        delete_button.clicked.connect(self.delete_contact)
        layout.addWidget(delete_button)

        back_button = QPushButton("Back to Contacts")
        back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.contact_page))
        layout.addWidget(back_button)

    def load_twilio_settings(self):
        with get_db() as db_session:
            settings = db_session.query(TwilioSettings).first()
        if settings:
            return {
                "account_sid": settings.account_sid,
                "auth_token": settings.auth_token,
                "phone_number": settings.phone_number,
            }
        return {"account_sid": "", "auth_token": "", "phone_number": ""}

    def load_contacts(self):
        self.contact_list_widget.clear()
        with get_db() as db_session:
            favorites = db_session.query(Contact).filter_by(is_favorite=True).all()
            others = db_session.query(Contact).filter_by(is_favorite=False).all()

        for contact in favorites + others:
            self.contact_list_widget.addItem(contact.name)

    def load_history(self):
        self.history_list_widget.clear()
        filter_type = self.history_filter.currentText()
        search_query = self.history_search.text().strip().lower()
        with get_db() as db_session:
            histories = db_session.query(CallHistory).all()
        for history in histories:
            if filter_type != "All" and history.call_type != filter_type:
                continue
            if search_query and search_query not in history.contact_name.lower() and search_query not in history.contact_number:
                continue
            self.history_list_widget.addItem(
                f"{history.contact_name or 'Unknown'} ({history.contact_number}) - {history.call_type} - {history.timestamp} - Duration: {history.duration or 'N/A'}"
            )

    def create_contact(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Contact")
        layout = QVBoxLayout(dialog)

        name_label = QLabel("Name:")
        name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        phone_label = QLabel("Phone Number:")
        phone_input = QLineEdit()
        layout.addWidget(phone_label)
        layout.addWidget(phone_input)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_contact(dialog, name_input.text(), phone_input.text()))
        layout.addWidget(save_button)
        dialog.exec_()

    def save_contact(self, dialog, name, phone):
        if not name or not phone:
            QMessageBox.warning(self, "Error", "Name and Phone Number are required!")
            return
        new_contact = Contact(name=name, phone_numbers=[PhoneNumber(number=phone)])
        with get_db() as db_session:
            db_session.add(new_contact)
            db_session.commit()
        dialog.accept()
        self.load_contacts()

    def show_contact_detail(self, item):
        contact_name = item.text()
        with get_db() as db_session:
            contact = db_session.query(Contact).filter_by(name=contact_name).first()
        if contact:
            self.detail_name_label.setText(f"Name: {contact.name}")
            self.favorite_checkbox.setChecked(contact.is_favorite)
            self.detail_phone_list.clear()
            for phone in contact.phone_numbers:
                self.detail_phone_list.addItem(phone.number)
            self.stack.setCurrentWidget(self.contact_detail_page)

    def toggle_favorite(self):
        contact_name = self.detail_name_label.text().replace("Name: ", "")
        with get_db() as db_session:
            contact = db_session.query(Contact).filter_by(name=contact_name).first()
        if contact:
            contact.is_favorite = self.favorite_checkbox.isChecked()
            db_session.commit()
            self.load_contacts()

    def delete_contact(self):
        contact_name = self.detail_name_label.text().replace("Name: ", "")
        with get_db() as db:
            contact = db.query(Contact).filter_by(name=contact_name).first()
        if contact:
            with get_db() as db:
                db.delete(contact)
                db.commit()
            self.stack.setCurrentWidget(self.contact_page)
            self.load_contacts()

    def edit_contact(self):
        current_name = self.detail_name_label.text().replace("Name: ", "")
        with get_db() as db:
            contact = db.query(Contact).filter_by(name=current_name).first()
        if not contact:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Contact")
        layout = QVBoxLayout(dialog)

        name_label = QLabel("Name:")
        name_input = QLineEdit(contact.name)
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        for phone in contact.phone_numbers:
            phone_input = QLineEdit(phone.number)
            layout.addWidget(phone_input)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.update_contact(dialog, contact, name_input))
        layout.addWidget(save_button)
        dialog.exec_()

    def update_contact(self, dialog, contact, name_input):
        contact.name = name_input.text()
        with get_db() as db:
            db.commit()
        dialog.accept()
        self.load_contacts()

    def make_call(self, phone):
        try:
            self.client = Client(self.twilio_settings["account_sid"], self.twilio_settings["auth_token"])
            start_time = datetime.datetime.now()
            self.call = self.client.calls.create(
                to=phone,
                from_=self.twilio_settings["phone_number"],
                record=True,
                twiml=f"<Response><Say>Calling</Say></Response>"
            )
            QMessageBox.information(self, "Call Started", f"Calling {phone}...\nCall SID: {self.call.sid}")

            self.log_call(phone, "Outgoing", duration=str(datetime.datetime.now() - start_time))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to make call: {e}")

    def log_call(self, phone, call_type, duration="Unknown"):
        history = CallHistory(
            contact_number=phone,
            call_type=call_type,
            duration=duration,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        with get_db() as db:
            db.add(history)
            db.commit()
        self.load_history()

    def hang_up_call(self):
        QMessageBox.information(self, "Hang Up", "Call ended.")
