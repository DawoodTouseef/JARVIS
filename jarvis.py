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

import sys
import json
import os
import uuid

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError
from gui.login import AnimatedLoginPage
from gui.signup import SignupPage
from gui.AssistantGUI import AssistantGUI
from config import JARVIS_DIR, DATABASE_URL, SESSION_PATH,loggers
from utils.models.users import Users

# Set up logging
log = loggers["MAIN"]

MIGRATIONS_PATH = JARVIS_DIR / "migrations"

# Environment variable for user agent
os.environ['USER_AGENT'] = "lang-chain-framework-builtin"


# --------------------------- DATABASE MIGRATION HANDLING --------------------------- #

def add_missing_imports():
    """Ensures required imports exist in Alembic migration files."""
    versions_path = MIGRATIONS_PATH / "versions"

    for _, _, filenames in os.walk(versions_path):
        for filename in filenames:
            if filename.endswith(".py"):
                file_path = os.path.join(versions_path, filename)

                with open(file_path, "r") as f:
                    content = f.read()

                if "import utils" not in content:
                    with open(file_path, "w") as f:
                        f.write("import utils\n" + content)


def database_initialized(engine):
    """Checks if the database schema exists and is being tracked by Alembic."""
    try:
        inspector = inspect(engine)
        return "alembic_version" in inspector.get_table_names()
    except OperationalError:
        return False


def detect_table_changes():
    """Detects if tables or columns were modified in models and require migration."""
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)

        # Fetch current database tables
        existing_tables = set(inspector.get_table_names())

        # Check if new tables exist in models that are missing in DB
        from utils.internals.db import Base  # Import your SQLAlchemy models
        model_tables = {table.name for table in Base.metadata.tables.values()}

        if model_tables - existing_tables:
            log.info(f"New tables detected: {model_tables - existing_tables}")
            return True

        # Check if table structure changed
        for table in model_tables.intersection(existing_tables):
            db_columns = {col["name"] for col in inspector.get_columns(table)}
            model_columns = {col.name for col in Base.metadata.tables[table].columns}

            if model_columns - db_columns:
                log.info(f"New columns detected in {table}: {model_columns - db_columns}")
                return True

        return False  # No changes detected

    except Exception as e:
        log.error(f"Table modification detection failed: {e}")
        return True  # Assume migration needed if error occurs


def run_migrations():
    """Runs Alembic migrations, generating new revisions if table changes are detected."""
    log.info("Checking database migration status...")

    try:
        alembic_cfg = Config(JARVIS_DIR / "alembic.ini")
        alembic_cfg.set_main_option("script_location", str(MIGRATIONS_PATH))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        engine = create_engine(DATABASE_URL)

        # Initialize Alembic if not set up
        if not MIGRATIONS_PATH.exists():
            log.info("Initializing Alembic for the first time...")
            command.init(alembic_cfg, str(MIGRATIONS_PATH))
            command.revision(alembic_cfg, message="Initial database setup", autogenerate=True)
            add_missing_imports()

        # Apply initial migrations if DB is uninitialized
        if not database_initialized(engine):
            log.info("Database is not initialized. Running initial migration...")
            command.upgrade(alembic_cfg, "head")
            return

        # Detect table structure changes
        if detect_table_changes():
            log.info("Schema changes detected. Generating migration script...")
            command.revision(alembic_cfg, message=f"Auto migration {uuid.uuid4()}", autogenerate=True)
            add_missing_imports()

        # Apply migrations
        log.info("Applying latest migrations...")
        command.upgrade(alembic_cfg, "head")
        log.info("Database migration completed successfully!")

    except Exception as e:
        log.error(f"Migration process failed: {e}")


# --------------------------- APPLICATION HANDLING --------------------------- #

class ApplicationManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.set_application_icon()

        # Check for existing session
        if self.is_logged_in():
            self.main_window = AssistantGUI(self.logout_and_show_login)
            self.current_page = self.main_window
            self.login_page = AnimatedLoginPage(self.show_main_window, self.show_signup_page)
            self.signup_page = SignupPage(self.show_login_page)
        else:
            self.login_page = AnimatedLoginPage(self.show_main_window, self.show_signup_page)
            self.signup_page = SignupPage(self.show_login_page)
            self.current_page = self.login_page

        self.current_page.show()

    def set_application_icon(self):
        """Sets the application window icon."""
        try:
            icon_path = os.path.join(JARVIS_DIR, "icons", "jarvis-logo1.svg")
            if os.path.exists(icon_path):
                self.app.setWindowIcon(QIcon(icon_path))
            else:
                log.warning("Application icon not found.")
        except Exception as e:
            log.error(f"Failed to set application icon: {e}")

    def is_logged_in(self):
        """Check if a session file exists and is valid."""
        session_file = os.path.join(SESSION_PATH, "session.json")
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as file:
                    session_data = json.load(file)
                    if session_data.get("email"):
                        user = Users.get_user_by_email(session_data.get("email"))
                        if user:
                            return True
                        os.remove(session_file)
            except (json.JSONDecodeError, FileNotFoundError):
                log.error("Corrupted or missing session file.")
        return False

    def show_login_page(self):
        self.current_page.close()
        self.current_page = self.login_page
        self.current_page.show()

    def show_signup_page(self):
        self.current_page.close()
        self.current_page = self.signup_page
        self.current_page.show()

    def show_main_window(self):
        self.current_page.close()
        self.main_window = AssistantGUI(self.show_login_page)
        self.current_page = self.main_window
        self.current_page.show()

    def logout_and_show_login(self):
        """Logout the user and delete session data."""
        session_file = os.path.join(SESSION_PATH, "session.json")
        if os.path.exists(session_file):
            os.remove(session_file)
        self.show_login_page()

    def run(self):
        sys.exit(self.app.exec_())

