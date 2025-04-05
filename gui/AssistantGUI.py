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
from PyQt5.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu,QAction
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
import io
import pyautogui
from PyQt5.QtCore import  pyqtProperty, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QBrush, QLinearGradient, QFont
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox,  QDialog
)
from core.brain import MemorySettings
import time
import os
from config import  stop_event, loggers
import sounddevice as sd
from audio.tts_providers.BarkTTS import BarkTTS as Indic_Parler_TTS
import torch
import pyttsx4
import numpy as np
import psutil
import netifaces
from datetime import datetime
import cv2
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt
import requests
from PIL import Image
import socket
import subprocess,platform


if torch.cuda.is_available():
    tts = Indic_Parler_TTS()
else:
    tts = pyttsx4.init()
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


class SecurityIndicator(QWidget):
    """Circular security status indicator (Green=Secure, Red=Threat)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 90)
        self._status = False
        self.opacity = 1.0

    def set_status(self, active):
        """Change security status."""
        self._status = active
        self.update()

    def paintEvent(self, event):
        """Draw security indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(30, 30, 30))
        painter.drawEllipse(0, 0, 90, 90)

        color = QColor(0, 255, 0) if self._status else QColor(255, 0, 0)
        painter.setBrush(color)
        painter.drawEllipse(20, 20, 50, 50)

class SecurityScanThread(QThread):
    """Thread to perform real security scanning."""
    scanCompleted = pyqtSignal(int)  # Emits number of detected threats

    def __init__(self, scan_type="quick"):
        super().__init__()
        self.scan_type = scan_type

    def run(self):
        """Runs system security scanning based on OS."""
        detected_threats = 0
        os_name = platform.system()

        if os_name == "Windows":
            detected_threats = self.scan_windows()
        elif os_name == "Linux":
            detected_threats = self.scan_linux()
        elif os_name == "Darwin":  # macOS
            detected_threats = self.scan_macos()

        self.scanCompleted.emit(detected_threats)

    def scan_windows(self):
        """Performs a security scan using Windows Defender."""
        try:
            scan_cmd = r'powershell -Command "Start-MpScan -ScanType QuickScan"'
            subprocess.run(scan_cmd, shell=True, check=True)

            result = subprocess.run(
                r'powershell -Command "Get-MpThreat | Measure-Object"',
                shell=True, capture_output=True, text=True
            )

            threats_found = int(result.stdout.strip().split()[-1]) if result.stdout.strip() else 0
            return threats_found

        except Exception as e:
            print(f"[Error] Windows Defender Scan Failed: {e}")
            return 0

    def scan_linux(self):
        """Performs a security scan using ClamAV on Linux."""
        try:
            if os.system("which clamscan > /dev/null 2>&1") != 0:
                print("[Error] ClamAV is not installed. Install it using 'sudo apt install clamav'")
                return 0

            os.system("freshclam")

            result = subprocess.run(
                "clamscan -r --bell -i /home",  # Modify path as needed
                shell=True, capture_output=True, text=True
            )

            threats = sum(1 for line in result.stdout.split("\n") if "FOUND" in line)
            return threats

        except Exception as e:
            print(f"[Error] ClamAV Scan Failed: {e}")
            return 0

    def scan_macos(self):
        """Performs a security scan using ClamAV on macOS."""
        return self.scan_linux()  # macOS also uses ClamAV


class SecurityDashboard(QWidget):
    """Security dashboard widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_threats = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        self.status_header = QLabel("🛡️ Quantum Security Shield")
        self.status_header.setStyleSheet("font-size: 18px; color: #00ffff; font-weight: bold;")

        stats_layout = QHBoxLayout()
        self.threat_count = QLabel("0 Threats Blocked")
        self.last_scan = QLabel("Last Scan: Never")
        stats_layout.addWidget(self.threat_count)
        stats_layout.addWidget(self.last_scan)

        self.security_indicator = QLabel("🟢 Secure")
        self.security_indicator.setAlignment(Qt.AlignCenter)
        self.security_indicator.setStyleSheet("font-size: 16px; color: green; font-weight: bold;")

        control_layout = QHBoxLayout()
        self.quick_scan_btn = QPushButton("🚀 Quick Scan")
        self.full_scan_btn = QPushButton("🛑 Full Scan")
        control_layout.addWidget(self.quick_scan_btn)
        control_layout.addWidget(self.full_scan_btn)

        layout.addWidget(self.status_header)
        layout.addLayout(stats_layout)
        layout.addWidget(self.security_indicator, alignment=Qt.AlignCenter)
        layout.addLayout(control_layout)

        self.setLayout(layout)
        self.setStyleSheet("""
            background-color: rgba(40, 40, 40, 220);
            border-radius: 15px;
            border: 2px solid #505050;
        """)

        self.quick_scan_btn.clicked.connect(lambda: self.start_scan("quick"))
        self.full_scan_btn.clicked.connect(lambda: self.start_scan("full"))

    def start_scan(self, scan_type):
        """Starts the security scan."""
        self.security_indicator.setText("🟡 Scanning...")
        self.security_indicator.setStyleSheet("font-size: 16px; color: orange; font-weight: bold;")

        self.scan_thread = SecurityScanThread(scan_type)
        self.scan_thread.scanCompleted.connect(self.update_scan_results)
        self.scan_thread.start()

    def update_scan_results(self, detected_threats):
        """Updates UI with scan results."""
        self.total_threats += detected_threats
        self.threat_count.setText(f"{self.total_threats} Threats Blocked")
        self.last_scan.setText(f"Last Scan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if detected_threats > 0:
            self.security_indicator.setText("🔴 Threats Detected!")
            self.security_indicator.setStyleSheet("font-size: 16px; color: red; font-weight: bold;")
        else:
            self.security_indicator.setText("🟢 Secure")
            self.security_indicator.setStyleSheet("font-size: 16px; color: green; font-weight: bold;")

    def closeEvent(self, a0):
        self.scan_thread.quit()
        self.scan_thread.wait()

        a0.accept()

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


class WakeWordWorker(QObject):
    wake_word_detected = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, porcupine, audio_stream, stop_event):
        super().__init__()
        self.porcupine = porcupine
        self.audio_stream = audio_stream
        self.stop_event = stop_event

    def run(self):
        try:
            log.info("Listening for wake word...")
            while not self.stop_event.is_set():
                pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack("h" * self.porcupine.frame_length, pcm)
                result = self.porcupine.process(pcm)
                if result >= 0:
                    self.wake_word_detected.emit()
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.cleanup()

    def cleanup(self):
        if self.porcupine:
            self.porcupine.delete()
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()


class SpeechRecognitionWorker(QObject):
    listen_signal = pyqtSignal(str)
    transcription_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, recognizer: sr.Recognizer(), microphone: sr.Microphone(), stop_event):
        super().__init__()
        self.recognizer = recognizer
        self.microphone = microphone
        self.stop_event = stop_event
        self.log = loggers["AUDIO"]

    def capture_with_vad(self, source):
        audio_data = []
        energy_threshold = 300
        silence_duration = 2
        silence_counter = 0

        while not self.stop_event.is_set():
            try:
                frame = source.stream.read(1024)
                pcm_data = np.frombuffer(frame, dtype=np.int16)
                energy = np.sqrt(np.mean(pcm_data ** 2))

                if energy > energy_threshold:
                    audio_data.append(frame)
                    silence_counter = 0
                else:
                    silence_counter += 1

                if silence_counter > silence_duration * (source.SAMPLE_RATE / 1024):
                    break
            except Exception as e:
                self.error_signal.emit(f"Error during audio capture: {e}")
                return None

        return sr.AudioData(b''.join(audio_data), source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    def run(self):
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=5)
                self.listen_signal.emit("Listening...")
                # Use VAD instead of recognizer.listen for consistency
                audio = self.recognizer.listen(source)
                if audio:
                    self.listen_signal.emit("Recognizing...")
                    transcription = self.recognizer.recognize_whisper(audio, model="base")
                    self.log.info(f"Transcription: {transcription}")
                    self.transcription_signal.emit(transcription)
                else:
                    self.error_signal.emit("No audio captured.")
        except sr.UnknownValueError:
            self.log.error("Sorry, I didn't catch that.")
            self.error_signal.emit("Sorry, I didn't catch that.")
        except sr.RequestError as e:
            self.log.error(f"API error: {e}")
            self.error_signal.emit(f"API error: {e}")
        except Exception as e:
            self.error_signal.emit(str(e))


class AgentWorker(QObject):
    response_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.text = None
        self.image=None
    def set_text(self, text):
        self.text = text

    def set_input(self,image):
        self.image = image

    def run(self):
        from core.brain import get_agent
        from core.vision_agents import vision_agent
        from core.Agent_models import get_model_from_database,get_vision_model_from_database
        if self.text is None:
            if get_vision_model_from_database() is not None:
                response = vision_agent(images=self.image)
                log.info(f"Agent Response: {response}")
                self.response_signal.emit(response)
            else:
                self.response_signal.emit("⚠️ Oops! It looks like the model isn't configured yet. Please check the settings and set it up to proceed.")

        log.info(f"Processing input: {self.text}")
        if get_model_from_database():
            try:
                if self.image is not  None:
                    response = get_agent(user_input=self.text,image=self.image)
                    log.info(f"Agent Response: {response}")
                    self.response_signal.emit(response)
                else:
                    response = get_agent(user_input=self.text)
                    log.info(f"Agent Response: {response}")
                    self.response_signal.emit(response)

            except Exception as e:
                self.response_signal.emit(f"⚠️ An error occurred: {str(e)}")
        else:
            self.response_signal.emit("⚠️ Oops! It looks like the model isn't configured yet. Please check the settings and set it up to proceed.")



class AlertCheck(QObject):
    alert_triggered = pyqtSignal(list)  # Signal to emit triggered alerts (stock and system)

    def __init__(self, db_tool, yahoo_tool, parent=None):
        super().__init__(parent)
        self.db_tool = db_tool
        self.yahoo_tool = yahoo_tool
        self.running = False
        # Thresholds for proactive system alerts (customizable via preferences if desired)
        self.cpu_threshold = 90.0  # Alert if CPU usage > 90%
        self.memory_threshold = 90.0  # Alert if memory usage > 90%
        self.battery_threshold = 20.0  # Alert if battery < 20%
        self.disk_threshold = 90.0  # Alert if disk usage > 90%

    def get_system_sensors(self):
        """Fetch system metrics using psutil."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery()
            return {
                "cpu": cpu_usage,
                "memory": memory.percent,
                "disk": disk.percent,
                "battery": battery.percent if battery else 100.0,  # Assume 100% if no battery
                "power_plugged": battery.power_plugged if battery else True
            }
        except Exception as e:
            return {"error": f"System monitoring failed: {str(e)}"}

    def get_network_status(self):
        """Check network connectivity using netifaces."""
        try:
            gateways = netifaces.gateways()
            return "connected" if 'default' in gateways and gateways['default'] else "disconnected"
        except Exception:
            return "unknown"

    def run(self):
        from core.personal_assistant import EXCHANGE_RATES  # Assuming EXCHANGE_RATES is defined here
        self.running = True
        while self.running:
            triggered = []  # Collect all alerts (stock + system)

            # 1. Stock Alerts (existing functionality)
            user_currency_result = self.db_tool._run("get_preference", key="currency", default="USD")
            user_currency = user_currency_result if user_currency_result in EXCHANGE_RATES else "USD"
            rate_to_usd = EXCHANGE_RATES[user_currency]
            alerts = json.loads(self.db_tool._run("get_alerts"))
            purchases = json.loads(self.db_tool._run("get_purchases_for_alerts"))

            # Stock price target alerts
            for ticker, target_price, alert_currency in alerts:
                data = json.loads(self.yahoo_tool._run(ticker))
                if "price" in data:
                    usd_price = data["price"]
                    alert_price_in_usd = target_price / EXCHANGE_RATES.get(alert_currency, 1.0)
                    if usd_price >= alert_price_in_usd:
                        converted_price = usd_price * EXCHANGE_RATES[user_currency]
                        triggered.append(
                            f"Alert: {data['company']} ({ticker}) is at {user_currency}{converted_price:.2f}, hit your target of {alert_currency}{target_price}"
                        )
                        self.db_tool._run("log_notification",
                                        message=f"Alert triggered for {ticker} at {user_currency}{converted_price:.2f}")

            # Stock profit reminders
            for ticker, purchase_price, quantity, purchase_currency in purchases:
                data = json.loads(self.yahoo_tool._run(ticker))
                if "price" in data:
                    usd_price = data["price"]
                    purchase_price_usd = purchase_price / EXCHANGE_RATES.get(purchase_currency, 1.0)
                    target_profit = float(self.db_tool._run("get_preference", key=f"{ticker}_target_profit", default=0))
                    min_profit = float(self.db_tool._run("get_preference", key=f"{ticker}_min_profit", default=0))
                    profit_usd = (usd_price - purchase_price_usd) * quantity
                    target_price_usd = purchase_price_usd + target_profit
                    if usd_price >= target_price_usd and profit_usd >= min_profit:
                        converted_price = usd_price * EXCHANGE_RATES[user_currency]
                        converted_profit = profit_usd * EXCHANGE_RATES[user_currency]
                        triggered.append(
                            f"Reminder: {data['company']} ({ticker}) bought at {purchase_currency}{purchase_price} is now {user_currency}{converted_price:.2f}. Selling yields profit of {user_currency}{converted_profit:.2f} (≥ {user_currency}{min_profit})."
                        )
                        self.db_tool._run("log_notification",
                                        message=f"Profit reminder for {ticker}: {user_currency}{converted_profit:.2f}")

            # 2. System Monitoring and Proactive Updates
            sensors = self.get_system_sensors()
            network_status = self.get_network_status()

            # CPU usage alert
            if "cpu" in sensors and sensors["cpu"] > self.cpu_threshold:
                triggered.append(f"Warning: CPU usage at {sensors['cpu']:.1f}%, exceeding {self.cpu_threshold}% threshold.")
                self.db_tool._run("log_notification",
                                message=f"High CPU usage detected: {sensors['cpu']:.1f}% at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Memory usage alert
            if "memory" in sensors and sensors["memory"] > self.memory_threshold:
                triggered.append(f"Warning: Memory usage at {sensors['memory']:.1f}%, exceeding {self.memory_threshold}% threshold.")
                self.db_tool._run("log_notification",
                                message=f"High memory usage detected: {sensors['memory']:.1f}% at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Disk usage alert
            if "disk" in sensors and sensors["disk"] > self.disk_threshold:
                triggered.append(f"Warning: Disk usage at {sensors['disk']:.1f}%, exceeding {self.disk_threshold}% threshold.")
                self.db_tool._run("log_notification",
                                message=f"High disk usage detected: {sensors['disk']:.1f}% at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Battery level alert (if not plugged in)
            if "battery" in sensors and sensors["battery"] < self.battery_threshold and not sensors["power_plugged"]:
                triggered.append(f"Warning: Battery level at {sensors['battery']:.1f}%, below {self.battery_threshold}% threshold.")
                self.db_tool._run("log_notification",
                                message=f"Low battery detected: {sensors['battery']:.1f}% at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Network disconnection alert
            if network_status == "disconnected":
                triggered.append("Warning: Network connection lost.")
                self.db_tool._run("log_notification",
                                message=f"Network disconnection detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Emit all triggered alerts (stock + system)
            if triggered:
                self.alert_triggered.emit(triggered)

            # Sleep for 10 seconds (consistent with stock checks)
            QThread.msleep(10000)

    def stop(self):
        self.running = False

class TTSWorker(QObject):
    finished_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.text =Queue()

    def set_text(self, text):
        self.text.put(text)

    def run(self):
        if self.text.empty():
            self.finished_signal.emit()
            return

        if stop_event.is_set():
            sd.stop()
            stop_event.clear()

        log.info(f"Speaking: {self.text.get()}")
        try:
            if torch.cuda.is_available():
                audio, sample_rate = tts.run(self.text.get())  # Assuming tts.run is defined elsewhere
                sd.play(data=audio, samplerate=sample_rate)
                sd.wait(ignore_errors=True)
                sd.stop()
            else:
                # tts.setProperty("speaker_wav","")
                tts.say(self.text)
                tts.runAndWait()
        except Exception as e:
            log.error(f"TTS error: {e}")
        finally:
            self.finished_signal.emit()

class ConsciousnessWorker(QObject):
    update_signal = pyqtSignal(str)  # Proactive updates
    image_signal = pyqtSignal(list)  # Image data for processing

    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event
        self.memory = MemorySettings()
        self.camera = cv2.VideoCapture(0)  # Default camera
        self.last_screenshot_time = 0

    def get_system_sensors(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        disk = psutil.disk_usage('/')
        return {
            "CPU Usage": f"{cpu_usage}%",
            "Memory Usage": f"{memory.percent}%",
            "Battery": f"{battery.percent}% (Plugged: {battery.power_plugged})" if battery else "N/A",
            "Disk Usage": f"{disk.percent}%"
        }

    def get_network_status(self):
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            gateways = netifaces.gateways()
            default_gateway = gateways['default'][netifaces.AF_INET][0] if 'default' in gateways else "Unknown"
            return {
                "IP Address": ip,
                "Gateway": default_gateway,
                "Internet": "Connected" if requests.get("http://www.google.com", timeout=2).status_code == 200 else "Disconnected"
            }
        except:
            return {"Internet": "Status unknown"}

    def capture_camera_feed(self):
        if self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                # Convert to PIL Image and save temporarily
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return [buffer.getvalue()]  # Return as a list for get_agent compatibility
        return None

    def capture_screenshot(self):
        screenshot = pyautogui.screenshot()
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        return [buffer.getvalue()]

    def run(self):
        log.info("JARVIS consciousness online...")
        while not self.stop_event.is_set():
            try:
                # System and network awareness
                sensors = self.get_system_sensors()
                network = self.get_network_status()
                context = (
                    f"System: {', '.join([f'{k}: {v}' for k, v in sensors.items()])} | "
                    f"Network: {', '.join([f'{k}: {v}' for k, v in network.items()])}"
                )
                self.memory.add_memory(context, source="system")

                # Proactive checks
                if "Battery" in sensors and float(sensors["Battery"].split("%")[0]) < 20:
                    suggestion = "Battery critically low, sir. Recommend plugging in or optimizing power usage."
                    self.memory.add_memory(suggestion, source="proactive")
                    self.update_signal.emit(suggestion)

                if "Internet" in network and network["Internet"] == "Disconnected":
                    suggestion = "Network offline, sir. Shall I troubleshoot connectivity?"
                    self.memory.add_memory(suggestion, source="proactive")
                    self.update_signal.emit(suggestion)

                # Camera feed analysis (every 60 seconds)
                camera_feed = self.capture_camera_feed()
                if camera_feed:
                    self.image_signal.emit(camera_feed)
                    self.memory.add_memory("Captured camera feed", source="camera")

                # Screenshot analysis (every 120 seconds, staggered from camera)
                current_time = time.time()
                if current_time - self.last_screenshot_time > 120:
                    screenshot = self.capture_screenshot()
                    self.image_signal.emit(screenshot)
                    self.memory.add_memory("Captured screenshot", source="screenshot")
                    self.last_screenshot_time = current_time

                # Retrieve proactive context
                proactive = self.memory.get_proactive_context("current state")
                if proactive and "Suggestion" in proactive:
                    self.update_signal.emit(proactive.split("Suggestion: ")[-1])

                time.sleep(300)  # Check every 5 minutes for responsiveness
            except Exception as e:
                log.error(f"Consciousness error: {e}")

    def cleanup(self):
        if self.camera.isOpened():
            self.camera.release()

class ImagePreviewDialog(QDialog):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Captured Image Preview")
        self.setModal(False)  # Non-modal so code can continue

        # Convert OpenCV BGR image to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Convert to QImage
        h, w, ch = image_rgb.shape
        bytes_per_line = ch * w
        q_image = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Create pixmap and scale it
        pixmap = QPixmap.fromImage(q_image)
        pixmap = pixmap.scaled(640, 480, Qt.KeepAspectRatio)

        # Setup UI
        layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap)
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        # Adjust window size to image
        self.adjustSize()

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
        # OpenGL Widget
        central_widget = QWidget(self)
        layout = QVBoxLayout()

        # OpenGL Assistant Interface
        self.gl_widget = AssistantOpenGLWidget(self)

        # Security Dashboard
        self.security_dashboard = SecurityDashboard(self)

        layout.addWidget(self.gl_widget)
        layout.addWidget(self.security_dashboard)

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
                "callback": self.home_application,
                "tooltip": "Home",
                "key": QKeySequence(Qt.CTRL + Qt.Key.Key_M)
            },
            {
                "name": "call_button",
                "geometry": (420, 20, 60, 60),
                "icon": "phone.svg",
                "callback": self.call_application,
                "tooltip": "Call Window",
                "key": QKeySequence(Qt.CTRL + Qt.Key_C)
            },
            {
                "name": "close_button",
                "geometry": (500, 20, 60, 60),
                "icon": "close.svg",
                "callback": self.closeapplication,
                "tooltip": "Close Application",
                "key": QKeySequence(Qt.Key.Key_Alt + Qt.Key_F4)
            },
        ]

        for config in button_config:
            icon_path = os.path.join(JARVIS_DIR, "icons", config["icon"])
            button = AnimatedButton(icon_path, self)
            button.setGeometry(*config["geometry"])
            button.clicked.connect(config["callback"])
            button.setShortcut(config['key'])
            button.setToolTip(f"{config.get("tooltip", "")} ({config['key'].toString()})")

            # Add moving light effect on hover
            shadow = QGraphicsDropShadowEffect()
            shadow.setColor(QColor(0, 191, 255))  # Blue shadow
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 0)
            button.setGraphicsEffect(shadow)

            setattr(self, config["name"], button)

        # Enable the window to be resized
        self.setFixedSize(650, 800)  # Adjust size if needed
        self.center_window()
        self.show()

    def update_security_indicator(self, status):
        """Update Security Indicator based on System Status"""
        self.security_indicator.set_status(status['active'])
        self.animate_security_indicator(status['active'])

    def animate_security_indicator(self, active):
        """Add Fade Effect on Security Indicator"""
        animation = QPropertyAnimation(self.security_indicator, b"opacity")
        animation.setDuration(500)
        animation.setStartValue(0.5 if active else 1.0)
        animation.setEndValue(1.0 if active else 0.5)
        animation.start()

    def handle_threat(self, threat_info):
        """Handle Detected Threats"""
        self.text_label.start_fade_animation(f"⚠️ Threat Detected: {threat_info['file_path']}")
        self.text_label.setStyleSheet("color: #ff4444; font-weight: bold;")

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
        if not self.tts_thread.isRunning():
            self.tts_worker.set_text(text)
            self.tts_thread.start()

    def tts_finished(self):
        """Handles completion of TTS playback."""
        self.tts_thread.quit()
        self.tts_thread.wait()
        self.agent_thread.quit()
        self.agent_thread.wait()
        self.speech_thread.quit()
        self.speech_thread.wait()
        self.stop_interaction_animation()

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
                if hasattr(self, 'speech_thread') and self.speech_thread.isRunning():
                    self.stop_recognition.set()
                    self.recognition_running = False
                    mic_svg = os.path.join(JARVIS_DIR, "icons", "mic-off.svg")
                    self.record_button.setIcon(QIcon(mic_svg))
                    self.speech_thread.quit()
                    self.speech_thread.wait()
            except Exception as e:
                self.display_error(f"Failed to stop recording: {e}")

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
