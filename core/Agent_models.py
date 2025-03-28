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