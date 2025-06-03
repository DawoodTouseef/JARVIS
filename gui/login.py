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
import bcrypt

from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer, QRegExp
from PyQt5.QtGui import QColor, QFont, QRegExpValidator, QLinearGradient, QPainter,QKeySequence
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect, QMessageBox
)
from jarvis_integration.models.users import Users
from config import  SessionManager,loggers


logger = loggers['LOGIN']

class AnimatedLoginPage(QWidget):
    def __init__(self, switch_to_main, switch_to_signup):
        super().__init__()
        self.switch_to_main = switch_to_main
        self.switch_to_signup = switch_to_signup
        self.setWindowTitle("Login")
        self.setFixedSize(500, 600)
        self.db = Users

        # UI Components
        self.title = QLabel("🔒 Welcome Back")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Arial", 24, QFont.Bold))
        self.title.setStyleSheet("color: white;")

        # 3D Shadow Effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(30)
        self.shadow.setColor(QColor(0, 120, 255))
        self.shadow.setOffset(0, 0)
        self.title.setGraphicsEffect(self.shadow)

        # Email Input
        self.email_label = QLabel("📧 Email:")
        self.email_label.setStyleSheet("color: white; font-size: 14px;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setValidator(QRegExpValidator(QRegExp(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"), self))
        self.email_input.textChanged.connect(self.validate_input)
        self.email_input.setStyleSheet(self._input_style())

        # Password Input
        self.password_label = QLabel("🔑 Password:")
        self.password_label.setStyleSheet("color: white; font-size: 14px;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.textChanged.connect(self.password_strength)
        self.password_input.setStyleSheet(self._input_style())

        # Password Strength Meter
        self.password_strength_label = QLabel("")
        self.password_strength_label.setStyleSheet("color: white; font-size: 12px;")

        # Toggle Password Visibility
        self.toggle_password_button = QPushButton("👁")
        self.toggle_password_button.setFixedSize(30, 30)
        self.toggle_password_button.setCheckable(True)
        self.toggle_password_button.setStyleSheet(self._button_style("#444"))
        self.toggle_password_button.clicked.connect(self.toggle_password_visibility)

        password_layout = QHBoxLayout()
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.toggle_password_button)

        # Login Button
        self.login_button = QPushButton("🚀 Login")
        self.login_button.setStyleSheet(self._button_style())
        self.login_button.clicked.connect(self.login)
        self.login_button.setShortcut(QKeySequence(Qt.Key.Key_Enter))

        # Sign Up Button
        self.signup_button = QPushButton("📝 Sign Up")
        self.signup_button.setStyleSheet(self._button_style("lightblue"))
        self.signup_button.clicked.connect(self.switch_to_signup)

        # Layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.title)
        self.layout.addSpacing(20)
        self.layout.addWidget(self.email_label)
        self.layout.addWidget(self.email_input)
        self.layout.addWidget(self.password_label)
        self.layout.addLayout(password_layout)
        self.layout.addWidget(self.password_strength_label)
        self.layout.addSpacing(20)
        self.layout.addWidget(self.login_button)
        self.layout.addWidget(self.signup_button)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(self.layout)

        # Background and Animation
        self._init_animation()

    def paintEvent(self, event):
        """Render a gradient background."""
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(18, 18, 18))
        gradient.setColorAt(1, QColor(50, 50, 80))
        painter.fillRect(self.rect(), gradient)

    def _init_animation(self):
        """Initialize animations for UI components."""
        self.setStyleSheet("background-color: #121212; border-radius: 15px;")
        self.title_animation = QPropertyAnimation(self.title, b"geometry")
        self.title_animation.setDuration(1000)
        title_width = self.title.sizeHint().width()
        title_height = self.title.sizeHint().height()
        self.title_animation.setStartValue(QRect((self.width() - title_width) // 2, -title_height, title_width, title_height))
        self.title_animation.setEndValue(QRect((self.width() - title_width) // 2, 20, title_width, title_height))
        self.title_animation.start()

    def _input_style(self):
        """Apply input styling."""
        return (
            "background-color: #1f1f1f; color: white; border: 1px solid #444;"
            "border-radius: 5px; padding: 8px; font-size: 14px;"
        )

    def _button_style(self, color="dodgerblue"):
        """Apply button styling."""
        return (
            f"background-color: {color}; color: white; border-radius: 8px; padding: 10px; font-size: 14px;"
            "font-weight: bold;"
        )

    def validate_input(self):
        """Validate email format."""
        if self.email_input.hasAcceptableInput():
            self.email_input.setStyleSheet(self._input_style() + "border: 2px solid lime;")
        else:
            self.email_input.setStyleSheet(self._input_style() + "border: 2px solid red;")

    def password_strength(self):
        """Check password strength and provide feedback."""
        password = self.password_input.text()
        strength = "Weak"
        requirements = []
        if len(password) > 8:
            requirements.append("Length > 8")
        if any(c.isdigit() for c in password):
            requirements.append("Contains digit")
        if any(c.isupper() for c in password):
            requirements.append("Contains uppercase")
        if len(requirements) == 3:
            strength = "Strong"
        elif len(requirements) >= 2:
            strength = "Moderate"

        self.password_strength_label.setText(f"Password Strength: {strength} ({', '.join(requirements)})")

    def toggle_password_visibility(self):
        """Toggle password visibility."""
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_password_button.setText("👁‍🗨")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_password_button.setText("👁")

    def login(self):
        """Perform login validation and update session."""
        email = self.email_input.text().strip().lower()
        password = self.password_input.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "⚠ Login Failed", "Email and password are required!")
            logger.warning("Login attempt with empty email or password")
            return

        try:
            user = self.db.get_user_by_email(email=email)
            if not user:
                QMessageBox.warning(self, "⚠ Login Failed", "Invalid email or password!")
                logger.warning(f"Login failed: No user found for email {email}")
                return

            if bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
                # Update last_active_at
                self.db.update_user_last_active_by_id(user.id)
                # Create session
                session = SessionManager()
                session.create_session(email)
                logger.info(f"Successful login for user {email}")

                self._animate_success()
                QTimer.singleShot(1000, self.switch_to_main)
            else:
                QMessageBox.warning(self, "⚠ Login Failed", "Invalid email or password!")
                logger.warning(f"Login failed: Incorrect password for email {email}")
        except Exception as e:
            QMessageBox.critical(self, "⚠ Login Error", f"An error occurred: {str(e)}")
            logger.error(f"Login error for email {email}: {str(e)}")

    def _animate_success(self):
        """Animate successful login."""
        self.title.setText("✅ Login Successful!")
        self.title.setStyleSheet("color: limegreen;")
        self.title_animation.setStartValue(self.title.geometry())
        title_width = self.title.sizeHint().width()
        title_height = self.title.sizeHint().height()
        self.title_animation.setEndValue(QRect((self.width() - title_width) // 2, self.height() // 2, title_width, title_height))
        self.title_animation.start()