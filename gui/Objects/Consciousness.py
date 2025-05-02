from PyQt5.QtCore import QObject, pyqtSignal
from config import loggers
from core.memory.memory_agent import MemorySettings
from core.Agent_models import get_model

import cv2, psutil, socket, netifaces, requests
from PIL import Image
from time import time, sleep
from io import BytesIO

log = loggers['AGENTS']


class ConsciousnessWorker(QObject):
    update_signal = pyqtSignal(str)  # Proactive messages for GUI
    image_signal = pyqtSignal(list)  # Pass image data to vision model

    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event
        self.memory = MemorySettings()
        self.memory._initialize_memory()
        self.llm = get_model()
        self.last_screenshot_time = 0
        self.camera = cv2.VideoCapture(0)

    # ----------------- Internal Awareness ----------------- #
    def awareness_system(self):
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        battery = psutil.sensors_battery()
        battery_info = f"{battery.percent}% (Plugged in: {battery.power_plugged})" if battery else "N/A"

        stats = {
            "CPU": f"{cpu}%",
            "Memory": f"{mem}%",
            "Disk": f"{disk}%",
            "Battery": battery_info
        }

        self.memory.add_memory(str(stats), source="system")
        if battery and battery.percent < 20:
            alert = "⚠️ Battery critically low. Plug in the device."
            self.update_signal.emit(alert)
            self.memory.add_memory(alert, source="alert")

        return stats

    def awareness_mood(self, frame):
        from deepface import DeepFace
        try:
            result = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False)
            emotion = result[0]["dominant_emotion"] if isinstance(result, list) else result["dominant_emotion"]
            self.memory.add_memory(f"Detected emotion: {emotion}", source="emotion")
            return emotion
        except Exception as e:
            log.warning(f"[Emotion] {e}")
            return "neutral"

    def awareness_llm_suggestion(self, query="system and emotional context"):
        try:
            memories = self.memory.search_memory(query, limit=3)
            prompt = "\n".join(m['memory'] for m in memories) + \
                     "\n\nBased on this, suggest a tip or improvement."
            suggestion = self.llm.invoke(prompt).strip()
            self.memory.add_memory(suggestion, source="llm")
            self.update_signal.emit(f"💡 Tip: {suggestion}")
        except Exception as e:
            log.error(f"[LLM Suggestion] {e}")

    # ----------------- External Awareness ----------------- #
    def awareness_network(self):
        try:
            ip = socket.gethostbyname(socket.gethostname())
            gateway = netifaces.gateways().get('default', {}).get(netifaces.AF_INET, [None])[0]
            connected = requests.get("http://www.google.com", timeout=2).status_code == 200
            net = {
                "IP": ip,
                "Gateway": gateway or "N/A",
                "Internet": "Connected" if connected else "Disconnected"
            }
            self.memory.add_memory(str(net), source="network")
            if not connected:
                msg = "🌐 Internet appears disconnected."
                self.update_signal.emit(msg)
            return net
        except Exception:
            return {"Internet": "Status unknown"}

    def awareness_camera(self):
        if self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                emotion = self.awareness_mood(frame)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                self.image_signal.emit([buffer.getvalue()])

    def awareness_screenshot(self):
        from pyautogui import screenshot
        ss = screenshot()
        buffer = BytesIO()
        ss.save(buffer, format="PNG")
        self.image_signal.emit([buffer.getvalue()])
        self.last_screenshot_time = time()

    # ----------------- Extendable Hook ----------------- #
    def awareness_extendable_tasks(self):
        # 👉 Add future IoT sensor awareness, app usage, activity tracking here
        pass

    # ----------------- Main Loop ----------------- #
    def run(self):
        log.info("🧠 Consciousness thread running...")
        while not self.stop_event.is_set():
            try:
                system_stats = self.awareness_system()
                network_stats = self.awareness_network()
                self.awareness_camera()

                if time() - self.last_screenshot_time > 120:
                    self.awareness_screenshot()

                self.awareness_llm_suggestion()
                self.awareness_extendable_tasks()

                sleep(60)
            except Exception as e:
                log.error(f"[Consciousness Thread Error] {e}")

    def cleanup(self):
        if self.camera.isOpened():
            self.camera.release()
