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

import os
import torch
import logging
from config import JARVIS_DIR
from jarvis_integration.audio.tts_providers.BaseTTS import BaseText2Speech
from transformers import AutoTokenizer
from config import SRC_LOG_LEVELS
from parler_tts import ParlerTTSForConditionalGeneration

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])


def download_parlertts():
    """Download the Parler TTS model if not already present."""
    try:
        import git
    except Exception as e:
        log.error("Bad git executable.")
    path = os.path.join(JARVIS_DIR, "config", "model", "parler-tts")
    if not os.path.exists(path):
        log.info(f"Downloading the model to {path} ...")
        try:
            git.Repo.clone_from("https://huggingface.co/ai4bharat/indic-parler-tts", to_path=path)
            log.info("Model downloaded successfully")
        except Exception as e:
            log.error(f"Failed to download model: {e}")
            raise
    else:
        log.info("Model already downloaded.")

class Indic_Parler_TTS(BaseText2Speech):
    def __init__(self):
            super().__init__()
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            local_path = os.path.join(JARVIS_DIR, "config", "model", "parler-tts")

            # Load model and tokenizers
            self.model = ParlerTTSForConditionalGeneration.from_pretrained(local_path).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(local_path)
            self.desc_tokenizer = AutoTokenizer.from_pretrained(self.model.config.text_encoder._name_or_path)

            log.info("Indic_Parler_TTS model loaded.")
            if self.device == "cuda":
                log.info(f"GPU memory allocated: {torch.cuda.memory_allocated() / (1024 ** 3):.2f} GB")

    def synthesize(self, text: str):
        """Synthesize speech from text with a fixed English description."""
        # Fixed English description for voice conditioning
        description = """A deep, robotic male voice, calm, precise, and slightly monotone. 
                    The speech is clear, authoritative, and measured, delivered with a controlled pace 
                    and even tone, resembling a highly intelligent AI assistant."""

        # Tokenize with max_length to limit memory usage
        input_ids = self.desc_tokenizer(
            description, return_tensors="pt", truncation=True
        ).input_ids.to(self.device)
        prompt_input_ids = self.tokenizer(
            text, return_tensors="pt", truncation=True
        ).input_ids.to(self.device)

        # Generate audio
        generation = self.model.generate(input_ids=input_ids, prompt_input_ids=prompt_input_ids)
        audio_arr = generation.cpu().numpy().squeeze().astype('float32')

        return audio_arr, self.model.config.sampling_rate

    def detect_language(self, text: str) -> str:
        """Detect the language of the input text."""
        from langdetect import detect
        try:
            return detect(text)
        except Exception as e:
            log.error(f"Language detection error: {e}")
            return "en"


if __name__=="__main__":
    import sounddevice as sd
    from datetime import datetime

    print(f"Loading:{datetime.now().time()}")
    tts=Indic_Parler_TTS()
    print(f"Started:{datetime.now().time()}")
    audio, sample_rate = tts.run("Hello How are you?")
    print(f"Completed:{datetime.now().time()}")
    user_input=input("Enter 'speak' to play the audio:")
    if "speak" in user_input:
        sd.play(data=audio, samplerate=sample_rate)
        sd.wait(ignore_errors=True)