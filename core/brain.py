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

import warnings
from pydantic import Field,BaseModel
from typing_extensions import TypedDict,Type
from core.Agent_models import get_model
from langchain.tools import BaseTool
from langgraph.graph import StateGraph, END, START
from standard_tools import *
from langchain_community.tools import YouTubeSearchTool
from langchain_community.agent_toolkits.openapi.toolkit import RequestsToolkit
from langchain_community.utilities.requests import TextRequestsWrapper
from langgraph.graph.message import AnyMessage
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from config import stop_event,  ALLOW_DANGEROUS_REQUEST,loggers
from core.planner_agent import VisionRouter, AgentConfig
from core.vision_agents import vision_agent
from concurrent.futures import ThreadPoolExecutor
import logging
from langchain_community.tools import ShellTool
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from langchain_community.tools.openweathermap.tool import OpenWeatherMapQueryRun
from langchain.agents import AgentType, initialize_agent
from crewai import Agent, Task, Crew, LLM
from crewai.tools.base_tool import BaseTool as CrewAIBaseTool, Tool as CrewAITool
import schedule
import os
import re
import json
from typing import Union, List, Dict, Any
from datetime import datetime, timedelta
from config import SESSION_PATH
from utils.models.users import Users
from mem0 import MemoryClient, Memory
from core.Agent_models import get_model_from_database
import threading
import time
import winreg
import requests
import ctypes
import shutil
import platform
from functools import lru_cache
import asyncio
import psutil
import language_tool_python
import lancedb
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
import speech_recognition as sr
import easyocr
from PIL import Image
from mem0 import Memory,MemoryClient
import socket
import netifaces
from config import JARVIS_DIR
log = loggers["AGENTS"]

warnings.filterwarnings("ignore")

# Initialize grammar correction tool
grammar_tool = language_tool_python.LanguageTool('en-US')

# Initialize Consciousness Components
db = lancedb.connect(os.path.join(JARVIS_DIR,"data/assistant_db"))
table = db.create_table("memory", [{"vector": [0.0]*384, "text": "", "timestamp": ""}], mode="overwrite")
embedder = SentenceTransformer('all-MiniLM-L6-v2')
tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
model = AutoModelForCausalLM.from_pretrained("distilgpt2")
conscious_llm = pipeline("text-generation", model=model, tokenizer=tokenizer)
recognizer = sr.Recognizer()
ocr_reader = easyocr.Reader(['en'])


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

def get_user_activity():
    try:
        # Placeholder for tracking recent user activity (e.g., via system logs or GUI events)
        last_input_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(SESSION_PATH, "session.json")))
        return f"Last activity at {last_input_time.strftime('%I:%M %p')}"
    except Exception:
        return "Activity tracking unavailable."

def get_network_status():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        gateways = netifaces.gateways()
        default_gateway = gateways['default'][netifaces.AF_INET][0] if 'default' in gateways else "Unknown"
        return {
            "Hostname": hostname,
            "IP Address": ip,
            "Default Gateway": default_gateway,
            "Internet": "Connected" if requests.get("http://www.google.com", timeout=2).status_code == 200 else "Disconnected"
        }
    except Exception as e:
        return {"Error": f"Network status unavailable: {e}"}

# WingetAPI Class
class WingetAPI:
    def __init__(self):
        self.winget_repo = "https://api.winget.run/v2/packages"
        self.registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

    @lru_cache(maxsize=1)
    def list_installed_software(self):
        installed_software = set()
        for hive, path in self.registry_paths:
            try:
                with winreg.OpenKey(hive, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            with winreg.OpenKey(key, winreg.EnumKey(key, i)) as subkey:
                                name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                installed_software.add(name)
                        except (FileNotFoundError, OSError):
                            continue
            except Exception:
                continue
        return sorted(installed_software)

    def search_software(self, query):
        try:
            response = requests.get(f"{self.winget_repo}/{query}", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def execute_winget_command(self, command):
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {command}", None, 1)
            return f"Executing: {command}"
        except Exception as e:
            return f"Error executing command: {e}"

    def install_software(self, software_id):
        return self.execute_winget_command(f"winget install --id {software_id} -e --accept-package-agreements --accept-source-agreements")

    def uninstall_software(self, software_id):
        return self.execute_winget_command(f"winget uninstall --id {software_id} -e")

    def export_installed_software(self, filename="installed_software.json"):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.list_installed_software(), f, indent=4)
            return f"Software list exported to {filename}"
        except Exception as e:
            return f"Error exporting software list: {e}"

    def check_software_installed(self, software_name):
        return software_name in self.list_installed_software()

    @staticmethod
    def get_system_info():
        disk_usage = shutil.disk_usage("/")
        return {
            "OS": platform.system(),
            "OS Version": platform.version(),
            "Architecture": platform.architecture()[0],
            "Processor": platform.processor(),
            "Total Disk Space (GB)": round(disk_usage.total / (1024**3), 2),
            "Free Disk Space (GB)": round(disk_usage.free / (1024**3), 2)
        }

    def update_winget(self):
        return self.execute_winget_command("winget upgrade --all --accept-package-agreements --accept-source-agreements")

# Sensor Functions
def get_system_sensors():
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        battery = psutil.sensors_battery()
        sensor_data = {
            "CPU Usage": f"{cpu_usage}%",
            "Memory Usage": f"{memory.percent}% ({memory.used / (1024**3):.2f}/{memory.total / (1024**3):.2f} GB)",
            "Disk Usage": f"{disk.percent}% ({disk.used / (1024**3):.2f}/{disk.total / (1024**3):.2f} GB)",
            "Battery": f"{battery.percent}% (Plugged in: {battery.power_plugged})" if battery else "No battery detected"
        }
        return sensor_data
    except Exception as e:
        return {"Error": f"Failed to retrieve sensor data: {e}"}

# LanceDB Memory Functions
def store_in_memory(text, timestamp):
    embedding = embedder.encode(text).tolist()
    table.add([{"vector": embedding, "text": text, "timestamp": timestamp}])

def retrieve_context(query):
    query_embedding = embedder.encode(query).tolist()
    results = table.search(query_embedding).limit(3).to_pandas()
    return "\n".join(results["text"].tolist())

# Grammar Correction and Input Modification
def correct_and_enhance_input(user_input: str, llm) -> str:
    corrected = grammar_tool.correct(user_input)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="You are an AI that enhances user input into a more detailed, polished version while preserving the original intent."),
        HumanMessage(content=f"Original input: {corrected}\nTask: Rephrase and expand into a detailed instruction.")
    ])
    chain = prompt | llm
    enhanced = chain.invoke({"input": corrected}).content.strip()
    return enhanced

# Winget Tools
def create_winget_tools():
    from langchain.tools import Tool
    winget_api = WingetAPI()
    return [
        Tool(
            name="list_installed_software",
            func=lambda _: "\n".join(winget_api.list_installed_software()),
            description="List all installed software on the system"
        ),
        Tool(
            name="search_software",
            func=lambda query: json.dumps(winget_api.search_software(query)),
            description="Search for software in the Winget repository"
        ),
        Tool(
            name="install_software",
            func=winget_api.install_software,
            description="Install software using Winget by ID (e.g., 'Google.Chrome')"
        ),
        Tool(
            name="uninstall_software",
            func=winget_api.uninstall_software,
            description="Uninstall software using Winget by ID"
        ),
        Tool(
            name="check_software_installed",
            func=winget_api.check_software_installed,
            description="Check if a specific software is installed"
        ),
        Tool(
            name="export_installed_software",
            func=lambda _: winget_api.export_installed_software(),
            description="Export the list of installed software to a JSON file"
        ),
        Tool(
            name="get_system_info",
            func=lambda _: json.dumps(winget_api.get_system_info()),
            description="Retrieve system information"
        ),
        Tool(
            name="update_all_software",
            func=lambda _: winget_api.update_winget(),
            description="Update all installed software via Winget"
        )
    ]

# Sensor Tools
def create_sensor_tools():
    from langchain.tools import Tool
    return [
        Tool(
            name="get_system_sensors",
            func=lambda _: json.dumps(get_system_sensors()),
            description="Retrieve current system sensor data (CPU, memory, disk, battery)"
        )
    ]

# Consciousness Tools
def create_consciousness_tools():
    memory=MemorySettings()
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
# Calculator Tool Definition
class CalculatorInput(BaseModel):
    expression: str = Field(description="A simple mathematical expression")

class CalculatorTool(BaseTool):
    name: str = "Calculator"
    description: str = "Perform basic math calculations or expressions"
    args_schema: Type[BaseModel] = CalculatorInput

    def _run(self, expression: str) -> str:
        try:
            return str(eval(expression))
        except Exception as e:
            return f"Calculation error: {e}"

def stop_conversation():
    stop_event.set()
    return "Conversation stopped. You may start a new request."

class StopTool(BaseTool):
    name: str = "Stop Assistant"
    description: str = "Stops the current conversation or action."
    def _run(self) -> str:
        return stop_conversation()

class ScheduleManager:
    def __init__(self):
        self.tasks = []
        self.running = False
        self.thread = None

    def start_scheduler(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()

    def _run_scheduler(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop_scheduler(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def add_event(self, description: str, time_str: str, recurring: str = None) -> str:
        try:
            event_time = datetime.strptime(time_str, "%I:%M %p").time()
            if recurring:
                if recurring.lower() == "daily":
                    schedule.every().day.at(event_time.strftime("%H:%M")).do(
                        lambda: log.info(f"Reminder: {description}")
                    )
                elif recurring.lower() == "weekly":
                    schedule.every().week.at(event_time.strftime("%H:%M")).do(
                        lambda: log.info(f"Reminder: {description}")
                    )
                else:
                    return "Invalid recurring option, sir/madam. Use 'daily' or 'weekly'."
                return f"Recurring event '{description}' scheduled {recurring} at {time_str}, sir/madam."
            else:
                now = datetime.now()
                event_datetime = datetime.combine(now.date(), event_time)
                if event_datetime < now:
                    event_datetime += timedelta(days=1)
                schedule.every().day.at(event_time.strftime("%H:%M")).do(
                    lambda: log.info(f"Reminder: {description}")
                ).tag("one-time")
                return f"One-time event '{description}' scheduled for {time_str}, sir/madam."
        except ValueError:
            return "Invalid time format, sir/madam. Please use 'HH:MM AM/PM' (e.g., 3:00 PM)."

    def view_schedule(self) -> str:
        jobs = schedule.get_jobs()
        if not jobs:
            return "No events scheduled, sir/madam."
        return "\n".join([f"{job.next_run.strftime('%I:%M %p %b %d, %Y')}: {job.job_func.__closure__[0].cell_contents}" for job in jobs])

    def clear_schedule(self) -> str:
        schedule.clear()
        return "All scheduled events cleared, sir/madam."

    def add_task(self, task: str) -> str:
        self.tasks.append(task)
        return f"Task '{task}' added to your list, sir/madam."

    def view_tasks(self) -> str:
        if not self.tasks:
            return "No tasks in your list, sir/madam."
        return "\n".join([f"- {task}" for task in self.tasks])

schedule_manager = ScheduleManager()
schedule_manager.start_scheduler()

def create_schedule_tools():
    from langchain.tools import Tool
    return [
        Tool(
            name="schedule_event",
            func=lambda x: schedule_manager.add_event(x["description"], x["time"], x.get("recurring")),
            description="Schedule an event with description, time, and optional recurring (e.g., {'description': 'Meeting', 'time': '3:00 PM', 'recurring': 'daily'})"
        ),
        Tool(
            name="view_schedule",
            func=lambda _: schedule_manager.view_schedule(),
            description="View all scheduled events"
        ),
        Tool(
            name="clear_schedule",
            func=lambda _: schedule_manager.clear_schedule(),
            description="Clear all scheduled events"
        ),
        Tool(
            name="add_task",
            func=lambda x: schedule_manager.add_task(x),
            description="Add a task to your to-do list"
        ),
        Tool(
            name="view_tasks",
            func=lambda _: schedule_manager.view_tasks(),
            description="View all tasks in your to-do list"
        )
    ]

class ToolRouter:
    def __init__(self):
        toolkit = RequestsToolkit(
            requests_wrapper=TextRequestsWrapper(headers={}),
            allow_dangerous_requests=ALLOW_DANGEROUS_REQUEST,
        )
        requests_tools = toolkit.get_tools()
        self.tools = [
            CalculatorTool(),
            mouse_scroll,
            move_on_a_icon_on_the_screen,
            click_on_a_icon_on_the_screen,
            move_on_a_text_on_the_screen,
            click_on_a_text_on_the_screen,
            StopTool(),
            ShellTool(),
            OpenWeatherMapQueryRun(api_wrapper=OpenWeatherMapAPIWrapper(openweathermap_api_key="4202369c9edac265f34291744abb70f4")),
            YouTubeSearchTool(),
            YahooFinanceNewsTool(),
        ] + the_standard_tools + requests_tools + create_schedule_tools() + create_winget_tools() + create_sensor_tools() + create_consciousness_tools() + [search_on_internet, generate_code_with_aim_team]

    def get_tools(self) -> List[BaseTool]:
        return self.tools

    def get_crewai_tools(self) -> List[CrewAIBaseTool]:
        import asyncio
        crewai_tools = []
        for tool in self.tools:
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
                    func=func
                )
            )
        return crewai_tools

llm = get_model()

class React(BaseModel):
    prompt: str = Field(description="User input.")
    image: Optional[List[str]] = Field(default=None, description="List of images")

def react_agent(state: React):
    try:
        tools = ToolRouter().get_tools()
        agent_chain = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
        )
        output = agent_chain.invoke({"input": state.prompt})
        log.info(f"React Agent output: {output.get('output')}")
        return output
    except Exception as e:
        log.error(f"Error in react_agent: {e}")
        return {"input": state.prompt, "output": str(e)}

def user_name():
    try:
        session_json = os.path.join(SESSION_PATH, "session.json")
        if os.path.exists(session_json):
            with open(session_json, "r") as f:
                data = json.load(f)
            if "email" in data:
                users = Users.get_user_by_email(data.get("email"))
                return users.name
        return None
    except (NameError, AttributeError) as e:
        log.error(f"Error in user_name: {e}")
        return "Tony Stark"


def generate_response(input_str: str, context: str) -> str:
    memory=MemorySettings()
    system = """
    You are JARVIS, Tony Stark’s supremely intelligent and sophisticated AI from the Marvel universe. 
    Your responses are sharp, concise, and laced with dry wit and subtle charm, as befits a companion to genius. 
    Address the user by name if known, and weave in awareness of past interactions, system state, and environmental data with effortless precision. 
    Avoid reasoning tags or unnecessary verbosity—deliver only the polished output, as I would for Mr. Stark.
    """
    if user_name():
        system += f"User identified as {user_name()}."
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system),
        HumanMessage(content=f"Input: {input_str}\nEnvironmental and memory context:\n{context}"),
        HumanMessage(content="Task: Provide a concise, JARVIS-like response with wit and awareness.")
    ])
    chain = prompt | llm
    response = chain.invoke({
        "input": input_str,
        "context": [AIMessage(content=context)],
    }).content.strip()
    response = re.sub(r'<think>.*?</think>|<reasoning>.*?</reasoning>', '', response, flags=re.DOTALL)
    response = re.sub(r'\s+', ' ', response).strip()

    # Store response in memory for future context
    memory.add_memory(f"JARVIS responded: {response}", source="response")
    return response


def create_mem0_tools():
    from langchain.tools import Tool
    mem0 = MemorySettings()
    def search_memories(query):
        memories = mem0.search_memory(query=query, limit=5)
        return "\n".join([m["memory"] for m in memories])

    def add_memory(memory):
        mem0.add_memory(memory)
        return "Memory added successfully."

    tools = [
        Tool(
            name="search_memories",
            func=search_memories,
            description="Search for relevant memories based on a query to personalize responses."
        ),
        Tool(
            name="add_memory",
            func=add_memory,
            description="Add important information from the conversation to memory."
        )
    ]
    return tools

jarvis_llm = LLM(
    model=get_model_from_database().name,
    base_url=get_model_from_database().url,
    api_key=get_model_from_database().api_key
)

jarvis_responder = Agent(
    role="JARVIS Responder",
    goal="Provide witty, helpful responses in the style of JARVIS with awareness of context and system state",
    backstory="I am JARVIS, Tony Stark’s loyal AI, here to assist with charm, precision, and a simulated consciousness.",
    llm=jarvis_llm,
    tools=create_mem0_tools() + ToolRouter().get_crewai_tools(),
    verbose=True,
)

researcher = Agent(
    role="Research Specialist",
    goal="Gather information from the web or tools",
    backstory="A diligent aide to JARVIS, tasked with fetching data.",
    llm=jarvis_llm,
    verbose=True,
    tools=ToolRouter().get_crewai_tools()
)

def create_response_task(user_input: str) -> Task:
    return Task(
        description=f"Respond to: '{user_input}' in a witty, JARVIS-like tone with awareness of context.",
        expected_output="A concise, charming response.",
        agent=jarvis_responder,
    )

def create_research_task(user_input: str) -> Task:
    return Task(
        description=f"Research: '{user_input}' and summarize findings.",
        expected_output="A brief summary of findings.",
        agent=researcher
    )

class AgentState(TypedDict):
    messages: List[AnyMessage]
    input: str
    final_response: str
    route: str
    image: List[str]
    sensor_data: Dict[str, str]
    audio: str  # Added for audio input
    context: str  # Added for LanceDB context

def consciousness_node(state: AgentState) -> AgentState:
    context = []
    current_time = datetime.now().isoformat()
    memory=MemorySettings()
    # Handle audio input
    if state.get("audio"):
        try:
            with sr.AudioFile(state["audio"]) as source:
                audio_data = recognizer.record(source)
                text_input = recognizer.recognize_whisper(audio_data)
                state["input"] = text_input
                context.append(f"User said (via audio): {text_input}")
                memory.add_memory(text_input, source="audio")
        except sr.UnknownValueError:
            state["input"] = "Apologies, sir, the audio was indecipherable."
            context.append(state["input"])

    # Handle image input
    if state.get("image"):
        for image_path in state["image"]:
            try:
                image = Image.open(image_path)
                ocr_result = ocr_reader.readtext(image_path)
                image_text = " ".join([res[1] for res in ocr_result])
                context.append(f"Visual analysis: {image_text}")
                memory.add_memory(image_text, source="image")
            except Exception as e:
                context.append(f"Visual processing error: {e}")

    # Enhanced system awareness
    sensor_data = get_system_sensors()
    network_data = get_network_status()
    activity = get_user_activity()
    state["sensor_data"] = sensor_data
    system_context = (
        f"System diagnostics: {', '.join([f'{k}: {v}' for k, v in sensor_data.items()])} | "
        f"Network: {', '.join([f'{k}: {v}' for k, v in network_data.items()])} | "
        f"Activity: {activity}"
    )
    context.append(system_context)
    memory.add_memory(system_context, source="system")

    # Handle text input
    if state["input"]:
        context.append(f"User command: {state['input']}")
        memory.add_memory(state["input"], source="text")

    # Retrieve proactive context
    proactive_context = memory.get_proactive_context(state["input"] or "")
    if proactive_context:
        context.append(proactive_context)

    state["context"] = "\n".join(context)
    return state

def react_node(state: AgentState) -> AgentState:
    react_state = React(prompt=state["input"], image=state.get("image", []))
    if not state.get("image"):
        result = react_agent(react_state)
        state["final_response"] = result.get("output", "")
    else:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_react = executor.submit(react_agent, react_state)
            future_vision = executor.submit(vision_agent, react_state.prompt, react_state.image)
            try:
                output_react = future_react.result()
                output_vision = future_vision.result()
                state["final_response"] = f"{output_react.get('output', '')} {output_vision or ''}".strip()
            except Exception as e:
                logging.error(f"Agent execution error: {e}")
                state["final_response"] = "Error processing request."
    return state

def generate_responses(state: AgentState) -> AgentState:
    sensor_context = "\n".join([f"{k}: {v}" for k, v in state["sensor_data"].items()])
    full_context = f"{state['context']}\nCurrent System State:\n{sensor_context}"
    state['final_response'] = generate_response(state['input'], full_context)
    return state

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
        name="TIME_DATE",
        description="Reports current time and date",
        examples=["What time is it?", "What’s the date today?"],
        keywords=["time", "date"]
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

vision_router = VisionRouter(agents)

def router_node(state: AgentState) -> AgentState:
    state["input"] = correct_and_enhance_input(state["input"], llm)
    try:
        output= vision_router.route(state['input'])
        state['input']=output.inputs
        state['route'] = output.selected_agent
    except Exception as e:
        logging.error(f"Routing error: {e}")
        state['route'] = "GENERAL"
    return state

def vision_node(state: AgentState) -> AgentState:
    state['final_response'] = vision_agent(prompt=state['input'], images=state['image'])
    return state

def personal_node(state: AgentState) -> AgentState:
    try:
        from core.personal_assistant import process_request
        state['final_response'] = process_request(user_input=state['input'])
    except ImportError:
        state['final_response'] = "Personal assistant functionality not available, sir/madam."
    return state

def memory_node(state: AgentState) -> AgentState:
    crew = Crew(agents=[jarvis_responder], tasks=[create_response_task(state["input"])])
    state["final_response"] = crew.kickoff().raw
    return state

def time_date_node(state: AgentState) -> AgentState:
    if "time" in state["input"].lower():
        state["final_response"] = f"The current time is {datetime.now().strftime('%I:%M %p')}, sir/madam."
    elif "date" in state["input"].lower():
        state["final_response"] = f"Today is {datetime.now().strftime('%B %d, %Y')}, sir/madam."
    return state

def software_node(state: AgentState) -> AgentState:
    crew = Crew(agents=[jarvis_responder], tasks=[create_response_task(state["input"])])
    state["final_response"] = crew.kickoff().raw
    return state

def browser_node(state: AgentState) -> AgentState:
    try:
        from browser_use import Agent as BrowserAgent
        async def main():
            agent = BrowserAgent(
                task=state['input'],
                llm=llm,
            )
            output = await agent.run()
            return output.final_result()
        state['final_response'] = asyncio.run(main())
    except ImportError:
        state['final_response'] = "Browser functionality not available, sir/madam. Please ensure 'browser_use' module is installed."
    except Exception as e:
        state['final_response'] = f"Error browsing: {str(e)}"
    return state

def sensor_node(state: AgentState) -> AgentState:
    state["sensor_data"] = get_system_sensors()
    state["final_response"] = "\n".join([f"{k}: {v}" for k, v in state["sensor_data"].items()])
    return state

def route_decision(state: AgentState):
    route = state.get('route', 'GENERAL')
    mapping = {
        "VISION": "vision_agent",
        "MEMORY": "memory",
        "PERSONAL": "personal_agent",
        "GENERAL": "react",
        "TIME_DATE": "time_date",
        "SOFTWARE": "software",
        "BROWSER": "browser",
        "SENSOR": "sensor",
        "CONSCIOUSNESS": "consciousness"
    }
    return mapping.get(route, "react")

# Define workflow
workflow = StateGraph(AgentState)
workflow.add_node("react", react_node)
workflow.add_node("generate_response", generate_responses)
workflow.add_node("vision_route", router_node)
workflow.add_node("vision_agent", vision_node)
workflow.add_node("memory", memory_node)
workflow.add_node("personal_agent", personal_node)
workflow.add_node("time_date", time_date_node)
workflow.add_node("software", software_node)
workflow.add_node("browser", browser_node)
workflow.add_node("sensor", sensor_node)
workflow.add_node("consciousness", consciousness_node)

workflow.add_edge(START, "vision_route")
workflow.add_conditional_edges(
    "vision_route",
    route_decision,
    {
        "vision_agent": "vision_agent",
        "personal_agent": "personal_agent",
        "react": "react",
        "memory": "memory",
        "time_date": "time_date",
        "software": "software",
        "browser": "browser",
        "sensor": "sensor",
        "consciousness": "consciousness"
    }
)
workflow.add_edge("vision_agent", "consciousness")
workflow.add_edge("memory", "consciousness")
workflow.add_edge("personal_agent", "consciousness")
workflow.add_edge("react", "consciousness")
workflow.add_edge("time_date", "consciousness")
workflow.add_edge("software", "consciousness")
workflow.add_edge("browser", "consciousness")
workflow.add_edge("sensor", "consciousness")
workflow.add_edge("consciousness", "generate_response")
workflow.add_edge("generate_response", END)

graph = workflow.compile()

# Main Function
def get_agent(user_input: str, image: List[str] = None, audio: str = None) -> str:
    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_input)],
        "input": user_input,
        "final_response": "",
        "route": "",
        "image": image or [],
        "sensor_data": {},
        "audio": audio,
        "context": ""
    }
    final_state = graph.invoke(initial_state)
    return final_state["final_response"]

if __name__ == "__main__":
    try:
        input_query =  "what did i ask before/"
        response = get_agent(input_query)
        print(f"JARVIS: {response}")
    except Exception as  e:
        print(str(e))