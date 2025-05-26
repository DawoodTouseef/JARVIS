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

import json
import logging
from contextlib import contextmanager
from typing import Any, Optional, Callable


from jarvis_integration.internals.wrappers import register_connection
from jarvis_integration.utils.config import  JARVIS_DIR, DATABASE_URL
import os
try:
    from config import SRC_LOG_LEVELS
except ImportError as e:
    log_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
    log_sources = ["DB"]
    loggers = {}
    SRC_LOG_LEVELS={}
    GLOBAL_LOG_LEVEL="INFO"
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

from peewee_migrate import Router
from sqlalchemy import create_engine, types, Dialect
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from typing_extensions import Self
from jarvis_integration.internals.register import register

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

class JSONField(types.TypeDecorator):
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: Dialect) -> Any:
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value: Optional[Any], dialect: Dialect) -> Any:
        return json.loads(value) if value is not None else None

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    def db_value(self, value):
        return json.dumps(value) if value is not None else None

    def python_value(self, value):
        return json.loads(value) if value is not None else None

def handle_peewee_migration(db_url: str):
    db = None
    try:
        migration_url = db_url.replace("postgresql://", "postgres://")
        db = register_connection(migration_url)
        migrate_dir = JARVIS_DIR / "internals" / "migrations"
        migrate_dir.mkdir(parents=True, exist_ok=True)
        router = Router(db, logger=log, migrate_dir=migrate_dir)
        router.run()
    except Exception as e:
        log.error(f"Failed to run Peewee migrations: {e}")
        raise
    finally:
        if db and not db.is_closed():
            db.close()
        assert db is None or db.is_closed(), "Database connection not properly closed"

SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {},
    pool_pre_ping=True if "postgresql" in SQLALCHEMY_DATABASE_URL else False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()
Session = scoped_session(SessionLocal)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    log.info(f"Registered tables: {list(register.keys())}")
    for table_name, table_fn in register.items():
        model = table_fn
        model.metadata.create_all(engine)
        log.info(f"Prepared table: {table_name}")
