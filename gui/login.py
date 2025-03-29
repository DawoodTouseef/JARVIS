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
import bcrypt
import base64

from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer,QRegExp
from PyQt5.QtGui import QColor, QFont, QRegExpValidator,QPixmap
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect, QMessageBox
)
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from utils.models.users import Users
from config import SESSION_PATH
import math


class OpenGLBackground(QWidget):
    """Creates a dynamic OpenGL animated 3D Cube."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(20)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)

    def paintGL(self):
        """Render a rotating 3D cube with neon glow."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        glRotatef(self.angle, 1, 1, 1)
        self.angle += 1  # Rotate cube

        glBegin(GL_QUADS)
        glColor3f(0.2, 0.7, 1.0)
        for i in range(6):
            for j in range(4):
                glVertex3f(math.cos(j * math.pi / 2), math.sin(j * math.pi / 2), (-1) ** i)
        glEnd()

        glFlush()

class AnimatedLoginPage(QWidget):
    def __init__(self, switch_to_main, switch_to_signup):
        super().__init__()
        self.switch_to_main = switch_to_main
        self.switch_to_signup = switch_to_signup
        self.setWindowTitle("Login")
        self.setFixedSize(500, 600)
        self.db = Users

        # OpenGL Background
        self.opengl_background = OpenGLBackground(self)

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
        self.email_input.setValidator(QRegExpValidator(QRegExp(r"^[\w\.-]+@[\w\.-]+\.\w+$"), self))  # Validate email
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

        # Background Animation
        self._init_animation()

    def _init_animation(self):
        """Initialize animations for UI components."""
        self.setStyleSheet("background-color: #121212; border-radius: 15px;")
        self.title_animation = QPropertyAnimation(self.title, b"geometry")
        self.title_animation.setDuration(1000)
        self.title_animation.setStartValue(QRect(50, -50, 300, 50))
        self.title_animation.setEndValue(QRect(50, 20, 300, 50))
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
            "font-weight: bold; transition: 0.3s;"
            "box-shadow: 3px 3px 10px rgba(0, 150, 255, 0.5);"
        )

    def validate_input(self):
        """Checks email format."""
        if self.email_input.hasAcceptableInput():
            self.email_input.setStyleSheet(self._input_style() + "border: 2px solid lime;")
        else:
            self.email_input.setStyleSheet(self._input_style() + "border: 2px solid red;")

    def password_strength(self):
        """Checks password strength."""
        password = self.password_input.text()
        strength = "Weak"
        if len(password) > 8 and any(c.isdigit() for c in password) and any(c.isupper() for c in password):
            strength = "Strong"
        elif len(password) > 5:
            strength = "Moderate"

        self.password_strength_label.setText(f"Password Strength: {strength}")


    def toggle_password_visibility(self):
        """Toggle password visibility."""
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_password_button.setText("👁‍🗨")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_password_button.setText("👁")

    def login(self):
        """Perform login validation."""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if email and password:
            user = self.db.get_user_by_email(email=email)
            if user:
                hashed_password_bytes = base64.b64decode(user.password)
                if bcrypt.checkpw(password.encode("utf-8"), hashed_password_bytes):
                    with open(os.path.join(SESSION_PATH, "session.json"), "w") as session_file:
                        json.dump({"email": email}, session_file)

                    self._animate_success()
                    QTimer.singleShot(1000, self.switch_to_main)
                    return

        QMessageBox.warning(self, "⚠ Login Failed", "Invalid email or password!")

    def _animate_success(self):
        """Animate successful login."""
        self.title.setText("✅ Login Successful!")
        self.title.setStyleSheet("color: limegreen;")
        self.title_animation.setStartValue(self.title.geometry())
        self.title_animation.setEndValue(QRect(50, 200, 300, 50))
        self.title_animation.start()
