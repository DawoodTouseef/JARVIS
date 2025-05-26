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
from PyQt5.QtCore import QObject, pyqtSignal
import litellm

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
            from core.Agent_models import get_model_from_database, get_vision_model_from_database
            if  get_model_from_database() is not None:
                from core.memory.memory_agent import MemorySettings
                memory=MemorySettings()
                memory._initialize_memory()
                from core.brain import JARVIS
                agent=JARVIS(memory)
                if get_vision_model_from_database() is not None:
                    from core.agents.vision_agents import vision_agent
                    if not self.text:
                        log.info("🧠 Vision-only task initiated (no text provided).")
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
                    response = agent.get_agent(user_input=self.text, image=self.image)
                else:
                    response = agent.get_agent(user_input=self.text)
                log.info(f"🤖 Agent Response: {response}")
                print(f"🤖 Agent Response: {response}")
                self.response_signal.emit(response)

        except Exception as e:
            err_msg = f"❌ Agent Error: {str(e)}"
            log.error(err_msg)
            self.response_signal.emit(err_msg)

        except litellm.exceptions.RateLimitError as e:
            err_msg = f"❌ Agent Error: {str(e['error']['message'])}"
            log.error(err_msg)
            self.response_signal.emit(err_msg)