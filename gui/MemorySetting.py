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
import json
from typing import Union, List, Dict, Any

from config import SESSION_PATH
from utils.models.users import Users
from mem0 import MemoryClient, Memory
from core.Agent_models import get_model_from_database
from config import loggers
from datetime import datetime

log=loggers['AGENTS']

class MemorySettings:
    def __init__(self):
        self.users = None
        self.memory = None
        self.user_metadata = {}
        self._initialize_memory()

    def _initialize_memory(self) -> None:
        """Initialize memory based on user settings with enhanced context."""
        try:
            session_file = os.path.join(SESSION_PATH, "session.json")
            if not os.path.exists(session_file):
                log.warning("Session file not found. Creating a default session.")
                os.makedirs(SESSION_PATH, exist_ok=True)
                with open(session_file, "w") as f:
                    json.dump({"email": "default@example.com"}, f)

            with open(session_file, "r") as f:
                data = json.load(f)

            if "email" not in data:
                raise ValueError("No email found in session data.")

            # Fetch user settings
            self.users = Users.get_user_by_email(data["email"])
            if not self.users or not self.users.settings:
                log.warning("User or settings not found. Using default profile.")
                self.users = Users(email=data["email"], name="Unknown", settings=json.dumps({}))

            settings = json.loads(self.users.settings.json())
            memory_settings = settings.get("memory", {})
            api_key = memory_settings.get("api_key", "")
            memory_type = memory_settings.get("memo_engine", "local").lower()

            # Store user metadata for richer context
            self.user_metadata = {
                "user_id": f"{self.users.id}-{self.users.name}" if self.users.id else "unknown",
                "name": self.users.name,
                "email": self.users.email,
                "last_active": datetime.now().isoformat(),
                "preferences": settings.get("preferences", {})
            }

            # Initialize memory based on engine type
            if "online" in memory_type:
                if not api_key:
                    raise ValueError("API key required for online memory.")
                self.memory = MemoryClient(api_key=api_key)
                log.info("Initialized online memory client.")
            else:
                model = get_model_from_database()
                if model is None:
                    log.warning("No model found in database. Memory disabled.")
                    return

                config = {
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": model.name,
                            "openai_base_url": model.url,
                            "api_key": model.api_key
                        }
                    },
                    "embedder": {
                        "provider": "huggingface",
                        "config": {
                            "model": "multi-qa-MiniLM-L6-cos-v1"
                        }
                    },
                    "vector_store": {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "memory",
                            "path": f"{os.path.join(SESSION_PATH, 'memory')}",
                        }
                    }

                }
                self.memory = Memory.from_config(config)
                log.info("Initialized local memory with Chroma vector store.")


        except Exception as e:
            log.error(f"Error initializing memory: {e}")
            self.memory = None

    def add_memory(self, messages: Union[str, List[Dict[str, str]]], *args, **kwargs) -> Dict[str, Any]:
        """Add memory entries with timestamp and metadata."""
        if not self.memory:
            log.error("Memory not initialized.")
            raise RuntimeError("Memory is not initialized.")

        user_id = self.user_metadata.get("user_id", "unknown")
        metadata = kwargs.get("metadata", {})
        metadata.update({
            "timestamp": datetime.now().isoformat(),
            "source": kwargs.get("source", "user_input")
        })
        result = self.memory.add(messages=messages, metadata=metadata, user_id=user_id, *args)
        log.debug(f"Added memory: {messages}")
        return result

    def search_memory(self, query: str, limit: int = 5, *args, **kwargs) -> List[Dict[str, Any]]:
        """Search memory with enhanced context retrieval."""
        if not self.memory:
            log.error("Memory not initialized.")
            raise RuntimeError("Memory is not initialized.")

        user_id = self.user_metadata.get("user_id", "unknown")
        results = self.memory.search(query=query, user_id=user_id, limit=limit, *args, **kwargs)
        log.debug(f"Memory search for '{query}': {len(results)} results")
        return results

    def get_proactive_context(self, current_input: str) -> str:
        """Generate proactive context based on recent memories."""
        if not self.memory:
            return ""

        recent_memories = self.search_memory("recent interactions", limit=3)
        context = "\n".join([f"Recalled: {m['memory']} (at {m['metadata']['timestamp']})" for m in recent_memories])

        # Proactive suggestions based on input and memory
        suggestions = {
            "weather": "Shall I provide the latest weather update?",
            "system": "Would you like a system status report?",
            "schedule": "May I check your upcoming events?"
        }
        for key, suggestion in suggestions.items():
            if key in current_input.lower() or any(key in m["memory"].lower() for m in recent_memories):
                context += f"\nSuggestion: {suggestion}"
                break

        return context if context else "No recent context available."

    def clear_memory(self) -> Any:
        """Clear all memory entries for the user."""
        if not self.memory:
            log.error("Memory not initialized.")
            raise RuntimeError("Memory is not initialized.")

        user_id = self.user_metadata.get("user_id", "unknown")
        log.info(f"Clearing memory for user: {user_id}")
        return self.memory.delete_all(user_id=user_id)

    def update_user_metadata(self, key: str, value: Any) -> None:
        """Update user metadata dynamically."""
        self.user_metadata[key] = value
        self.add_memory(f"Updated user metadata: {key} = {value}", metadata=self.user_metadata)
