from PyQt5.QtCore import QObject, pyqtSignal
from config import loggers

log = loggers['AGENTS']

class AgentWorker(QObject):
    response_signal = pyqtSignal(str) #Signal to emit and play the audio

    def __init__(self):
        super().__init__()
        self.text = None
        self.image = None

    def set_text(self, text):
        self.text = text

    def set_input(self, image):
        self.image = image

    def run(self):
        try:
            from core.brain import get_agent
            from core.vision_agents import vision_agent
            from core.Agent_models import get_model_from_database, get_vision_model_from_database

            if not self.text:
                log.info("🧠 Vision-only task initiated (no text provided).")
                vision_model = get_vision_model_from_database()
                if vision_model:
                    response = vision_agent(image_inputs=self.image, user_input="Analyze this image and give a brief understanding.")
                    log.info(f"🖼️ Vision Agent Response: {response}")
                    self.response_signal.emit(response)
                else:
                    warning = "⚠️ Vision model not configured. Please set it up in settings."
                    log.warning(warning)
                    self.response_signal.emit(warning)
                return

            log.info(f"💬 Processing input: {self.text}")
            llm_model = get_model_from_database()
            if not llm_model:
                msg = "⚠️ Language model not configured. Please check your assistant settings."
                log.warning(msg)
                self.response_signal.emit(msg)
                return


                # If image is provided, pass both text and image
            if self.text and self.image and get_vision_model_from_database() is not None:
                response = get_agent(user_input=self.text, image=self.image)
            else:
                response = get_agent(user_input=self.text)

            log.info(f"🤖 Agent Response: {response}")
            print(f"🤖 Agent Response: {response}")
            self.response_signal.emit(response)

        except Exception as e:
            err_msg = f"❌ Agent Error: {str(e)}"
            log.error(err_msg)
            self.response_signal.emit(err_msg)