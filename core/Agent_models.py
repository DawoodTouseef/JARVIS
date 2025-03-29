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

from utils.models.users import Users
from config import SESSION_PATH
import json
import os
from config import Model
from typing import Optional
from langchain_openai import ChatOpenAI

def get_model_from_database()->Optional[Model]:
    """

    :return:
    """
    session_json=os.path.join(SESSION_PATH,"session.json")
    if os.path.exists(os.path.join(SESSION_PATH,"session.json")):
        with open(session_json,"r") as f:
            data=json.load(f)
        if "email" in data:
            users=Users.get_user_by_email(data.get("email"))
            if users:
                if users.settings is not None:
                    settings = json.loads(users.settings.json())
                    if "model" in settings:
                        model_dict=settings['model']
                        model=Model.model_validate(model_dict)
                        return model
    else:
        return None
def get_vision_model_from_database()->Optional[Model]:
    """

    :return:
    """
    session_json=os.path.join(SESSION_PATH,"session.json")
    if os.path.exists(os.path.join(SESSION_PATH,"session.json")):
        with open(session_json,"r") as f:
            data=json.load(f)
        if "email" in data:
            users=Users.get_user_by_email(data.get("email"))
            if users:
                if users.settings is not None:
                    settings = json.loads(users.settings.json())
                    if "vision" in settings:
                        model_dict=settings['vision']
                        model=Model.model_validate(model_dict)
                        return model
    else:
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