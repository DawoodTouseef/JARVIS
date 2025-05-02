from deep_translator import GoogleTranslator,MyMemoryTranslator
from jarvis_integration.models.users import Users
from config import SESSION_PATH
import os
import json

class Translator:
    """Simple Translator using Google Translate API."""
    def __init__(self, source_lang='auto', target_lang='en'):
        """
        :param source_lang: Language to translate from (default 'auto' detects language)
        :param target_lang: Language to translate to (default 'en' for English)
        """
        self.source_lang = source_lang
        self.target_lang = target_lang

    def translate(self, text: str) -> str:
        """
        Translate a given text from source_lang to target_lang.
        :param text: The text to be translated
        :return: Translated text
        """
        try:
            translated_text = MyMemoryTranslator(
                source=self.source_lang,
                target=self.target_lang
            ).translate(text)
            return translated_text
        except Exception as e:
            try:
                translated_text = GoogleTranslator(
                    source="auto",
                    target=self.target_lang
                ).translate(text)
                return translated_text
            except Exception as e:
                return text

    def set_target_language(self, lang_code: str):
        """Change target language dynamically."""
        self.target_lang = lang_code

    def set_source_language(self, lang_code: str):
        """Change source language dynamically."""
        self.source_lang = lang_code

def _create_translate(from_lang = "en-US",text=None):
    from_lang = "en-US"
    to_lang = "en-US"
    try:
        session_file = os.path.join(SESSION_PATH, "session.json")
        if os.path.exists(session_file):
            with open(session_file, "r") as f:
                data = json.load(f)
        else:
            data = {}
        if "email" in data:
            users = Users.get_user_by_email(data["email"])
            if users:
                if users.settings is None:
                    users.settings = {}

                if not isinstance(users.settings.json(), dict):
                    users.settings = json.loads(users.settings.json())
                to_lang=users.settings['language']
    except Exception as e:
        pass
    return Translator(source_lang=from_lang,target_lang=to_lang).translate(text)

if __name__=="__main__":
    text="Hello"
    to_lang = "hi-IN"
    print(_create_translate(text=text))