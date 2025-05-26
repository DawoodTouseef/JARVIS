from hassapi import Hass
from jarvis_integration.models.preferences import Preferences
from config import SessionManager
from jarvis_integration.models.users import Users
from jarvis_integration.utils.config import JARVIS_DIR
from langchain_core.tools.base import BaseTool

session=SessionManager()
session.load_session()
def get_hass():
    email=session.get_email()
    if email:
        user=Users.get_user_by_email(email)
        if user:
            prefrences=Preferences.get_preferences_by_user_id(user.id)
            hass_config = next((pref for pref in prefrences if pref.setting_key == "hass"), None)
            return hass_config


class HomeAssistant:
    def __init__(self):
        self.ha=None
        self.load_ha()


    def load_ha(self):
        self.base_url=get_hass().setting_value.get("base_url")
        self.token=get_hass().setting_value.get("token")

        self.ha=Hass(hassurl=self.base_url,token=self.token)








