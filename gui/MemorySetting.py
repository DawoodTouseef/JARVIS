import os
import json
from typing import Union, List, Dict, Any

from config import SESSION_PATH
from utils.models.users import Users
from mem0 import MemoryClient, Memory
from core.Agent_models import get_model_from_database

class MemorySettings:
    def __init__(self):
        super().__init__()
        self.users = None
        self.memory = None
        self._initialize_memory()

    def _initialize_memory(self):
        """Initialize memory based on user settings."""
        try:
            session_file = os.path.join(SESSION_PATH, "session.json")
            if not os.path.exists(session_file):
                raise FileNotFoundError("Session file not found.")

            with open(session_file, "r") as f:
                data = json.load(f)

            if "email" not in data:
                raise ValueError("No email found in session data.")

            # Fetch user settings
            self.users = Users.get_user_by_email(data["email"])
            if not self.users or not self.users.settings:
                raise ValueError("User settings not found.")

            settings = json.loads(self.users.settings.json())
            memory_settings = settings.get("memory", {})
            api_key = memory_settings.get("api_key", "")
            memory_type = memory_settings.get("memo_engine", "").lower()

            # Initialize memory based on the engine type
            if "online" in memory_type:
                if not api_key:
                    raise ValueError("API key is required for online memory.")
                self.memory = MemoryClient(api_key=api_key)
            else:
                model=get_model_from_database()
                if model is not None:
                    config = {
                        "llm": {
                            "provider": "openai",
                            "config": {
                                "model": model.name,
                                "openai_base_url":model.url,
                                "api_key":model.api_key
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
                                "path": f"{os.path.join(SESSION_PATH,'memory')}",
                            }
                        }

                    }
                    self.memory = Memory.from_config(config)
        except Exception as e:
            print(f"Error initializing memory: {e}")
            self.memory = None

    def add_memory(self, messages: Union[str, List[Dict[str, str]]], *args,**kwargs) -> Dict[str, Any]:
        """Add memory entries."""
        if not self.memory:
            raise RuntimeError("Memory is not initialized.")
        user_id = f"{self.users.id}-{self.users.name}" if self.users else "unknown"
        return self.memory.add(messages=messages, metadata=kwargs.get("metadata"), user_id=user_id,*args,**kwargs)

    def search_memory(self, query: str,*args,**kwargs) -> Any:
        """Search memory for a specific query."""
        if not self.memory:
            raise RuntimeError("Memory is not initialized.")
        user_id = f"{self.users.id}-{self.users.name}" if self.users else "unknown"
        return self.memory.search(query=query, user_id=user_id,*args,**kwargs)

    def clear_memory(self) -> Any:
        """Clear all memory entries for the user."""
        if not self.memory:
            raise RuntimeError("Memory is not initialized.")
        user_id = f"{self.users.id}-{self.users.name}" if self.users else "unknown"
        print("Clearing memory for the user.")

        return self.memory.delete_all(user_id=user_id)

