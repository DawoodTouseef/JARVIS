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

from transformers import AutoProcessor, AutoModel
import torch
from jarvis_integration.audio.tts_providers.BaseTTS import BaseText2Speech
from config import SRC_LOG_LEVELS,JARVIS_DIR
import sqlite3
import scipy.io.wavfile
from datetime import datetime
import os
import logging
import numpy as np
from scipy.signal import butter, filtfilt, lfilter
import librosa

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])


def download_with_git(path):
    """Download the model using Git if available."""
    try:
        import git
        log.info("Using git to download the model...")
        git.Repo.clone_from("https://huggingface.co/suno/bark-small", to_path=path)
        return True
    except ImportError:
        log.warning("git not installed.")
        return False
    except Exception as e:
        log.error(f"Git cloning failed: {e}")
        return False


def download_with_hf_hub(path):
    """Download the model using Hugging Face Hub if available."""
    try:
        from huggingface_hub import snapshot_download
        log.info("Using huggingface_hub to download the model...")
        snapshot_download("suno/bark-small", local_dir=path)
        return True
    except ImportError:
        log.warning("huggingface_hub not installed.")
        return False
    except Exception as e:
        log.error(f"huggingface_hub download failed: {e}")
        return False


def download_bark():
    """Download the Bark TTS model if not already present."""
    path = os.path.join(JARVIS_DIR, "config", "model", "bark")
    if os.path.exists(path):
        log.info("Model already downloaded.")
        return

    log.info(f"Attempting to download the model to {path} ...")
    if download_with_git(path) or download_with_hf_hub(path):
        log.info("Model downloaded successfully.")
    else:
        log.error("Failed to download the model with both methods.")
        raise RuntimeError("Model download failed")


def apply_robotic_filter(audio, sample_rate):
    """Applies a robotic effect using a low-pass filter and pre-emphasis."""
    # Low-pass filter (softens high frequencies for a more robotic sound)
    cutoff = 2500  # Slightly lower cutoff for a more digital tone
    nyquist = 0.5 * sample_rate
    normal_cutoff = cutoff / nyquist
    b, a = butter(6, normal_cutoff, btype='low', analog=False)
    filtered_audio = filtfilt(b, a, audio)

    # Pre-emphasis filter to enhance clarity
    pre_emphasis = 0.97
    emphasized_audio = lfilter([1, -pre_emphasis], [1], filtered_audio)

    # Normalize volume
    emphasized_audio = emphasized_audio / np.max(np.abs(emphasized_audio))

    return emphasized_audio

def lower_pitch(audio, sr, semitones=-4):
    """Lowers the pitch of the audio by a specified number of semitones."""
    return librosa.effects.pitch_shift(audio, sr=sr, n_steps=semitones)

class BarkTTS(BaseText2Speech):
    def __init__(self, device="cpu"):
        """Initialize the BarkTTS class with a database for caching audio."""
        super().__init__()
        path = os.path.join(JARVIS_DIR, "config", "model", "bark")
        download_bark()
        self.processor = AutoProcessor.from_pretrained(path)
        self.model = AutoModel.from_pretrained(path).to(device)

        # **New Enhanced Prompt for More Jarvis-like Tone**
        self.voice_description = (
            "A deep, authoritative, and slightly robotic British AI assistant with a calm, sophisticated, and refined voice says: "
        )

        self.seed = 42  # Fixed seed for consistency
        self.db_path = os.path.join(JARVIS_DIR,"data","audio_cache.db")
        self.device = device
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with a table to cache audio."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audio_cache (
                    text TEXT PRIMARY KEY,
                    audio BLOB
                )
                """
            )
            conn.commit()

    def _get_voice_description_length(self):
        """Generate and return length of the voice description audio in samples."""
        torch.manual_seed(self.seed)
        inputs = self.processor(
            text=[self.voice_description], return_tensors="pt"
        ).to(self.device)
        speech_values = self.model.generate(**inputs, do_sample=True)
        return speech_values.shape[-1]

    def _fetch_cached_audio(self, text):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT audio FROM audio_cache WHERE text = ?", (text,))
            result = cursor.fetchone()
            return np.frombuffer(result[0], dtype=np.float32) if result else None

    def synthesize(self, text: str):
        """
        Synthesize speech for the given text, retrieving from cache if available
        or generating and caching if not.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT audio FROM audio_cache WHERE text = ?", (text,))
            result = cursor.fetchone()
            if result:
                log.info(f"Audio for '{text}' retrieved from cache.")
                processed_audio = np.frombuffer(result[0], dtype=np.float32)
                return processed_audio, self.model.generation_config.sample_rate

        # Generate new audio if not cached
        log.info(f"Generating audio for '{text}'...")
        N = self._get_voice_description_length()
        combined_text = self.voice_description + text
        log.info(f"Generating audio for '{combined_text}'")
        torch.manual_seed(self.seed)
        inputs = self.processor(text=[combined_text], return_tensors="pt").to(self.device)
        speech_values = self.model.generate(
            **inputs,
            do_sample=True,
        )
        audio = speech_values.cpu().numpy().squeeze()
        trimmed_audio = audio[N:]

        # Apply robotic effect
        processed_audio = apply_robotic_filter(trimmed_audio, self.model.generation_config.sample_rate)
        # Store in cache
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO audio_cache (text, audio) VALUES (?, ?)", (text, processed_audio.tobytes()))
            conn.commit()

        log.info(f"Audio for '{text}' generated and cached.")
        return processed_audio, self.model.generation_config.sample_rate


if __name__ == "__main__":
    print(f"Loading....{datetime.now().time()}")
    tts = BarkTTS(device="cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loaded BarkTTS {datetime.now().time()}")

    actual_text = "It seems your request got a bit... well, let's just say it's as unfinished as a Stark Industries prototype without Tony's final touches. Could you clarify if you're asking about the weather in a specific location? Once you do, I'll have the forecast ready faster than JARVIS can optimize the Arc Reactor. Current System State: - CPU Usage: 28.9% - Memory Usage: 63.1% (10.07/15.95 GB) - Disk Usage: 17.5% (68.26/389.65 GB) - Battery: 98% (Plugged in: True) Looking forward to assisting you, Dawood Touseef!"
    print(f"Generating {datetime.now().time()}")
    audio, sampling_rate = tts.synthesize(actual_text)
    print(f"Generated {datetime.now().time()}")

    scipy.io.wavfile.write("jarvis_voice.wav", rate=sampling_rate, data=audio)
