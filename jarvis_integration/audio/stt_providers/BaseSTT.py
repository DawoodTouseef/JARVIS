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

from abc import ABC, abstractmethod
import logging
import time
import hashlib
import asyncio
from typing import List, Dict, Optional, Union, Callable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from collections import defaultdict
import threading
from pathlib import Path as File
import os
from jarvis_integration.audio.stt_providers.exception import STTException
from jarvis_integration.models.preferences import Preferences

transcription_cache = {}
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class BaseSpeech2Text(ABC):
    """
    Enhanced Speech-To-Text (STT) provider with advanced features.
    """

    def __init__(self, user_id=None):
        self.language = os.getenv("STT_LANGUAGE", "en-US")
        self.audio_format = os.getenv("STT_AUDIO_FORMAT", "wav")
        self.timeout = int(os.getenv("STT_TIMEOUT", 30))
        self.retry_attempts = int(os.getenv("STT_RETRY_ATTEMPTS", 3))
        self.retry_delay = int(os.getenv("STT_RETRY_DELAY", 2))
        self.streaming_enabled = False
        self.secondary_provider = None
        self.log_level = logging.INFO
        self.event_hooks = {"pre_transcribe": None, "post_transcribe": None}
        self.supported_languages = os.getenv("STT_SUPPORTED_LANGUAGES", "en-US,es-ES,fr-FR").split(",")
        self.confidence_threshold = 0.75
        self.plugins = defaultdict(list)
        self.sessions = {}
        self.max_concurrent_requests = int(os.getenv("STT_MAX_CONCURRENT_REQUESTS", 10))
        self.concurrency_semaphore = threading.Semaphore(self.max_concurrent_requests)
        self.rate_limit = int(os.getenv("STT_RATE_LIMIT", 5))
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_requests)
        self.transcription_history = []
        self.user_auth = {}
        self.user_id = user_id or "default_user"
        self.logger = logging.getLogger(self.__class__.__name__)

    def __enter__(self):
        logging.info(f"Initializing {self.get_provider_name()} STT provider.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info(f"Shutting down {self.get_provider_name()} STT provider.")
        self.executor.shutdown()

    def _cache_audio(func):
        @wraps(func)
        def wrapper(self, audio_data: bytes, *args, **kwargs):
            cache_key = hashlib.sha256(audio_data).hexdigest()
            if cache_key in transcription_cache:
                logging.info("Transcription result retrieved from cache.")
                return transcription_cache[cache_key]
            result = func(self, audio_data, *args, **kwargs)
            transcription_cache[cache_key] = result
            return result
        return wrapper

    @abstractmethod
    def transcribe(self, audio_data: File, streaming: bool = False) -> Dict[str, Union[str, float]]:
        pass

    @abstractmethod
    def configure(self, **kwargs):
        pass

    def set_language(self, language_code: str):
        if language_code in self.supported_languages:
            self.language = language_code
            logging.info(f"Language set to {self.language}")
        else:
            raise STTException(f"Unsupported language: {language_code}")

    def set_audio_format(self, audio_format: str):
        self.audio_format = audio_format
        logging.info(f"Audio format set to {self.audio_format}")

    def set_timeout(self, timeout: int):
        self.timeout = timeout
        logging.info(f"Timeout set to {self.timeout} seconds")

    def enable_streaming(self, enable: bool = True):
        self.streaming_enabled = enable
        status = "enabled" if enable else "disabled"
        logging.info(f"Streaming {status}")

    def set_retry_delay(self, delay: int):
        self.retry_delay = delay
        logging.info(f"Retry delay set to {self.retry_delay} seconds")

    def set_log_level(self, level: int):
        self.log_level = level
        logging.getLogger().setLevel(level)
        logging.info(f"Log level set to {logging.getLevelName(self.log_level)}")

    def set_confidence_threshold(self, threshold: float):
        if 0 <= threshold <= 1:
            self.confidence_threshold = threshold
            logging.info(f"Confidence threshold set to {self.confidence_threshold}")
        else:
            raise STTException("Invalid confidence threshold. Must be between 0 and 1.")

    def log_transcription(self, transcription: dict):
        logging.info(f"Transcription: {transcription['text']}")
        if 'confidence' in transcription:
            logging.info(f"Confidence score: {transcription['confidence']}")
        self.transcription_history.append(transcription)

    def handle_error(self, error_message: str):
        logging.error(f"Error during transcription: {error_message}")
        raise STTException(error_message)

    def retry_transcription(self, func: Callable, audio_data: bytes, attempts: Optional[int] = None, **kwargs):
        if attempts is None:
            attempts = self.retry_attempts
        last_exception = None
        for attempt in range(1, attempts + 1):
            try:
                logging.info(f"Attempt {attempt} of {attempts}")
                return func(audio_data, **kwargs)
            except Exception as e:
                last_exception = e
                logging.warning(f"Retry {attempt} failed with error: {e}")
                time.sleep(self.retry_delay)
        raise STTException(f"Failed after {attempts} attempts") from last_exception

    def batch_transcribe(self, audio_data_list: List[bytes], streaming: bool = False) -> List[Dict[str, Union[str, float]]]:
        logging.info(f"Transcribing a batch of {len(audio_data_list)} audio files.")
        results = []
        for audio_data in audio_data_list:
            results.append(self.transcribe(audio_data, streaming))
        return results

    def get_provider_name(self) -> str:
        return self.__class__.__name__

    def process_with_plugins(self, hook_type: str, data: Union[bytes, str]) -> Union[bytes, str]:
        if hook_type in self.plugins:
            for plugin in self.plugins[hook_type]:
                data = plugin(data)
        return data

    async def stream_transcription(self, audio_data: bytes):
        logging.info("Starting streaming transcription.")
        try:
            for i in range(10):
                await asyncio.sleep(1)
                update = self.transcribe(audio_data)
                logging.info(f"Streaming update: {update}")
                self.log_transcription(update)
        except Exception as e:
            self.handle_error(str(e))

    def get_configuration(self) -> dict:
        """
        Retrieve component configuration from the database.
        :return: Dictionary of configuration key-value pairs
        """
        try:
            setting_key = f"component_hub_config_speech_{self.get_provider_name()}"
            preferences = Preferences.get_preferences_by_user_id(self.user_id)
            for pref in preferences:
                if pref.setting_key == setting_key:
                    return pref.setting_value or {}
            return {}
        except Exception as e:
            self.logger.error(f"Failed to retrieve configuration: {e}")
            return {}