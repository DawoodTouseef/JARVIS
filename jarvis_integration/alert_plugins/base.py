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

from jarvis_integration.models.preferences import Preferences
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class BaseAlertPlugin:
    def __init__(self, db_tool=None, yahoo_tool=None):
        self.db_tool = db_tool
        self.yahoo_tool = yahoo_tool
        self.user_id = "default_user"
        self.logger = logging.getLogger(self.__class__.__name__)

    def check_alerts(self) -> list:
        """
        Override this method in subclasses to return a list of triggered alert messages.
        """
        raise NotImplementedError("Plugin must implement `check_alerts` method.")

    def get_configuration(self) -> dict:
        """
        Retrieve component configuration from the database.
        :return: Dictionary of configuration key-value pairs
        """
        try:
            setting_key = f"component_hub_config_alert_{self.__class__.__name__}"
            preferences = Preferences.get_preferences_by_user_id(self.user_id)
            for pref in preferences:
                if pref.setting_key == setting_key:
                    return pref.setting_value or {}
            return {}
        except Exception as e:
            self.logger.error(f"Failed to retrieve configuration: {e}")
            return {}