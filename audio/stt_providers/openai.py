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

from typing import Dict, Union

from openai import OpenAI
from .BaseSTT import BaseSpeech2Text

from pathlib import Path as File
from .exception import STTException

class OpenAISTT(BaseSpeech2Text):
    def __init__(self):
        super().__init__()
        self.client=None
    def configure(self,api_key:str):
        self.client=OpenAI(
            api_key=api_key
        )
    def transcribe(self, audio_data: "File", streaming: bool = False) -> str:
        if self.client is not None:
            responses=self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_data
            )
            return responses.text
        else:
            raise STTException("First, you need to configure it. Then, call the function.",status_code=500)


