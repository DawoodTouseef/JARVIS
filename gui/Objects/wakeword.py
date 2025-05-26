from PyQt5.QtCore import QObject
from PyQt5.QtCore import  pyqtSignal
from config import loggers
import struct

log=loggers['AUDIO']

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

