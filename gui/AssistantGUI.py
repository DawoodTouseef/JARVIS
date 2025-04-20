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

from PyQt5.QtCore import QObject, QThread
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu,QAction,QStackedLayout
from config import JARVIS_DIR
from gui.user_setting import UserDialog
from gui.settings import AndroidSettingsDialog
from gui.AssistantOpenGLWidget import AssistantOpenGLWidget
from config import SESSION_PATH
import pyaudio
import pvporcupine
import json
import threading
from queue import Queue
from utils.models.users import Users
import struct
import speech_recognition as sr
from PyQt5.QtCore import  QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from gui.Home import HomeDialog
from gui.call import CallDialerDialog
from core.personal_assistant import YahooFinanceTool, DatabaseTool
from PyQt5.QtGui import QKeySequence
from gui.integrations import IntegrationsDialog
from PyQt5.QtCore import  pyqtProperty, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QBrush, QLinearGradient, QFont
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox
)
import os
from config import  loggers

import numpy as np


import cv2
from PyQt5.QtCore import Qt
from gui.Objects.AgentWorker import AgentWorker
from gui.Objects.wakeword import WakeWordWorker
from gui.Objects.SpeechRecognition import SpeechRecognitionWorker
from gui.Objects.AlertChecker import AlertCheck
from gui.Objects.TTSWorker import TTSWorker
from gui.Objects.Consciousness import ConsciousnessWorker
from gui.ImagePreview import ImagePreviewDialog
from gui.secuirty_dashboard import SecurityDashboard

log = loggers["GUI"]

class HoverButton(QPushButton):
    """Button with hover animations."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(140, 45)
        self.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #333;
            }
            QPushButton:hover {
                background-color: #00cc99;
                color: black;
            }
        """)

class AnimatedButton(QPushButton):
    """Custom Button with Moving Light Border Effect."""

    def __init__(self, icon_path, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(icon_path))
        self.setIconSize(self.size())
        self.setStyleSheet(
            """
            QPushButton {
                /*background-color: rgba(0, 0, 0, 0);   Fully transparent background */
                border: 2px solid transparent;
                border-radius: 30px;  /* Circular button */
            }
            QPushButton:hover {
                border: 2px solid rgba(255, 255, 255, 0.5); /* Semi-transparent on hover */
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.1);  /* Subtle press effect */
            }
            """
        )
        self.light_position = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_light_position)
        self.animation_timer.start(50)  # Adjust for speed of light movement

    def update_light_position(self):
        """Update light position for moving border."""
        self.light_position += 1
        if self.light_position >= 360:
            self.light_position = 0
        self.update()

    def paintEvent(self, event):
        """Custom painting for the moving light effect."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(self.rect().center(), self.rect().topLeft())
        gradient.setColorAt(0, QColor(0, 191, 255, 150))  # Soft blue
        gradient.setColorAt(1, QColor(255, 255, 255, 0))  # Transparent

        brush = QBrush(gradient)
        painter.setBrush(brush)

        angle = self.light_position
        painter.drawEllipse(self.rect().adjusted(3, 3, -3, -3))  # Adjust for the border
        painter.rotate(angle)

class AnimatedLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Arial", 18, QFont.Bold))
        self.setStyleSheet("color: rgba(10, 10, 10, 0.0);")  # Initially transparent
        self._opacity = 0.0

        # Fade-in Animation
        self.fade_in_animation = QPropertyAnimation(self, b"opacity")
        self.fade_in_animation.setDuration(1000)  # 1 second
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)

        # Fade-out Animation
        self.fade_out_animation = QPropertyAnimation(self, b"opacity")
        self.fade_out_animation.setDuration(1000)  # 1 second
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)

    def start_fade_animation(self, text):
        """Set text and start the fade-in and fade-out animation."""
        self.setText(text)
        self.fade_in_animation.start()
        self.fade_in_animation.finished.connect(self.fade_out_animation.start)

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, value):
        """Update opacity effect."""
        self._opacity = value
        self.setStyleSheet(f"color: rgba(10, 10, 10, {value});")

    opacity = pyqtProperty(float, get_opacity, set_opacity)

# Main Window
class AssistantGUI(QMainWindow):
    def __init__(self, login_page):
        super().__init__()
        self.setGeometry(100, 100, 800, 800)
        self.setWindowTitle("J.A.R.V.I.S.")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool)  # Changed to OnTop for usability
        self.recognition_running = False
        self.stop_recognition = threading.Event()
        self.login_page = login_page
        self.porcupine = None
        self.audio_stream = None
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.init_ui()
        self.load_wake_word_configuration()

        self.text_label = AnimatedLabel(self)
        self.text_label.setGeometry(10, 700, 780, 40)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("color: rgba(10, 10, 10, 0.9); font-size: 18px;")
        self.text_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.text_label.start_fade_animation("Hello, I am JARVIS")

        self.security_dashboard = SecurityDashboard(self)
        self.security_dashboard.setGeometry(20, 150, 610, 200)

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon("icon.png"))  # Replace with your icon path
        self.tray.setVisible(True)
        self.tray_menu = QMenu()

        # Add an exit option
        exit_action = QAction("Exit", self.tray_menu)
        exit_action.triggered.connect(self.exit_application)
        self.tray_menu.addAction(exit_action)

        self.tray.setContextMenu(self.tray_menu)

        if self.audio_stream is not None:
            self.wake_word_thread = QThread()
            self.wake_word_worker = WakeWordWorker(self.porcupine, self.audio_stream, self.stop_recognition)
            self.wake_word_worker.moveToThread(self.wake_word_thread)
            self.wake_word_worker.wake_word_detected.connect(self.on_wake_word_detected)
            self.wake_word_worker.error_signal.connect(self.display_error)
            self.wake_word_thread.started.connect(self.wake_word_worker.run)
            self.wake_word_thread.start()

        self.speech_thread = QThread()
        self.speech_worker = SpeechRecognitionWorker(self.recognizer, self.microphone, self.stop_recognition)
        self.speech_worker.moveToThread(self.speech_thread)
        self.speech_worker.transcription_signal.connect(self.start_agent_processing)
        self.speech_worker.listen_signal.connect(self.display_error)
        self.speech_worker.error_signal.connect(self.display_error)
        self.speech_thread.started.connect(self.speech_worker.run)

        self.agent_thread = QThread()
        self.agent_worker = AgentWorker()
        self.agent_worker.moveToThread(self.agent_thread)
        self.agent_worker.response_signal.connect(self.start_tts)
        self.agent_thread.started.connect(self.agent_worker.run)
        # Note: started signal not connected directly to run due to parameter issue

        self.tts_thread = QThread()
        self.tts_worker = TTSWorker()
        self.tts_worker.moveToThread(self.tts_thread)
        self.tts_worker.finished_signal.connect(self.tts_finished)
        self.tts_thread.started.connect(self.tts_worker.run)
        # Note: started signal not connected directly to run due to parameter issue

        self.db_tool = DatabaseTool()
        self.yahoo_tool = YahooFinanceTool()

        # Set up the worker and thread
        self.alert_thread = QThread()
        self.alert_checker = AlertCheck(self.db_tool, self.yahoo_tool)
        self.alert_checker.moveToThread(self.alert_thread)

        # Connect signals
        self.alert_thread.started.connect(self.alert_checker.run)
        self.alert_checker.alert_triggered.connect(self.handle_alerts)

        # Start the thread
        self.alert_thread.start()

        # Consciousness Thread
        self.consciousness_thread = QThread()
        self.consciousness_worker = ConsciousnessWorker(self.stop_recognition)
        self.consciousness_worker.moveToThread(self.consciousness_thread)
        self.consciousness_worker.update_signal.connect(self.display_proactive_update)
        self.consciousness_worker.image_signal.connect(self.process_image_input)
        self.consciousness_thread.started.connect(self.consciousness_worker.run)

        # Start the thread
        self.consciousness_thread.start()


    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray.setVisible(True)
        tray_menu = QMenu()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_application)
        tray_menu.addAction(exit_action)
        self.tray.setContextMenu(tray_menu)

    def process_image_input(self, image_data):
        if not self.agent_thread.isRunning():
            self.agent_worker.set_input(image=image_data)
            self.agent_thread.start()
            self.text_label.setText("JARVIS: Analyzing visual input...")

    def display_proactive_update(self, update):
        self.text_label.setText(f"JARVIS: {update}")
        self.tts_worker.set_text(update)
        if not self.tts_thread.isRunning():
            self.tts_thread.start()

    def handle_alerts(self, alerts):
        # Show notification and play TTS
        self.start_tts("You have a new notification")
        for alert in alerts:
            self.tray.showMessage("J.A.R.V.I.S. Alert", alert, QSystemTrayIcon.Information, 5000)
            self.start_tts(alert)
            QThread.msleep(1000)  # Small delay to avoid overlapping TTS

    def exit_application(self):
        """Exits the application."""
        self.tray.hide()

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def display_error(self, error_message):
        """Display errors."""
        log.info(error_message)
        self.display_text(error_message)

    def load_wake_word_configuration(self):
        """Load configuration for wake word detection."""
        try:
            with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
                data = json.load(f)
            if "email" in data:
                user = Users.get_user_by_email(data["email"])
                if user and user.settings:
                    settings = json.loads(user.settings.json())
                    wakeword_config = settings.get("wakeword", {})
                    self.api_key = wakeword_config.get("api_key", "")
                    self.wake_word_engine = wakeword_config.get("wakeword_engine", "")
                    model_path = wakeword_config.get("model_path", "")

                    if "porcupine" in self.wake_word_engine and self.api_key:
                        self.initialize_porcupine(self.api_key, model_path)
        except Exception as e:
            log.info(f"Failed to load wake word configuration: {e}")

    def initialize_porcupine(self, api_key, model_path):
        """Initialize Porcupine with the provided API key and model path."""
        try:
            self.porcupine = pvporcupine.create(
                access_key=api_key,
                keyword_paths=[model_path] if model_path else None,
                keywords=["jarvis"] if not model_path else None,
            )
            self.audio_stream = pyaudio.PyAudio().open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.porcupine.sample_rate,
                input=True,
                frames_per_buffer=self.porcupine.frame_length,
            )
        except Exception as e:
            log.info(f"Failed to initialize Porcupine: {e}")
            self.porcupine = None

    def stop_interaction_animation(self):
        """Stop animation after interaction ends."""
        if self.gl_widget.animation_running:
            self.gl_widget.toggle_animation()
            self.record_button.setIcon(QIcon(os.path.join(JARVIS_DIR, "icons", "mic-off.svg")))

    def init_ui(self):
        """Initialize the main user interface with 3D transparent buttons and lighting effects."""
        # Central Widget and Layout
        central_widget = QWidget(self)
        layout = QVBoxLayout()

        # Stacked layout to switch between Assistant and Security Dashboards
        self.stacked_layout = QStackedLayout()

        self.gl_widget = AssistantOpenGLWidget(self)
        self.security_dashboard = SecurityDashboard(self)

        self.stacked_layout.addWidget(self.gl_widget)  # index 0
        self.stacked_layout.addWidget(self.security_dashboard)  # index 1

        # Current dashboard state
        self.current_view = "assistant"  # or "security"

        # Container for the stacked layout
        stacked_container = QWidget()
        stacked_container.setLayout(self.stacked_layout)

        layout.addWidget(stacked_container)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Transcription/Response Label
        self.text_label = AnimatedLabel(self)
        self.text_label.setGeometry(10, 700, 780, 40)
        self.text_label.setAlignment(Qt.AlignCenter)

        # Buttons Configuration
        button_config = [
            {
                "name": "record_button",
                "geometry": (20, 20, 60, 60),
                "icon": "mic-off.svg",
                "callback": self.record,
                "tooltip": "Start/Stop Recording",
                "key": QKeySequence(Qt.CTRL + Qt.Key.Key_M)
            },
            {
                "name": "integrations_button",
                "geometry": (100, 20, 60, 60),
                "icon": "system-integration.svg",
                "callback": self.change_color,
                "tooltip": "Integration",
                "key": QKeySequence(Qt.CTRL + Qt.Key.Key_C)
            },
            {
                "name": "settings_button",
                "geometry": (180, 20, 60, 60),
                "icon": "settings.svg",
                "callback": self.open_settings_dialog,
                "tooltip": "Open Settings",
                "key": QKeySequence(Qt.CTRL + Qt.Key.Key_S)
            },
            {
                "name": "users_button",
                "geometry": (260, 20, 60, 60),
                "icon": "user.svg",
                "callback": self.open_users_dialog,
                "tooltip": "Manage Users",
                "key": QKeySequence(Qt.CTRL + Qt.Key.Key_F1)
            },
            {
                "name": "home_button",
                "geometry": (340, 20, 60, 60),
                "icon": "home.svg",
                "callback": self.toggle_dashboard_view,  # <- switch between views
                "tooltip": "Toggle Dashboard View",
                "key": QKeySequence(Qt.CTRL + Qt.Key.Key_H)
            },
            {
                "name": "call_button",
                "geometry": (420, 20, 60, 60),
                "icon": "phone.svg",
                "callback": self.call_application,
                "tooltip": "Call Window",
                "key": QKeySequence(Qt.CTRL + Qt.Key.Key_P)
            },
            {
                "name": "close_button",
                "geometry": (500, 20, 60, 60),
                "icon": "close.svg",
                "callback": self.closeapplication,
                "tooltip": "Close Application",
                "key": QKeySequence(Qt.ALT + Qt.Key.Key_F4)
            },
        ]

        for config in button_config:
            icon_path = os.path.join(JARVIS_DIR, "icons", config["icon"])
            button = AnimatedButton(icon_path, self)
            button.setGeometry(*config["geometry"])
            button.clicked.connect(config["callback"])
            button.setShortcut(config['key'])
            button.setToolTip(f"{config.get('tooltip', '')} ({config['key'].toString()})")

            # Add moving light effect on hover
            shadow = QGraphicsDropShadowEffect()
            shadow.setColor(QColor(0, 191, 255))  # Blue shadow
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 0)
            button.setGraphicsEffect(shadow)

            setattr(self, config["name"], button)

        # Enable the window to be resized
        self.setFixedSize(650, 800)
        self.center_window()
        self.show()

    def toggle_dashboard_view(self):
        """Switch between Assistant and Security Dashboard using state."""
        if self.current_view == "assistant":
            self.stacked_layout.setCurrentIndex(1)
            self.current_view = "security"
        else:
            self.stacked_layout.setCurrentIndex(0)
            self.current_view = "assistant"


    def record(self):
        self.gl_widget.toggle_animation()
        if self.gl_widget.animation_running and not self.recognition_running:
            try:
                self.stop_recognition.clear()
                self.recognition_running = True
                mic_svg = os.path.join(JARVIS_DIR, "icons", "mic.svg")
                self.record_button.setIcon(QIcon(mic_svg))

                self.speech_thread.start()
            except Exception as e:
                self.display_error(f"Failed to start recording: {e}")
                self.recognition_running = False
        else:
            try:
                if self.speech_thread.isRunning():
                    self.stop_recognition.set()
                    self.recognition_running = False
                    mic_svg = os.path.join(JARVIS_DIR, "icons", "mic-off.svg")
                    self.record_button.setIcon(QIcon(mic_svg))
                    self.speech_thread.quit()
                    self.speech_thread.wait()
            except Exception as e:
                self.display_error(f"Failed to stop recording: {e}")

    def on_wake_word_detected(self):
        """Handle wake word detection."""
        log.info("Wake word detected!")
        self.start_animation()
        if not self.recognition_running:
            self.recognition_running = True
            self.wake_word_thread.quit()
            self.speech_thread.start()  # Start speech recognition

    def start_agent_processing(self, transcription):
        """Handle transcription results."""
        log.info(f"Transcription: {transcription}")
        self.display_text(f"You said: {transcription}")
        if not self.agent_thread.isRunning():
            print("Agent is started!")
            self.agent_worker.set_text(transcription)
            self.agent_thread.start()

    def start_tts(self, text):
        """Starts the TTS (Text-to-Speech) thread."""
        self.display_text(f"J.A.R.V.I.S.: {text}")
        self.tts_worker.set_text(text)
        if not self.tts_thread.isRunning():
            self.tts_thread.start()

    def tts_finished(self):
        """Handles completion of TTS playback."""
        if self.tts_thread.isRunning():
            self.tts_thread.quit()
            self.tts_thread.wait()
        if self.agent_thread.isRunning():
            self.agent_thread.quit()
            self.agent_thread.wait()
        if self.speech_thread.isRunning():
            self.speech_thread.quit()
            self.speech_thread.wait()
        self.stop_interaction_animation()

    def change_color(self):
        dialog = IntegrationsDialog(self)
        dialog.exec_()

    def get_user_face_from_database(self):
        from utils.models.users import Users
        import json
        import os  # Need to import os at the top

        session_path = os.path.join(SESSION_PATH, "session.json")
        try:
            with open(session_path, "r") as f:
                data = json.load(f)

            if "email" in data:
                users = Users.get_user_by_email(data['email'])
                return users.user_face
            else:
                raise ValueError("Email not found in session data")
        except FileNotFoundError:
            print("Session file not found")
            return None
        except json.JSONDecodeError:
            print("Invalid JSON in session file")
            return None

    def get_face(self):
        # Open the default camera (index 0)
        cap = cv2.VideoCapture(0)
        max_attempts = 3

        for attempt in range(max_attempts):
            if cap.isOpened():
                ret, frame = cap.read()

                if ret and frame is not None:
                    # Show the captured image
                    preview_dialog = ImagePreviewDialog(frame, self)
                    preview_dialog.show()

                    # Release camera before returning
                    cap.release()

                    # Return the numpy array
                    return np.array(frame)
                else:
                    QMessageBox.critical(
                        self,
                        "Camera Error",
                        f"Failed to capture frame, attempt {attempt + 1}/{max_attempts}"
                    )
                    log.critical(f"Failed to capture frame, attempt {attempt + 1}/{max_attempts}")
            else:
                QMessageBox.critical(
                    self,
                    "Camera Error",
                    f"Cannot open camera, attempt {attempt + 1}/{max_attempts}"
                )
                log.critical(f"Cannot open camera, attempt {attempt + 1}/{max_attempts}")
                cap.release()
                cap = cv2.VideoCapture(0)  # Try reopening

            # Small delay between attempts
            cv2.waitKey(100)

        QMessageBox.critical(
            self,
            "Camera Error",
            "Failed to capture image after all attempts"
        )
        log.critical("Failed to capture image after all attempts")
        cap.release()
        return None

    def open_settings_dialog(self):
        from deepface import DeepFace

        image = self.get_face()
        if image is None:
                QMessageBox.critical(self, "Camera Error", "Cannot open camera")
                return

        try:
            db_face = self.get_user_face_from_database()
            if db_face is None:
                    QMessageBox.critical(self, "Database Error", "Failed to retrieve user face from database")
                    return

            verify = DeepFace.verify(
                    img1_path=image,
                    img2_path=db_face,
                    enforce_detection=False,
                    model_name='Facenet512',
                    distance_metric="cosine",
                    align=True,
                    detector_backend="opencv"
                )
            if verify['verified']:
                dialog = AndroidSettingsDialog(self)
                dialog.exec_()
            else:
                QMessageBox.warning(self, "Verification", "Face verification failed")
                log.warning("Face verification failed")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Verification failed: {str(e)}")
            log.critical(f"Verification failed: {str(e)}")
            return
        # If the session file is removed, go back to login
        if not os.path.exists(os.path.join(SESSION_PATH, "session.json")):
            self.login_page()

    def open_users_dialog(self):
        dialog = UserDialog(self)
        dialog.exec_()

    def home_application(self):
        """Open the home page dialog."""
        dialog = HomeDialog(self)
        dialog.exec_()

    def call_application(self):
        """Open the Call page dialog."""
        dialog = CallDialerDialog(self)
        dialog.exec_()

    def closeapplication(self):
        QApplication.quit()  # Close the application

    def start_animation(self):
        """Start the animation."""
        if not self.gl_widget.animation_running:
            self.gl_widget.toggle_animation()
            mic_svg = os.path.join(JARVIS_DIR, "icons", "mic.svg")
            self.record_button.setIcon(QIcon(mic_svg))  # Update icon for running animation

    def closeEvent(self, event):
        """Handle window close event."""
        self.stop_recognition.set()
        self.alert_checker.stop()
        if self.audio_stream is not None:
            self.wake_word_thread.quit()
            self.wake_word_thread.wait()
        self.speech_thread.quit()
        self.speech_thread.wait()
        self.alert_thread.quit()
        self.alert_thread.wait()
        event.accept()

    def display_text(self, text):
        """Display text with animations and auto-clear."""
        log.info(text)
        self.animate_text_in(text)

        # Delay the fade-out animation
        QTimer.singleShot(2000, self.animate_text_out)  # Show text for 2 seconds before fading out

    def animate_text_in(self, text):
        """Fade in text with animation."""
        self.text_label.setText(text)  # Update the text
        self.text_label.show()  # Ensure the label is visible

        # Fade in animation
        fade_in = QPropertyAnimation(self.text_label, b"opacity")
        fade_in.setDuration(800)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        fade_in.setEasingCurve(QEasingCurve.OutBack)
        fade_in.start()

    def animate_text_out(self):
        """Fade out text with animation."""
        # Fade out animation
        fade_out = QPropertyAnimation(self.text_label, b"opacity")
        fade_out.setDuration(800)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)
        fade_out.setEasingCurve(QEasingCurve.InBack)

        # Clear the text after the animation completes
        def clear_text():
            self.text_label.clear()
            self.text_label.hide()  # Hide the label to ensure it doesn't remain visible

        fade_out.finished.connect(clear_text)
        fade_out.start()