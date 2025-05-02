from config import loggers,SessionManager,SESSION_PATH
import os
from mem0 import Memory,MemoryClient
from datetime import datetime
from core.Agent_models import get_model_from_database
from typing import Union,List,Any,Dict
from jarvis_integration.models.users import Users
from jarvis_integration.models.preferences import Preferences

log=loggers['MEMORY']

class MemorySettings:
    def __init__(self):
        self.users = None
        self.memory = None
        self.user_metadata = {}


    def _initialize_memory(self) -> None:
        """Initialize memory based on user settings with enhanced context."""
        try:
            session_file = SessionManager()
            session_file.load_session()
            data = session_file.get_email()

            # Fetch user settings
            self.users = Users.get_user_by_email(data)
            if self.users:
                mem0_prefs = Preferences.get_preferences_by_user_id(self.users.id)
                mem0_config = next((pref.setting_value for pref in mem0_prefs if pref.setting_key == "memory"),
                                       {})
                model=next((pref for pref in mem0_prefs if pref.setting_key == "llm_model"), None)
                if mem0_config.get("api_key") is not None or model is not None:
                    api_key = mem0_config.get("api_key", "")
                    memory_type = mem0_config.get("memo_engine", "local").lower()

                    # Store user metadata for richer context
                    self.user_metadata = {
                        "user_id": f"{self.users.id}-{self.users.name}" if self.users.id else "unknown",
                        "name": self.users.name,
                        "email": self.users.email,
                        "last_active": datetime.now().isoformat(),
                        "preferences": mem0_config.get("preferences", {})
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

    def get_proactive_context(self, current_input: str,limit:int=3) -> str:
        """Generate proactive context based on recent memories."""
        if not self.memory:
            return ""

        recent_memories = self.search_memory("recent interactions", limit=limit)
        context = "\n".join(
        f"- {m['memory']} (at {m['metadata'].get('timestamp', 'unknown')})"
        for m in recent_memories
    )


        chain=self.memory.llm.generate_response(
                            messages=[
                                {
                                    "role":"user",
                                    "content":f"""
                You are a smart assistant reviewing a user's recent system activity log.
                
                Context:
                {context}
                
                Current User Input: "{current_input}"
                
                Based on this, generate a useful proactive suggestion in one sentence that could help the user.
                Avoid repetition and make it helpful. Reply with just the suggestion.
                """
                                }
                            ],

        )
        context=f"{context}\nSuggestion: {chain}"
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

if __name__=="__main__":
    m=MemorySettings()
    m._initialize_memory()
    print(m.memory)