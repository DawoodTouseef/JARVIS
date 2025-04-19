from core.planner_agent import AgentConfig

agents = [
    AgentConfig(
        name="VISION",
        description="Handles image analysis, photo processing, and visual content questions",
        examples=["What's in this photo?", "Enhance image colors", "Describe this picture"],
        keywords=["photo", "image", "visual"]
    ),
    AgentConfig(
        name="GENERAL",
        description="Handles text-based questions and general knowledge",
        examples=["Explain quantum physics", "Who invented radio?", "What is AI?", "what is the weather?"],
        keywords=["explain", "what", "who", "how", "when", "why"]
    ),
    AgentConfig(
        name="MEMORY",
        description="Handles past interactions and personalized experiences",
        examples=["What did we discuss last time?", "Based on my preferences..."],
        keywords=["remember", "preference", "last time"]
    ),
    AgentConfig(
        name="PERSONAL",
        description="Handles personal tasks like schedules, reminders, and preferences",
        examples=["What's on my schedule today?", "Set a reminder for 5 PM", "Update my preferences"],
        keywords=["schedule", "reminder", "preference", "personal"]
    ),
    AgentConfig(
        name="SOFTWARE",
        description="Manages software installation, uninstallation, and system info",
        examples=["Install Google Chrome", "List installed software", "Update all software"],
        keywords=["install", "uninstall", "software", "system", "update"]
    ),
    AgentConfig(
        name="BROWSER",
        description="Handles browser-related tasks like navigation and interaction",
        examples=["Browse to Google", "Click the search button", "Fill out a form"],
        keywords=["browse", "click", "navigate", "webpage"]
    ),
    AgentConfig(
        name="SENSOR",
        description="Handles system sensor data and state awareness",
        examples=["What’s the CPU usage?", "How much battery is left?"],
        keywords=["cpu", "memory", "disk", "battery", "sensor", "system state"]
    ),
    AgentConfig(
        name="CONSCIOUSNESS",
        description="Processes multimodal inputs and maintains awareness",
        examples=["What did I say earlier?", "Describe my surroundings", "What’s happening now?"],
        keywords=["audio", "image", "context", "aware", "surroundings"]
    ),
]