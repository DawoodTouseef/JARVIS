from core.memory.memory_agent import MemorySettings

# Consciousness Tools
def create_consciousness_tools():
    memory=MemorySettings()
    memory._initialize_memory()
    from langchain.tools import Tool
    return [
        Tool(
            name="add_memory",
            func=lambda x: memory.add_memory(x["text"], source="tool"),
            description="Store text in JARVIS’s memory."
        ),
        Tool(
            name="search_memory",
            func=lambda x: "\n".join([m["memory"] for m in memory.search_memory(x["query"])]),
            description="Retrieve relevant context from JARVIS’s memory."
        )
    ]