from PyQt5.QtCore import QObject, pyqtSignal
from queue import Queue
from config import loggers, stop_event
from sounddevice import play, wait, stop
from torch.cuda import is_available
import re
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
        except Exception as e:
            log.error(f"TTS initialization error: {e}")
            self.tts_engine = None
    def set_text(self, text: str):
        if text:
            self.text_queue.put(text)

    def run(self):
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
                emoji_pattern = re.compile("["
                                           u"\U0001F600-\U0001F64F"  # emoticons
                                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                           u"\U0001F700-\U0001F77F"  # alchemical symbols
                                           u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
                                           u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                                           u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                                           u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                                           u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                                           u"\U00002702-\U000027B0"  # Dingbats
                                           u"\U000024C2-\U0001F251"  # Enclosed characters
                                           "]+", flags=re.UNICODE)
                current_text=emoji_pattern.sub(r'',current_text)
                if is_available():
                    from jarvis_integration.audio.tts_providers.indic_parler_tts import Indic_Parler_TTS
                    print("Using transformers...")
                    audio, sample_rate = self.tts_engine.run(current_text)
                    play(audio, sample_rate)
                    wait(ignore_errors=True)
                    stop()
                else:
                    import pyttsx4
                    self.tts_engine = pyttsx4.init()
                    self.tts_engine.say(current_text)
                    self.tts_engine.runAndWait()

            except Exception as e:
                log.error(f"❌ TTS Error: {e}")
                break

        self.finished_signal.emit()
