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
import os
import logging
import sys
from pathlib import Path
import shutil
from pydantic import BaseModel
import threading
import json
import keyring
from datetime import datetime, timedelta

stop_event = threading.Event()

VERSION="0.0.1"

class Model(BaseModel):
    name:str
    type:str
    url:str=None
    api_key:str=None
####################################
# Load .env file
####################################
JARVIS_DIR = Path(__file__).parent  # the path containing this file
SESSION_PATH=os.path.join(Path.home(),".cache","jarvis")
SESSION_FILE=os.path.join(SESSION_PATH,"session.json")
PLUGIN_DIR=os.path.join(SESSION_PATH,"components","alert_plugin")
if not os.path.exists(PLUGIN_DIR):
    os.makedirs(PLUGIN_DIR,exist_ok=True)
TOOLS=[]
ALLOW_DANGEROUS_REQUEST = True
if not os.path.exists(SESSION_PATH):
    os.makedirs(SESSION_PATH,exist_ok=True)
try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(str(JARVIS_DIR / ".env")))
except ImportError:
    print("dotenv not installed, skipping...")


####################################
# LOGGING
####################################
LOG_DIR = os.path.join(JARVIS_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app.log")

log_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
GLOBAL_LOG_LEVEL = os.environ.get("GLOBAL_LOG_LEVEL", "INFO").upper()
if GLOBAL_LOG_LEVEL not in log_levels:
    GLOBAL_LOG_LEVEL = "INFO"

# Remove all handlers associated with the root logger
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configure root logger manually
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, GLOBAL_LOG_LEVEL))
formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] - %(threadName)s - %(message)s")

file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)

log = logging.getLogger("MainLogger")
log.setLevel(getattr(logging, GLOBAL_LOG_LEVEL))
log.propagate = False
log.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")

log_sources = ["DB", "MAIN", "AGENTS", "GUI", "AUDIO", "VISION","MEMORY","SIGNUP","LOGIN","COMPONENT_HUB"]
SRC_LOG_LEVELS = {}
loggers = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    source_log_level = os.environ.get(log_env_var, GLOBAL_LOG_LEVEL).upper()
    if source_log_level not in log_levels:
        source_log_level = GLOBAL_LOG_LEVEL

    source_logger = logging.getLogger(source)
    source_logger.setLevel(getattr(logging, source_log_level))
    source_logger.propagate = True

    SRC_LOG_LEVELS[source] = source_log_level
    loggers[source] = source_logger
    log.info(f"{log_env_var}: {source_log_level}")


###########################
# ENV (dev,test,prod)
####################################

ENV = os.environ.get("ENV", "dev")


####################################
# DATA/FRONTEND BUILD DIR
####################################

DATA_DIR = Path(os.getenv("DATA_DIR", JARVIS_DIR / "data")).resolve()

NEW_DATA_DIR = Path(os.getenv("DATA_DIR", JARVIS_DIR / "data")).resolve()
NEW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if the data directory exists in the package directory
if DATA_DIR.exists() and DATA_DIR != NEW_DATA_DIR:
    log.info(f"Moving {DATA_DIR} to {NEW_DATA_DIR}")
    for item in DATA_DIR.iterdir():
        dest = NEW_DATA_DIR / item.name
        if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    DATA_DIR = Path(os.getenv("DATA_DIR", JARVIS_DIR / "data"))


####################################
# Database
####################################

# Check if the file exists
if os.path.exists(f"{DATA_DIR}/application.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/application.db", f"{DATA_DIR}/jarvis.db")
    log.info("Database migrated from Ollama-WebUI successfully.")
else:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/jarvis.db")

# Replace the postgres:// with postgresql://
if "postgres://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

SCREENSHOT_PATH=DATA_DIR / "screenshot" / "screenshot_with_text.png"
MIC_RECORD_LOCATION = DATA_DIR / "cache"/ "audio" / "mic_record.wav"
SYSTEM_SOUND_LOCATION = DATA_DIR / "system_sound.wav"
JUST_SCREENSHOT_PATH = DATA_DIR / "screenshot" /"screenshot.png"

class SessionManager:
    def __init__(self):
        self.session_data = {}
        self.session_timeout = timedelta(minutes=480)  # Session expiry time

    def create_session(self, email):
        """Create a new session and store it."""
        self.session_data = {
            "email": email,
            "token": f"token_{email}_{int(datetime.now().timestamp())}",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + self.session_timeout).isoformat()
        }
        # Save session to file
        with open(SESSION_FILE, 'w') as f:
            json.dump(self.session_data, f)
        # Optionally store token in keyring for security
        keyring.set_password("MyApp", email, self.session_data["token"])

    def load_session(self):
        """Load session from file and validate."""
        if not os.path.exists(SESSION_FILE):
            return False
        try:
            with open(SESSION_FILE, 'r') as f:
                self.session_data = json.load(f)
            # Check if session is still valid
            expiry = datetime.fromisoformat(self.session_data["expires_at"])
            if datetime.now() > expiry:
                self.clear_session()
                return False
            # Verify token in keyring
            stored_token = keyring.get_password("MyApp", self.session_data["email"])
            if stored_token != self.session_data["token"]:
                self.clear_session()
                return False
            return True
        except (json.JSONDecodeError, KeyError):
            self.clear_session()
            return False

    def clear_session(self):
        """Clear session data."""
        self.session_data = {}
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        # Clear token from keyring
        if self.session_data.get("email"):
            keyring.delete_password("MyApp", self.session_data["email"])

    def is_authenticated(self):
        """Check if a valid session exists."""
        return bool(self.session_data and self.load_session())

    def get_email(self):
        """Get the current user's username."""
        return self.session_data.get("email", "")