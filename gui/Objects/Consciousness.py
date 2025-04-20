from PyQt5.QtCore import QObject
from PyQt5.QtCore import  pyqtSignal
from config import loggers
from core.memory.memory_agent import MemorySettings
import cv2
import psutil
import socket
import netifaces
from PIL import Image
import requests

from core.Agent_models import get_model

log=loggers['AGENTS']


class ConsciousnessWorker(QObject):
    update_signal = pyqtSignal(str)  # Proactive updates
    image_signal = pyqtSignal(list)  # Image data for processing

    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event
        self.camera = cv2.VideoCapture(0)
        self.last_screenshot_time = 0
        self.memory = MemorySettings()
        self.llm = get_model()

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
        from io import BytesIO
        if self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                emotion = self.detect_emotion(frame)
                self.memory.add_memory(f"Detected emotion: {emotion}", source="emotion")

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return [buffer.getvalue()]
        return None

    def detect_emotion(self, frame):
        from deepface import DeepFace
        try:
            result = DeepFace.analyze(frame, actions=["emotion","gender"], enforce_detection=False)
            result = result[0] if isinstance(result, list) else result
            emotion = result.get("dominant_emotion", "neutral")
            return emotion
        except Exception as e:
            log.warning(f"[Emotion Detection] Error: {e}")
            return "neutral"

    def capture_screenshot(self):
        from pyautogui import screenshot
        from io import BytesIO
        screenshot = screenshot()
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        return [buffer.getvalue()]

    def suggest_from_llm(self, query="current context"):
        try:
            memories = self.memory.search_memory(query, limit=3)
            prompt = "\n".join([f"{m['memory']}" for m in memories])
            prompt += "\n\nBased on this context, provide one suggestion to enhance user experience or productivity."
            response = self.llm.invoke(prompt)
            return response.strip()
        except Exception as e:
            log.error(f"LLM suggestion error: {e}")
            return None

    def run(self):
        log.info("🧠 Consciousness thread running...")
        from time import sleep,time
        while not self.stop_event.is_set():
            try:
                sensors = self.get_system_sensors()
                network = self.get_network_status()

                context = (
                    f"System: {', '.join([f'{k}: {v}' for k, v in sensors.items()])} | "
                    f"Network: {', '.join([f'{k}: {v}' for k, v in network.items()])}"
                )
                self.memory.add_memory(context, source="system")

                if "Battery" in sensors and float(sensors["Battery"].split("%")[0]) < 20:
                    suggestion = "⚠️ Battery critically low. Recommend plugging in or optimizing power usage."
                    self.memory.add_memory(suggestion, source="proactive")
                    self.update_signal.emit(suggestion)

                if network.get("Internet") == "Disconnected":
                    suggestion = "🌐 Network offline. Shall I troubleshoot connectivity?"
                    self.memory.add_memory(suggestion, source="proactive")
                    self.update_signal.emit(suggestion)

                # Camera capture & emotion
                camera_feed = self.capture_camera_feed()
                if camera_feed:
                    self.image_signal.emit(camera_feed)

                # Screenshot every 2 mins
                now = time()
                if now - self.last_screenshot_time > 120:
                    screenshot = self.capture_screenshot()
                    self.image_signal.emit(screenshot)
                    self.last_screenshot_time = now

                # 🧠 LLM Suggestion
                suggestion = self.suggest_from_llm("mood or emotional support")
                if suggestion:
                    self.memory.add_memory(suggestion, source="llm_suggestion")
                    self.update_signal.emit(f"💡 Suggestion: {suggestion}")

                sleep(120)  # Run every 5 minutes
            except Exception as e:
                log.error(f"Consciousness error: {e}")

    def cleanup(self):
        if self.camera.isOpened():
            self.camera.release()
