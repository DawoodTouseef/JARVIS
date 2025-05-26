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

from jarvis_integration.models.users import Users
from jarvis_integration.models.preferences import Preferences
from config import  Model, SessionManager
from typing import Optional
from langchain_openai import ChatOpenAI

def get_model_from_database() -> Optional[Model]:
    """
    Retrieve the LLM model configuration from the preference table for the current user.

    Returns:
        Optional[Model]: The Model object if found, otherwise None.
    """
    try:
        # Load session and get user email
        session = SessionManager()
        session.load_session()
        email = session.get_email()
        if not email:
            return None

        # Fetch user by email
        user = Users.get_user_by_email(email)
        if not user:
            return None

        # Fetch LLM model preference
        llm_prefs = Preferences.get_preferences_by_user_id(user.id)
        existing_pref = next((pref for pref in llm_prefs if pref.setting_key == "llm_model"), None)
        if not existing_pref or not existing_pref.setting_value:
            return None

        # Validate and return the model
        model = Model.model_validate(existing_pref.setting_value)
        return model

    except Exception as e:
        # Log error if needed, but return None to handle gracefully
        print(f"Error retrieving model from database: {e}")
        return None

def get_vision_model_from_database()->Optional[Model]:
        """
        Retrieve the LLM model configuration from the preference table for the current user.

        Returns:
            Optional[Model]: The Model object if found, otherwise None.
        """
        try:
            # Load session and get user email
            session = SessionManager()
            session.load_session()
            email = session.get_email()
            if not email:
                return None

            # Fetch user by email
            user = Users.get_user_by_email(email)
            if not user:
                return None

            # Fetch LLM model preference
            llm_prefs = Preferences.get_preferences_by_user_id(user.id)
            existing_pref = next((pref for pref in llm_prefs if pref.setting_key == "vision_model"), None)
            if not existing_pref or not existing_pref.setting_value:
                return None

            # Validate and return the model
            model = Model.model_validate(existing_pref.setting_value)
            return model

        except Exception as e:
            # Log error if needed, but return None to handle gracefully
            print(f"Error retrieving model from database: {e}")
            return None


def get_model():
    """
    :return:
    """
    model=get_model_from_database()
    if model is not None:
        chat=ChatOpenAI(
            model_name=model.name,
            openai_api_base=model.url,
            openai_api_key=model.api_key,
        )
        return chat
    else:
        return None

