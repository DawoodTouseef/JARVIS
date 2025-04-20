import speech_recognition as sr
from PyQt5.QtCore import QObject
from PyQt5.QtCore import  pyqtSignal
from config import loggers
import numpy as np

log=loggers['AUDIO']



class SpeechRecognitionWorker(QObject):
    listen_signal = pyqtSignal(str)
    transcription_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, recognizer: sr.Recognizer, microphone: sr.Microphone, stop_event):
        super().__init__()
        self.recognizer = recognizer
        self.microphone = microphone
        self.stop_event = stop_event
        self.log = loggers["AUDIO"]
        self.energy_threshold = 300
        self.silence_duration = 2  # seconds
        self.frame_duration_ms = 30  # 30ms per frame
        self.sample_rate = 16000
        self.sample_width = 2
        self.chunk_size = int(self.sample_rate * (self.frame_duration_ms / 1000.0))

    def run(self):
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.listen_signal.emit("🎙️ Listening...")

                audio = self.recognizer.listen(source)

                if audio is not None:
                    self.listen_signal.emit("🧠 Recognizing speech...")
                    transcription = self.recognizer.recognize_whisper(audio, model="medium")
                    self.log.info(f"Transcription: {transcription}")
                    self.transcription_signal.emit(transcription)
                else:
                    self.error_signal.emit("⚠️ No speech detected or audio capture failed.")

        except sr.UnknownValueError:
            self.log.error("❌ Could not understand the audio.")
            self.error_signal.emit("❌ Sorry, I couldn't understand what you said.")
        except sr.RequestError as e:
            self.log.error(f"🚫 API request error: {e}")
            self.error_signal.emit(f"🚫 API request error: {e}")
        except Exception as e:
            self.error_signal.emit(f"⚠️ Unexpected error occurred: {str(e)}")
