from PyQt5.QtCore import QObject, pyqtSignal
from queue import Queue
from config import loggers, stop_event
from sounddevice import play, wait, stop
from torch.cuda import is_available

log = loggers['AUDIO']



class TTSWorker(QObject):
    finished_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.text_queue = Queue()
        try:
            if is_available():
                from jarvis_integration.audio.tts_providers.indic_parler_tts import Indic_Parler_TTS,download_parlertts
                download_parlertts()
                self.tts_engine = Indic_Parler_TTS()
                log.info("🔊 Using Indic Parler TTS (CUDA available).")
                print("🔊 Using Indic Parler TTS (CUDA available).")
            else:
                import pyttsx4
                self.tts_engine = pyttsx4.init()
                log.info("🔊 Using pyttsx4 (CPU fallback).")
        except Exception as e:
            log.error(f"TTS initialization error: {e}")
            self.tts_engine = None
    def set_text(self, text: str):
        if text:
            self.text_queue.put(text)

    def run(self):
        from jarvis_integration.audio.tts_providers.indic_parler_tts import Indic_Parler_TTS
        while not self.text_queue.empty():
            if stop_event.is_set():
                stop()
                log.info("🛑 Speech interrupted.")
                stop_event.clear()
                break

            try:
                current_text = self.text_queue.get()
                log.info(f"🗣️ Speaking: {current_text}")
                print(f"🗣️ Speaking: {current_text}")
                if isinstance(self.tts_engine, Indic_Parler_TTS):
                    print("Using transformers...")
                    audio, sample_rate = self.tts_engine.run(current_text)
                    play(audio, sample_rate)
                    wait(ignore_errors=True)
                    stop()
                else:
                    print("using Pyttsx4")
                    self.tts_engine.say(current_text)
                    self.tts_engine.runAndWait()

            except Exception as e:
                log.error(f"❌ TTS Error: {e}")
                break

        self.finished_signal.emit()
