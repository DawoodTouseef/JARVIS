import cv2
import base64
import uuid
import tempfile
import sounddevice as sd
import soundfile as sf
import numpy as np
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QMessageBox, QDateEdit, QGraphicsDropShadowEffect
)
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from utils.models.users import Users
import bcrypt

class OpenGLBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)
        glColor3f(0.2, 0.6, 1.0)
        glutSolidSphere(1, 50, 50)
        glFlush()

class SignupPage(QWidget):
    def __init__(self, switch_to_login):
        super().__init__()
        self.switch_to_login = switch_to_login
        self.setWindowTitle("Sign Up")
        self.setFixedSize(500, 750)

        layout = QVBoxLayout()
        self.db = Users
        self.opengl_background = OpenGLBackground(self)

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
        self.capture_photo_button.clicked.connect(self.capture_photo)

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

        # Background styling
        self.setStyleSheet("background-color: #121212; border-radius: 15px;")

        self.photo_path = None
        self.audio_path = None
        self.is_recording = False
        self.recording = None

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
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            if len(faces) == 0:
                QMessageBox.warning(self, "Upload Failed", "No face detected in the image!")
                return
            self.photo_path = file_path
            pixmap = QPixmap(file_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.photo_display.setPixmap(pixmap)

    def capture_photo(self):
        """Captures a photo and checks for a face before saving."""
        cap = cv2.VideoCapture(0)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

        while True:
            ret, frame = cap.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                if len(faces) > 0:
                    temp_photo_path = os.path.join(tempfile.gettempdir(), "captured_photo.jpg")
                    cv2.imwrite(temp_photo_path, frame)
                    self.photo_path = temp_photo_path
                    pixmap = QPixmap(temp_photo_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.photo_display.setPixmap(pixmap)
                    break
        cap.release()

    def upload_audio(self):
        """Allows user to upload an audio file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            self.audio_path = file_path
            self.audio_path_display.setText(file_path)

    def toggle_recording(self):
        """Start/Stop recording audio."""
        if self.is_recording:
            self.record_audio_button.setText("Record Audio")
            sd.stop()
            temp_audio_path = os.path.join(tempfile.gettempdir(), "recorded_audio.wav")
            sf.write(temp_audio_path, self.recording, 44100)
            self.audio_path = temp_audio_path
            self.audio_path_display.setText(temp_audio_path)
        else:
            self.record_audio_button.setText("Stop Recording")
            self.recording = sd.rec(int(60 * 44100), samplerate=44100, channels=2, dtype='int16')
        self.is_recording = not self.is_recording

    def signup(self):
        """Validate and register a new user."""
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        dob = self.dob_input.date().toString("yyyy-MM-dd")

        if not username or not email or not password or not dob:
            QMessageBox.warning(self, "Sign Up Failed", "All fields are required!")
            return

        if not self.photo_path:
            QMessageBox.warning(self, "Sign Up Failed", "Please upload a profile photo!")
            return

        if not self.audio_path:
            QMessageBox.warning(self, "Sign Up Failed", "Please upload an audio sample!")
            return

        email_db = self.db.get_user_by_email(email=email)
        if email_db:
            QMessageBox.warning(self, "Sign Up Failed", "Email already exists!")
            return

        role = "Admin" if self.db.get_num_users() == 0 else "User"
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_password_str = base64.b64encode(hashed_password).decode('utf-8')

        self.db.insert_new_user(
            id=str(uuid.uuid4()),
            name=username,
            email=email,
            password=hashed_password_str,
            role=role,
            dob=dob,
            profile_image_url=self.photo_path,
            user_voice=self.audio_path
        )

        QMessageBox.information(self, "Sign Up Success", "Account created successfully!")
        self.switch_to_login()
