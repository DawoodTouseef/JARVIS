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
from audio.stt_providers.exception import STTException


# In-memory cache for transcriptions to avoid redundant processing
transcription_cache = {}

# Configure logging with timestamps and other details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class BaseSpeech2Text(ABC):
    """
    Enhanced Speech-To-Text (STT) provider with advanced features including
    session management, multi-language support, plugins, error handling, real-time updates, and more.
    """

    def __init__(self):
        self.language = os.getenv("STT_LANGUAGE", "en-US")  # Default language from environment variable
        self.audio_format = os.getenv("STT_AUDIO_FORMAT", "wav")  # Default audio format
        self.timeout = int(os.getenv("STT_TIMEOUT", 30))  # Timeout for transcription
        self.retry_attempts = int(os.getenv("STT_RETRY_ATTEMPTS", 3))  # Retry attempts
        self.retry_delay = int(os.getenv("STT_RETRY_DELAY", 2))  # Delay between retries
        self.streaming_enabled = False  # Streaming support
        self.secondary_provider = None  # Optional fallback provider
        self.log_level = logging.INFO  # Default log level
        self.event_hooks = {"pre_transcribe": None, "post_transcribe": None}  # Event hooks
        self.supported_languages = os.getenv("STT_SUPPORTED_LANGUAGES", "en-US,es-ES,fr-FR").split(",")  # Supported languages
        self.confidence_threshold = 0.75  # Confidence threshold
        self.plugins = defaultdict(list)  # Plugins storage
        self.sessions = {}  # Active sessions tracking
        self.max_concurrent_requests = int(os.getenv("STT_MAX_CONCURRENT_REQUESTS", 10))  # Concurrent request limit
        self.concurrency_semaphore = threading.Semaphore(self.max_concurrent_requests)
        self.rate_limit = int(os.getenv("STT_RATE_LIMIT", 5))  # Rate limiting
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_requests)
        self.transcription_history = []  # Store history of transcriptions
        self.user_auth = {}  # Basic user authentication

    def __enter__(self):
        logging.info(f"Initializing {self.get_provider_name()} STT provider.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info(f"Shutting down {self.get_provider_name()} STT provider.")
        self.executor.shutdown()

    def _cache_audio(func):
        """
        Decorator to cache transcription results.
        """
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
        """
        Transcribe the given audio data and return the recognized text and confidence score.
        :param audio_data: Audio data in bytes format
        :param streaming: If True, handle streaming transcription
        :return: A dictionary with keys 'text' and optionally 'confidence'
        """
        pass

    @abstractmethod
    def configure(self, **kwargs):
        """
        Configure the provider with necessary parameters like API keys or settings.
        This can be customized based on the provider's requirements.
        :param kwargs: Configuration parameters
        """
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
        self.transcription_history.append(transcription)  # Save to history

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
        """
        Transcribe multiple audio files in a batch.
        :param audio_data_list: List of audio data (each element is bytes)
        :param streaming: Whether to enable streaming (default is False)
        :return: List of transcribed results, each a dictionary
        """
        logging.info(f"Transcribing a batch of {len(audio_data_list)} audio files.")
        results = []
        for audio_data in audio_data_list:
            results.append(self.transcribe(audio_data, streaming))
        return results

    def get_provider_name(self) -> str:
        """
        Get the name of the STT provider (used for logging and identification).
        :return: Provider name as a string
        """
        return self.__class__.__name__

    def process_with_plugins(self, hook_type: str, data: Union[bytes, str]) -> Union[bytes, str]:
        """
        Process the input data using registered plugins for a specific hook type.
        :param hook_type: Either 'pre_transcribe' or 'post_transcribe'
        :param data: Data to be processed (audio bytes or transcription string)
        :return: Processed data after all plugins are applied
        """
        if hook_type in self.plugins:
            for plugin in self.plugins[hook_type]:
                data = plugin(data)
        return data


    async def stream_transcription(self, audio_data: bytes):
        """
        Simulate streaming transcription updates.
        :param audio_data: Audio data in bytes format
        """
        logging.info("Starting streaming transcription.")
        try:
            for i in range(10):  # Simulate 10 updates
                await asyncio.sleep(1)  # Simulate processing time
                update = self.transcribe(audio_data)
                logging.info(f"Streaming update: {update}")
                self.log_transcription(update)
        except Exception as e:
            self.handle_error(str(e))





