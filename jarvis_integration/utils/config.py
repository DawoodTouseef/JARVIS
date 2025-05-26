import os
from pathlib import Path


JARVIS_DIR = Path(__file__).parent.parent.parent  # the path containing this file
DATA_DIR = Path(os.getenv("DATA_DIR", JARVIS_DIR / "data")).resolve()
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/jarvis.db")

# Replace the postgres:// with postgresql://
if "postgres://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")



