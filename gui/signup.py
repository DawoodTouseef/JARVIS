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
import cv2
import uuid
import os
import shutil
import sounddevice as sd
import soundfile as sf
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QColor, QLinearGradient, QPainter
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QMessageBox, QDateEdit, QGraphicsDropShadowEffect
)
from jarvis_integration.models.users import Users
import bcrypt
from config import JARVIS_DIR

class CameraThread(QThread):
    photoCaptured = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.error.emit("Failed to open camera!")
            return

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        timeout = 30  # seconds
        start_time = cv2.getTickCount() / cv2.getTickFrequency()

        while self.running:
            ret, frame = cap.read()
            if not ret:
                self.error.emit("Failed to capture frame!")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            if len(faces) > 0:
                temp_photo_path = os.path.join(JARVIS_DIR, "data", "users", f"photo_{uuid.uuid4()}.jpg")
                os.makedirs(os.path.dirname(temp_photo_path), exist_ok=True)
                cv2.imwrite(temp_photo_path, frame)
                self.photoCaptured.emit(temp_photo_path)
                break

            if (cv2.getTickCount() / cv2.getTickFrequency() - start_time) > timeout:
                self.error.emit("No face detected within timeout!")
                break

        cap.release()

class SignupPage(QWidget):
    def __init__(self, switch_to_login):
        super().__init__()
        self.switch_to_login = switch_to_login
        self.setWindowTitle("Sign Up")
        self.setFixedSize(500, 750)

        layout = QVBoxLayout()
        self.db = Users

        # Title
        self.title = QLabel("Create an Account")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Arial", 22, QFont.Bold))
        self.title.setStyleSheet("color: white;")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 120, 255))
        self.title.setGraphicsEffect(shadow)

        # Username Input
        self.username_label = QLabel("Username:")
        self.username_label.setStyleSheet("color: white;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet(self._input_style())

        # Email Input
        self.email_label = QLabel("Email:")
        self.email_label.setStyleSheet("color: white;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setStyleSheet(self._input_style())

        # Date of Birth Input
        self.dob_label = QLabel("Date of Birth:")
        self.dob_label.setStyleSheet("color: white;")
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setStyleSheet(self._input_style())

        # Password Input
        self.password_label = QLabel("Password:")
        self.password_label.setStyleSheet("color: white;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter a password")
        self.password_input.setStyleSheet(self._input_style())

        # Toggle Password Visibility Button
        self.toggle_password_button = QPushButton("👁")
        self.toggle_password_button.setFixedSize(30, 30)
        self.toggle_password_button.setCheckable(True)
        self.toggle_password_button.setStyleSheet(self._button_style("#444"))
        self.toggle_password_button.clicked.connect(self.toggle_password_visibility)

        password_layout = QHBoxLayout()
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.toggle_password_button)

        # Photo Upload or Capture
        self.photo_label = QLabel("Profile Photo:")
        self.photo_label.setStyleSheet("color: white;")
        self.photo_display = QLabel()
        self.photo_display.setFixedSize(100, 100)
        self.photo_display.setStyleSheet("border: 1px solid white; background-color: #333;")
        self.upload_photo_button = QPushButton("Upload Photo")
        self.upload_photo_button.setStyleSheet(self._button_style())
        self.upload_photo_button.clicked.connect(self.upload_photo)

        self.capture_photo_button = QPushButton("Capture Photo")
        self.capture_photo_button.setStyleSheet(self._button_style())
        self.capture_photo_button.clicked.connect(self.start_capture_photo)

        photo_layout = QHBoxLayout()
        photo_layout.addWidget(self.photo_display)
        photo_layout.addWidget(self.upload_photo_button)
        photo_layout.addWidget(self.capture_photo_button)

        # Audio Upload or Record
        self.audio_label = QLabel("Audio Sample:")
        self.audio_label.setStyleSheet("color: white;")
        self.audio_path_display = QLineEdit()
        self.audio_path_display.setReadOnly(True)
        self.audio_path_display.setStyleSheet(self._input_style())
        self.upload_audio_button = QPushButton("Upload Audio")
        self.upload_audio_button.setStyleSheet(self._button_style())
        self.upload_audio_button.clicked.connect(self.upload_audio)

        self.record_audio_button = QPushButton("Record Audio")
        self.record_audio_button.setStyleSheet(self._button_style())
        self.record_audio_button.setCheckable(True)
        self.record_audio_button.clicked.connect(self.toggle_recording)

        audio_layout = QHBoxLayout()
        audio_layout.addWidget(self.audio_path_display)
        audio_layout.addWidget(self.upload_audio_button)
        audio_layout.addWidget(self.record_audio_button)

        # Signup & Back Buttons
        self.signup_button = QPushButton("Sign Up")
        self.signup_button.setStyleSheet(self._button_style())
        self.signup_button.clicked.connect(self.signup)

        self.back_button = QPushButton("Back to Login")
        self.back_button.setStyleSheet(self._button_style("lightblue"))
        self.back_button.clicked.connect(self.switch_to_login)

        # Arrange Layout
        layout.addWidget(self.title)
        layout.addSpacing(10)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.email_label)
        layout.addWidget(self.email_input)
        layout.addWidget(self.dob_label)
        layout.addWidget(self.dob_input)
        layout.addWidget(self.password_label)
        layout.addLayout(password_layout)
        layout.addWidget(self.photo_label)
        layout.addLayout(photo_layout)
        layout.addWidget(self.audio_label)
        layout.addLayout(audio_layout)
        layout.addSpacing(20)
        layout.addWidget(self.signup_button)
        layout.addWidget(self.back_button)
        layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(layout)

        # Gradient background
        self.setStyleSheet("background-color: #121212; border-radius: 15px;")

        self.photo_path = None
        self.audio_path = None
        self.is_recording = False
        self.recording = None
        self.camera_thread = None

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(18, 18, 18))
        gradient.setColorAt(1, QColor(50, 50, 80))
        painter.fillRect(self.rect(), gradient)

    def _input_style(self):
        return (
            "background-color: #1f1f1f; color: white; border: 1px solid #444;"
            "border-radius: 5px; padding: 8px;"
        )

    def _button_style(self, color="dodgerblue"):
        return (
            f"background-color: {color}; color: white; border-radius: 5px; padding: 10px;"
            "font-weight: bold;"
        )

    def toggle_password_visibility(self):
        """Toggles password visibility."""
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_password_button.setText("👁‍🗨")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_password_button.setText("👁")

    def upload_photo(self):
        """Uploads a photo and ensures a face is detected before saving."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Photo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            img = cv2.imread(file_path)
            if img is None:
                QMessageBox.warning(self, "Upload Failed", "Invalid image file!")
                return
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            if len(faces) == 0:
                QMessageBox.warning(self, "Upload Failed", "No face detected in the image!")
                return
            # Copy to permanent location
            photo_path = os.path.join(JARVIS_DIR, "data", "users", f"photo_{uuid.uuid4()}.jpg")
            os.makedirs(os.path.dirname(photo_path), exist_ok=True)
            shutil.copyfile(file_path, photo_path)
            self.photo_path = photo_path
            pixmap = QPixmap(photo_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.photo_display.setPixmap(pixmap)

    def start_capture_photo(self):
        """Start capturing a photo in a separate thread."""
        if self.camera_thread and self.camera_thread.isRunning():
            QMessageBox.warning(self, "Capture Failed", "Photo capture already in progress!")
            return

        self.camera_thread = CameraThread()
        self.camera_thread.photoCaptured.connect(self.on_photo_captured)
        self.camera_thread.error.connect(self.on_capture_error)
        self.camera_thread.start()

    def on_photo_captured(self, photo_path):
        """Handle successful photo capture."""
        self.photo_path = photo_path
        pixmap = QPixmap(photo_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.photo_display.setPixmap(pixmap)
        self.camera_thread.running = False
        self.camera_thread = None

    def on_capture_error(self, error_message):
        """Handle photo capture errors."""
        QMessageBox.warning(self, "Capture Failed", error_message)
        self.camera_thread.running = False
        self.camera_thread = None

    def upload_audio(self):
        """Allows user to upload an audio file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            audio_path = os.path.join(JARVIS_DIR, "data", "users", f"audio_{uuid.uuid4()}{os.path.splitext(file_path)[1]}")
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            shutil.copyfile(file_path, audio_path)
            self.audio_path = audio_path
            self.audio_path_display.setText(audio_path)

    def toggle_recording(self):
        """Start/Stop recording audio."""
        try:
            if self.is_recording:
                self.record_audio_button.setText("Record Audio")
                sd.stop()
                if self.recording is not None:
                    audio_path = os.path.join(JARVIS_DIR, "data", "users", f"audio_{uuid.uuid4()}.wav")
                    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                    sf.write(audio_path, self.recording, 44100)
                    self.audio_path = audio_path
                    self.audio_path_display.setText(audio_path)
                self.recording = None
            else:
                self.record_audio_button.setText("Stop Recording")
                self.recording = sd.rec(int(60 * 44100), samplerate=44100, channels=2, dtype='int16')
            self.is_recording = not self.is_recording
        except Exception as e:
            QMessageBox.warning(self, "Recording Failed", f"Error during audio recording: {e}")
            self.is_recording = False
            self.record_audio_button.setText("Record Audio")
            self.recording = None

    def signup(self):
        """Validate and register a new user."""
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        dob = self.dob_input.date().toString("yyyy-MM-dd")

        # Input validation
        if not username or not email or not password or not dob:
            QMessageBox.warning(self, "Sign Up Failed", "All fields are required!")
            return

        if not self.photo_path:
            QMessageBox.warning(self, "Sign Up Failed", "Please upload or capture a profile photo!")
            return

        if not self.audio_path:
            QMessageBox.warning(self, "Sign Up Failed", "Please upload or record an audio sample!")
            return

        # Email format validation
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Sign Up Failed", "Invalid email format!")
            return

        # Password length validation
        if len(password) < 8:
            QMessageBox.warning(self, "Sign Up Failed", "Password must be at least 8 characters long!")
            return

        try:
            # Check if email exists
            email_db = self.db.get_user_by_email(email=email)
            if email_db:
                QMessageBox.warning(self, "Sign Up Failed", "Email already exists!")
                return

            # Determine role
            role = "Admin" if self.db.get_num_users() == 0 else "User"

            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Insert user
            self.db.insert_new_user(
                id=str(uuid.uuid4()),
                name=username,
                email=email,
                password=hashed_password,
                role=role,
                dob=dob,
                profile_image_url=self.photo_path,
                user_voice=self.audio_path
            )

            QMessageBox.information(self, "Sign Up Success", "Account created successfully!")
            self.switch_to_login()

        except Exception as e:
            QMessageBox.critical(self, "Sign Up Failed", f"Error creating account: {e}")