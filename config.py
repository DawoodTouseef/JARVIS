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

stop_event = threading.Event()


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

# Define available log levels
log_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

# Get global log level from environment or default to INFO
GLOBAL_LOG_LEVEL = os.environ.get("GLOBAL_LOG_LEVEL", "INFO").upper()
if GLOBAL_LOG_LEVEL not in log_levels:
    GLOBAL_LOG_LEVEL = "INFO"

# Configure root logger with thread-safe handlers
logging.basicConfig(
    level=getattr(logging, GLOBAL_LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(threadName)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE,mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)

# Create main logger
log = logging.getLogger("MainLogger")
log.setLevel(GLOBAL_LOG_LEVEL)
log.propagate = True  # Ensure propagation to root logger
log.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")

# Define sources and their log levels
log_sources = [
    "DB",
    "MAIN",
    "AGENTS",
    "GUI",
    "AUDIO",
    "VISION"
]

SRC_LOG_LEVELS = {}
loggers = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    source_log_level = os.environ.get(log_env_var, GLOBAL_LOG_LEVEL).upper()

    if source_log_level not in log_levels:
        source_log_level = GLOBAL_LOG_LEVEL

    # Create and configure logger for each source
    source_logger = logging.getLogger(source)
    source_logger.setLevel(getattr(logging, source_log_level))
    source_logger.propagate = True  # Allow messages to reach root logger

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
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/jarvis.db")
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
