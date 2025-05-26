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

from colorama import Fore, init

# Initialize colorama for cross-platform support
init(autoreset=True)

class STTException(Exception):
    def __init__(self, messages: str = None, status_code: int = None):
        super().__init__(messages)  # Pass the message to the base class
        self.status_code = status_code  # Store the status code as an instance variable

    def __str__(self):
        return Fore.RED + (self.args[0] if self.args else "An STT error occurred") + Fore.RESET
