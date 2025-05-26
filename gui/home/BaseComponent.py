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
from jarvis_integration.models.preferences import Preferences

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class BaseComponent(ABC):
    """
    Base class for generic virtual assistant components.
    Subclasses must implement initialize and get_metadata.
    """

    def __init__(self, user_id=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.user_id = user_id

    @abstractmethod
    def initialize(self, **kwargs):
        """
        Initialize the component with configuration parameters.
        :param kwargs: Configuration parameters
        """
        pass

    @abstractmethod
    def get_metadata(self) -> dict:
        """
        Return metadata about the component.
        :return: Dictionary with keys like 'name', 'version', 'description', 'type'
        """
        pass

    def get_component_name(self) -> str:
        """
        Get the name of the component for logging and identification.
        :return: Component name as a string
        """
        return self.__class__.__name__

    def get_configuration(self) -> dict:
        """
        Retrieve component configuration from the database.
        :return: Dictionary of configuration key-value pairs
        """
        try:
            setting_key = f"component_hub_config_{self.get_metadata()['type']}_{self.get_metadata()['name']}"
            preferences = Preferences.get_preferences_by_user_id(self.user_id)
            for pref in preferences:
                if pref.setting_key == setting_key:
                    return pref.setting_value or {}
            return {}
        except Exception as e:
            self.logger.error(f"Failed to retrieve configuration: {e}")
            return {}