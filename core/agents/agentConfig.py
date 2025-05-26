from core.agents.planner_agent import AgentConfig

agents = [
    AgentConfig(
        name="VISION",
        description="Handles image analysis, photo processing, and visual content questions",
        examples=["What's in this photo?", "Enhance image colors", "Describe this picture"],
        keywords=["photo", "image", "visual"]
    ),
    AgentConfig(
        name="GENERAL",
        description="Handles text-based questions , general knowledge ,personal tasks like schedules, reminders, and preferences",
        examples=["Explain quantum physics", "What is AI?", "what is the weather?","What's on my schedule today?", "Set a reminder for 5 PM"],
        keywords=["explain", "what", "who", "how", "when", "why","schedule", "reminder", "preference", "personal"]
    ),
    AgentConfig(
        name="MEMORY",
        description="Handles past interactions and personalized experiences",
        examples=["What did we discuss last time?", "Based on my preferences..."],
        keywords=["remember", "preference", "last time"]
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
    AgentConfig(
        name="GMAILAGENT",
        description="A context-aware AI agent that manages Gmail tasks such as sending, searching, and reading emails. Powered by LangChain, Gmail Toolkit, and mem0 for memory retention, it responds to natural language queries with personalized, context-informed actions.",
        examples=[
            "Send an email to team@company.com with the subject 'Project Update' and body 'Here's the latest progress report.'",
            "Search for emails from john.doe@example.com received this month.",
            "Read the latest unread email in my inbox.",
            "Draft an email to client@domain.com with subject 'Meeting Follow-Up'.",
            "Find all emails with the word 'invoice' in the subject."
        ],
        keywords=[
            "Gmail",
            "email",
            "send",
            "search",
            "read",
            "draft",
            "context-aware",
            "memory",
            "LangChain",
            "JARVIS",
            "automation",
            "productivity"
        ]
    ),
]