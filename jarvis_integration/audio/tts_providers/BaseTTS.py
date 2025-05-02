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

import time
import asyncio
import logging
from abc import abstractmethod
from typing import Optional, Dict
from collections import defaultdict
from langdetect import detect, DetectorFactory
from transformers import pipeline
import re
import inflect
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet, stopwords
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
from translate import Translator


# Initialize necessary tools
lemmatizer = WordNetLemmatizer()
p = inflect.engine()
stop_words = set(stopwords.words('english'))
DetectorFactory.seed = 0  # Ensures consistent language detection results

# Extended abbreviation mapping
abbreviation_mapping = {
    "u": "you", "r": "are", "btw": "between", "lol": "laugh out loud", "omg": "oh my god",
    "idk": "I don't know", "brb": "be right back", "smh": "shaking my head", "tbh": "to be honest",
    "gr8": "great", "plz": "please", "thx": "thanks", "won't": "will not", "can't": "cannot",
    "n't": "not", "'ve": "have", "'ll": "will", "'re": "are", "'d": "would", "bcuz": "because",
    "don't": "do not", "'s": "is", "bro": "brother"
}


class BaseText2Speech:
    def __init__(self, primary_provider=None, secondary_provider=None):
        self.primary_provider: BaseText2Speech = primary_provider
        self.secondary_provider: BaseText2Speech = secondary_provider
        self.sessions = {}
        self.task_queue = asyncio.Queue()
        self.priorities = asyncio.PriorityQueue()
        self.user_statistics = defaultdict(lambda: {"total_requests": 0, "languages": defaultdict(int)})
        self.language_support = ["en", "es", "fr", "de", "zh", "ar", "ru", "jp"]
        self.custom_voice_models = {}
        self.ssml_support = True
        self.sentiment_analysis_enabled = True
        self.feedback_system = {}
        self.usage_limits = {"free": 100, "premium": 1000}

    def start_session(self, session_id: str):
        self.sessions[session_id] = {"start_time": time.time()}
        logging.info(f"Session {session_id} started.")

    def end_session(self, session_id: str):
        if session_id in self.sessions:
            duration = time.time() - self.sessions.pop(session_id)["start_time"]
            logging.info(f"Session {session_id} ended. Duration: {duration:.2f} seconds")
        else:
            logging.warning(f"Session {session_id} not found.")

    async def real_time_stream(self, text: str, voice: Optional[str] = None):
        for segment in self.process_text_in_batches(text):
            audio_data = await self.stream_synthesize(segment, voice)
            yield audio_data

    async def stream_synthesize(self, text: str, voice: Optional[str]):
        audio_data = self.synthesize(text)
        await asyncio.sleep(min(len(text) * 0.01, 1.5))  # Adaptive delay
        return audio_data

    def prioritize_request(self, user_id: str, text: str, voice: str, priority: int):
        self.priorities.put_nowait((priority, (text, voice, user_id)))

    def translate_text(self, text: str, target_language: str) -> str:
        try:
            translator = Translator(to_lang=target_language)
            return translator.translate(text)
        except Exception as e:
            logging.error(f"Translation error: {e}")
            return text

    def run(self, text: str, types="normal", lang="en"):
        if types != "normal":
            if self.ssml_support and "<speak>" in text:
                logging.info("Processing SSML input.")
            if lang != "en":
                detected_lang = self.detect_language(text)
                text = self.normalize_text(text, detected_lang)
                text = self.translate_text(text, lang)
                logging.info(f"Translated text: {text}")
        return self.synthesize(text)

    @abstractmethod
    def synthesize(self, text: str):
        pass

    def apply_sentiment_analysis(self, text: str) -> Dict[str, float]:
        sentiment_pipeline = pipeline("sentiment-analysis")
        result = sentiment_pipeline(text)[0]
        tone = result['label'].lower()
        pitch = 1.5 if tone == 'positive' else 0.5 if tone == 'negative' else 1.0
        return {"tone": tone, "pitch": pitch}

    def expand_abbreviations(self, text):
        words = text.split()
        return ' '.join([abbreviation_mapping.get(word.lower(), word) for word in words])

    def convert_numbers(self, text):
        def replace_number(match):
            return p.number_to_words(match.group())
        text = re.sub(r'\b\d+\b', replace_number, text)
        text = re.sub(r'\$(\d+)', lambda m: f"{p.number_to_words(m.group(1))} dollars", text)
        text = re.sub(r'(\d+)%', lambda m: f"{p.number_to_words(m.group(1))} percent", text)
        return text

    def remove_punctuation(self, text):
        return re.sub(r'[^\w\s.?!]', '', text)

    def get_wordnet_pos(self, treebank_tag):
        return {"J": wordnet.ADJ, "V": wordnet.VERB, "N": wordnet.NOUN, "R": wordnet.ADV}.get(treebank_tag[0], wordnet.NOUN)

    def normalize_text(self, text: str, language: str) -> str:
        text = text.lower()
        text = self.expand_abbreviations(text)
        text = self.convert_numbers(text)
        text = self.remove_punctuation(text)
        tokens = word_tokenize(text)
        pos_tags = pos_tag(tokens)
        lemmatized_tokens = [lemmatizer.lemmatize(token, self.get_wordnet_pos(tag)) for token, tag in pos_tags]
        return ' '.join([token for token in lemmatized_tokens if token not in stop_words]).strip()

    def detect_language(self, text: str) -> str:
        try:
            return detect(text)
        except Exception as e:
            logging.error(f"Language detection error: {e}")
            return "en"
