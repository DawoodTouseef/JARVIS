import speech_recognition as sr
from PyQt5.QtCore import QObject
from PyQt5.QtCore import  pyqtSignal
from config import loggers
import numpy as np
from langchain.tools.human.tool import HumanInputRun
import time
import webrtcvad
import collections
import pyaudio


log=loggers['AUDIO']

class SpeechRecognitionWorker(QObject):
    listen_signal = pyqtSignal(str)
    transcription_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, recognizer, microphone, stop_event, sample_rate=16000, vad_mode=3):
        super().__init__()
        self.recognizer = recognizer
        self.microphone = microphone
        self.stop_event = stop_event
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(vad_mode)
        self.sample_rate = sample_rate
        self.ring_buffer = collections.deque(maxlen=75)  # 1.5s buffer
        self.is_speech_active = False
        self.speech_start_time = None

    def recognize(self, audio_data):
        try:
            audio = sr.AudioData(audio_data, self.sample_rate, 2)
            transcription = self.recognizer.recognize_whisper(audio, model="medium")
            self.transcription_signal.emit(transcription)
        except Exception as e:
            self.error_signal.emit(f"⚠️ Error: {str(e)}")

    def run(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=self.sample_rate, input=True, frames_per_buffer=320)
        while not self.stop_event.is_set():
            frame = stream.read(320, exception_on_overflow=False)
            self.ring_buffer.append(frame)
            if self.vad.is_speech(frame, self.sample_rate):
                if not self.is_speech_active:
                    self.is_speech_active = True
                    self.speech_start_time = time.time()
                    self.listen_signal.emit("🎙️ Listening...")
            elif self.is_speech_active and time.time() - self.speech_start_time > 1.0:
                self.is_speech_active = False
                audio_data = b''.join(self.ring_buffer)
                self.recognize(audio_data)
        stream.stop_stream()
        stream.close()
        p.terminate()