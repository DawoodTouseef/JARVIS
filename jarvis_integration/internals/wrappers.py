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

import logging
from contextvars import ContextVar

from config import SRC_LOG_LEVELS
from peewee import PostgresqlDatabase, SqliteDatabase, OperationalError, InterfaceError
from peewee import InterfaceError as PeeWeeInterfaceError
from playhouse.db_url import connect, parse
from playhouse.shortcuts import ReconnectMixin

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

db_state_default = {"closed": None, "conn": None, "ctx": None, "transactions": None}
db_state = ContextVar("db_state", default=db_state_default.copy())

class PeeweeConnectionState:
    def __init__(self, **kwargs):
        self._state = db_state
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        return self._state.get()[name]

class CustomReconnectMixin(ReconnectMixin):
    reconnect_errors = (
        (OperationalError, "termin"),
        (InterfaceError, "closed"),
        (PeeWeeInterfaceError, "closed"),
    )

class ReconnectingPostgresqlDatabase(CustomReconnectMixin, PostgresqlDatabase):
    pass

def register_connection(db_url):
    try:
        db = connect(db_url, unquote_password=True)
        if isinstance(db, PostgresqlDatabase):
            connection = parse(db_url, unquote_password=True)
            db = ReconnectingPostgresqlDatabase(**connection)
            db.connect(reuse_if_open=True)
            db.autoconnect = True
            db.reuse_if_open = True
            log.info("Connected to PostgreSQL database")
        elif isinstance(db, SqliteDatabase):
            db.autoconnect = True
            db.reuse_if_open = True
            log.info("Connected to SQLite database")
        else:
            raise ValueError("Unsupported database type")
        return db
    except Exception as e:
        log.error(f"Failed to register database connection: {e}")
        raise