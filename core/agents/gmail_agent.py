import os
import sys
import logging

from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
from config import JARVIS_DIR
from core.Agent_models import get_model_from_database
from crewai import Agent,Task,Process,Crew,LLM
from crewai.tools.base_tool import BaseTool as CrewAIBaseTool, Tool as CrewAITool
from typing import List

# Set up logging to console and file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(JARVIS_DIR, "data", "gmail_agent.log"))
    ]
)
logger = logging.getLogger(__name__)

class GmailAgent:
    def __init__(self, memory):
        self.memory = memory
        self.llm = LLM(
            model=f"openai/{get_model_from_database().name}",
            api_key=get_model_from_database().api_key,
            base_url=get_model_from_database().url
        )
        self.initialize_gmail_toolkit()
        # Initialize agents
        self._setup_agents()

        # Initialize tasks
        self._setup_tasks()

        # Initialize Crew
        self.crew = Crew(
            agents=[self.email_reader, self.email_categorizer, self.reply_drafter],
            tasks=[self.read_task, self.categorize_task, self.draft_task],
            verbose=True,
            process=Process.sequential
        )
        logger.info("GmailAgent initialized")

    def get_crewai_tools(self) -> List[CrewAIBaseTool]:
        import asyncio
        crewai_tools = []
        for tool in self.gmail_toolkit.get_tools():
            if hasattr(tool, '_run'):
                func = tool._run
            elif hasattr(tool, '_arun'):
                async def async_wrapper(*args, **kwargs):
                    return await tool._arun(*args, **kwargs)

                def sync_func(*args, **kwargs):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            return loop.run_until_complete(async_wrapper(*args, **kwargs))
                        else:
                            return asyncio.run(async_wrapper(*args, **kwargs))
                    except RuntimeError:
                        return asyncio.run(async_wrapper(*args, **kwargs))

                func = sync_func
            else:
                func = None

            crewai_tools.append(
                CrewAITool(
                    name=tool.name,
                    description=tool.description,
                    func=func,
                    args_schema=tool.args_schema
                )
            )
        return crewai_tools

    # Initialize Gmail Toolkit
    def initialize_gmail_toolkit(self):
        logger.info("Initializing Gmail Toolkit")
        try:
            credentials = get_gmail_credentials(
                token_file=os.path.join(JARVIS_DIR, "data", "token.json"),
                scopes=["https://mail.google.com/"],
                client_secrets_file=os.path.join(JARVIS_DIR, "data", "credentials.json"),
            )
        except Exception as e:
            logger.error("Error loading credentials: %s", e)
            if os.path.exists(os.path.join(JARVIS_DIR, "data", "token.json")):
                logger.info("Removing invalid token.json and retrying")
                os.remove(os.path.join(JARVIS_DIR, "data", "token.json"))
                credentials = get_gmail_credentials(
                    token_file=os.path.join(JARVIS_DIR, "data", "token.json"),
                    scopes=["https://mail.google.com/"],
                    client_secrets_file=os.path.join(JARVIS_DIR, "data", "credentials.json"),
                )
            else:
                raise
        api_resource = build_resource_service(credentials=credentials)
        gmail_toolkit = GmailToolkit(api_resource=api_resource)
        logger.info("Gmail Toolkit initialized")
        self.gmail_toolkit=gmail_toolkit

    # Retrieve relevant memories
    def get_memory_context(self, query):
        logger.info("Retrieving memory context for query: %s", query)
        try:
            memories = self.memory.search_memory(query)
            logger.debug("Raw memories: %s", memories)
            if memories:
                context = "\n".join([f"- {m['memory']}" for m in memories if isinstance(m, dict) and 'memory' in m])
                logger.info("Memory context: %s", context)
                return context or "No relevant memories found."
            return "No relevant memories found."
        except Exception as e:
            logger.error("Error retrieving memories: %s", e)
            return "Error retrieving memories."

    # Add memory with role
    def add_memory(self, role, content):
        logger.info("Adding memory: role=%s, content=%s", role, content)
        try:
            if not isinstance(content, str):
                content = str(content)
            self.memory.add_memory(content)
            logger.info("Memory added successfully")
        except Exception as e:
            logger.error("Error adding memory: %s", e)

    def _setup_agents(self):
            """Set up CrewAI agents for email management."""
            self.email_reader = Agent(
                role="Email Reader",
                goal="Fetch and summarize unread emails from Gmail inbox",
                backstory="You are an efficient assistant skilled at retrieving and summarizing emails to provide concise overviews.",
                tools=self.get_crewai_tools(),
                llm=self.llm,
                verbose=True
            )

            self.email_categorizer = Agent(
                role="Email Categorizer",
                goal="Analyze and categorize emails into Urgent, Newsletter, Personal, or Other",
                backstory="You are a meticulous organizer who can quickly assess email content and assign appropriate categories.",
                tools=self.get_crewai_tools(),
                llm=self.llm,
                verbose=True
            )

            self.reply_drafter = Agent(
                role="Reply Drafter",
                goal="Draft context-appropriate email responses and save them as drafts",
                backstory="You are a professional communicator adept at crafting polite and relevant email replies.",
                tools=self.get_crewai_tools(),
                llm=self.llm,
                verbose=True
            )

    def _setup_tasks(self):
        """Set up tasks for email management."""
        self.read_task = Task(
                description="Fetch all unread emails from the Gmail inbox and provide a summary of each email, including sender, subject, and a brief content overview (max 50 words per email).",
                agent=self.email_reader,
                expected_output="A list of summaries for unread emails, each containing sender, subject, and a brief content overview."
        )

        self.categorize_task = Task(
                description="Analyze the content of each unread email and categorize it as 'Urgent', 'Newsletter', 'Personal', or 'Other'. Add a Gmail label corresponding to the category.",
                agent=self.email_categorizer,
                expected_output="A list of emails with their assigned categories and confirmation that labels have been applied."
        )

        self.draft_task = Task(
                description="For each email categorized as 'Urgent' or 'Personal', draft a polite response acknowledging the email and addressing its main point. Save the response as a draft in Gmail.",
                agent=self.reply_drafter,
                expected_output="Confirmation that draft responses have been created for Urgent and Personal emails."
        )

    def run(self,query):
        """Execute the email management workflow."""
        try:
            result = self.crew.kickoff({"input":query})
            return result
        except Exception as e:
            return str(e)

if __name__ == '__main__':
    from core.memory.memory_agent import MemorySettings
    from config import SessionManager
    s=SessionManager()
    s.create_session("tdawood140@gmail.com")
    try:
        m = MemorySettings()
        m._initialize_memory()
        gmail = GmailAgent(m)
        result = gmail.run("Is there any email of Qspider?")
        print("Result:", result)
    except Exception as e:
        logger.error("Error in main: %s", e)
        print(f"Error: {str(e)}")