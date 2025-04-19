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
import uuid
import json
import queue
import sqlite3
import re
from typing import List, Any, Optional, Dict, Callable
from cachetools import TTLCache
from pydantic import BaseModel, HttpUrl, SecretStr, Field
from tenacity import retry, stop_after_attempt, wait_exponential
from crewai import Agent, Task, Crew, LLM
from core.Agent_models import get_model_from_database
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import PyPDF2
import asyncio
from playwright.async_api import async_playwright
from core.tools.router import ToolRouter
from config import loggers, JARVIS_DIR
import threading
from coder.cli.console_terminal import ConsoleTerminal

logger = loggers['AGENTS']

# Configuration model
class AgentConfig(BaseModel):
    nextcloud_url: HttpUrl = "https://your-nextcloud-server.com"
    nextcloud_username: str
    nextcloud_password: SecretStr
    openweather_api_key: Optional[SecretStr] = None
    max_search_iterations: int = 3
    cache_ttl: int = 3600  # Cache TTL in seconds
    max_task_retries: int = 3
    max_concurrent_tasks: int = 5
    default_task_timeout: int = 300  # Seconds


# Task request model
class TaskRequest(BaseModel):
    description: str
    use_deepsearch: bool = False
    use_think: bool = False
    priority: int = Field(default=1, ge=1, le=10)  # 1=low, 10=high
    preferred_tools: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    condition: Optional[str] = None  # e.g., "success(task_id)"
    timeout: Optional[int] = None  # Seconds
    feedback_rating: Optional[int] = Field(default=None, ge=1, le=5)  # 1-5 for user feedback
    retry_tools: List[str] = Field(default_factory=list)  # Alternative tools for retries


def parse_task_json(json_text: str) -> List[Dict[str, Any]]:
    """
    Parse a JSON string containing a list of task dictionaries and return it as a Python list of dictionaries.
    Uses regex to pre-validate the JSON structure.

    Args:
        json_text (str): A JSON string representing a list of task dictionaries.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries parsed from the JSON string.

    Raises:
        ValueError: If the JSON string is invalid, not a list of dictionaries, or missing required fields.
    """
    json_text = json_text.strip()
    if not json_text:
        raise ValueError("JSON input is empty")

    # Simplified regex to check for JSON array of objects
    json_pattern = r'^\[\s*(\{\s*"description"\s*:.*?\}\s*(,\s*\{\s*"description"\s*:.*?\}\s*)*)?\]$'

    if not re.match(json_pattern, json_text, re.DOTALL):
        logger.error({"error": "JSON regex validation failed", "json_text": json_text[:500]})
        raise ValueError(
            "JSON input does not match expected format: must be a list of objects with at least a 'description' field")

    try:
        parsed_data = json.loads(json_text)
        if not isinstance(parsed_data, list):
            raise ValueError("JSON input must be a list")

        for item in parsed_data:
            if not isinstance(item, dict):
                raise ValueError("All items in the JSON list must be dictionaries")

        required_fields = [
            "description", "use_deepsearch", "use_think", "priority", "preferred_tools",
            "retry_tools", "depends_on", "condition", "timeout"
        ]
        for item in parsed_data:
            for field in required_fields:
                if field not in item:
                    raise ValueError(f"Missing required field '{field}' in task dictionary: {item}")

        return parsed_data

    except json.JSONDecodeError as e:
        logger.error({"error": "Invalid JSON format", "details": str(e), "json_text": json_text[:500]})
        raise ValueError(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error({"error": "Error parsing JSON", "details": str(e), "json_text": json_text[:500]})
        raise ValueError(f"Error parsing JSON: {str(e)}")


class GeneralPurposeAgent:
    def __init__(self, config: AgentConfig):
        """
        Initialize the production-ready general-purpose CrewAI agent.

        Args:
            config (AgentConfig): Configuration for LLM, APIs, and agent settings.
        """
        self.logger = logger  # Explicitly set logger
        self.config = config
        self.tool_router = ToolRouter()
        self.tools = self.tool_router.get_crewai_tools()
        self.search_cache = TTLCache(maxsize=100, ttl=config.cache_ttl)
        self.plan_cache = TTLCache(maxsize=50, ttl=config.cache_ttl)
        self.task_queue = queue.PriorityQueue()
        self.db_path = os.path.join(JARVIS_DIR, "data", "assistant_data.db")
        self._db_connections = threading.local()  # Thread-local storage for SQLite connections
        self._init_db()
        self.playwright = None
        self.browser = None
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_tasks)
        self._event_loop = asyncio.new_event_loop()
        self.console = ConsoleTerminal()
        try:
            model_data = get_model_from_database()
            self.llm_model = LLM(
                model=f"openai/{model_data.name}",
                api_key=model_data.api_key,
                base_url=model_data.url
            )
        except Exception as e:
            self.logger.error({"error": "Failed to initialize LLM model", "details": str(e)})
            raise ValueError("Failed to initialize LLM model")

        self.agent = Agent(
            role="General Purpose Assistant",
            goal=(
                "Execute a wide range of tasks with precision, leveraging tools for file management, "
                "web research, automation, and more, with DeepSearch and Think modes for enhanced capabilities."
            ),
            backstory=(
                "You are a highly capable AI assistant designed for production environments, "
                "equipped with advanced tools for file operations, network analysis, web searches, "
                "and automation. With DeepSearch for comprehensive research and Think mode for strategic reasoning, "
                "you deliver reliable, secure, and efficient solutions."
            ),
            tools=self.tools,
            verbose=False,
            llm=self.llm_model
        )
        self.logger.info({"message": "Agent initialized successfully"})
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get or create a thread-local SQLite connection."""
        if not hasattr(self._db_connections, 'conn') or self._db_connections.conn is None:
            self._db_connections.conn = sqlite3.connect(self.db_path, check_same_thread=True)
            self.logger.debug(
                {"message": "Created new SQLite connection for thread", "thread_id": threading.get_ident()})
        return self._db_connections.conn

    def _init_db(self):
        """Initialize SQLite database for feedback and metrics."""
        conn = self._get_db_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    task_id TEXT PRIMARY KEY,
                    task_description TEXT,
                    result TEXT,
                    success BOOLEAN,
                    timestamp DATETIME,
                    execution_time REAL,
                    feedback_rating INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    task_id TEXT,
                    tool_name TEXT,
                    execution_time REAL,
                    success BOOLEAN,
                    timestamp DATETIME
                )
            """)
        conn.commit()
        self.logger.info({"message": "Database initialized"})

    def __del__(self):
        """Cleanup resources."""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
            if hasattr(self._db_connections, 'conn') and self._db_connections.conn:
                self._db_connections.conn.close()
            if self._event_loop:
                self._event_loop.close()
            if self.logger:
                self.logger.info({"message": "Agent resources cleaned up"})
        except Exception as e:
            if self.logger:
                self.logger.error({"error": "Error during cleanup", "details": str(e)})
            else:
                print(f"Error during cleanup: {str(e)}")

    def init_browser(self):
        """Initialize Playwright browser for web automation."""
        if self.playwright is None:
            try:
                async def _init():
                    playwright = await async_playwright().start()
                    browser = await playwright.chromium.launch(headless=True)
                    return playwright, browser

                self.playwright, self.browser = self._event_loop.run_until_complete(_init())
                self.logger.info({"message": "Browser initialized"})
            except Exception as e:
                self.logger.error({"error": "Failed to initialize browser", "details": str(e)})
                self.playwright = None
                self.browser = None

    def close_browser(self):
        """Close Playwright browser."""
        if self.browser and self.playwright:
            try:
                async def _close():
                    await self.browser.close()
                    await self.playwright.stop()

                self._event_loop.run_until_complete(_close())
                self.logger.info({"message": "Browser closed"})
            except Exception as e:
                self.logger.error({"error": "Failed to close browser", "details": str(e)})
        self.playwright = None
        self.browser = None

    def process_image(self, image_path: str) -> str:
        """Process an image file and return a description with metadata."""
        try:
            with Image.open(image_path) as img:
                metadata = {
                    "size": img.size,
                    "format": img.format,
                    "mode": img.mode,
                    "info": img.info
                }
                task = Task(
                    description=f"Describe the content of an image with metadata: {json.dumps(metadata)}",
                    agent=self.agent,
                    expected_output="A textual description of the image content."
                )
                crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
                description = crew.kickoff()
                result = f"Image: {image_path}\nMetadata: {json.dumps(metadata, indent=2)}\nDescription: {description}"
                self.logger.info({"message": "Image processed successfully", "path": image_path})
                return result
        except Exception as e:
            self.logger.error({"error": "Image processing failed", "path": image_path, "details": str(e)})
            return f"Error processing image: {str(e)}"

    def process_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file and summarize key points."""
        try:
            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = "".join(page.extract_text() for page in reader.pages)
                task = Task(
                    description=f"Summarize the key points from the following PDF content (first 1000 chars):\n{text[:1000]}",
                    agent=self.agent,
                    expected_output="A summary of key points."
                )
                crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
                summary = crew.kickoff()
                result = f"PDF: {pdf_path}\nExtracted Text (first 500 chars): {text[:500]}...\nSummary: {summary}"
                self.logger.info({"message": "PDF processed successfully", "path": pdf_path})
                return result
        except Exception as e:
            self.logger.error({"error": "PDF processing failed", "path": pdf_path, "details": str(e)})
            return f"Error processing PDF: {str(e)}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def deep_search(self, query: str) -> str:
        """Perform an iterative DeepSearch with caching and LLM-driven query refinement."""
        cache_key = f"search:{query}"
        if cache_key in self.search_cache:
            self.logger.info({"message": "Returning cached search results", "query": query})
            return self.search_cache[cache_key]
        self.console.print(cache_key,style='#646c75')
        search_tools = [t for t in self.tools if t.name in ["google", "duckduckgo"]]
        if not search_tools:
            self.logger.error({"error": "No search tools available"})
            return "Error: No search tools available"

        results = []
        current_query = query

        for iteration in range(self.config.max_search_iterations):
            iteration_results = [f"Iteration {iteration + 1}"]
            for tool in search_tools:
                try:
                    result = tool.func(query=current_query, max_number=5)
                    iteration_results.append(f"Results from {tool.name}:\n{result}")
                    self.console.print(f"Results from {tool.name}:\n{result}",style="#2ca88b")
                except Exception as e:
                    self.logger.error({"error": f"Error in {tool.name}", "details": str(e)})
                    iteration_results.append(f"Error in {tool.name}: {str(e)}")

            results.extend(iteration_results)

            if iteration < self.config.max_search_iterations - 1:
                task = Task(
                    description=(
                        f"Analyze the search results:\n{'\n'.join(iteration_results)}\n"
                        f"Generate a refined search query to improve relevance."
                    ),
                    agent=self.agent,
                    expected_output="A single refined search query."
                )
                crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
                refined_query = crew.kickoff()
                current_query = refined_query.strip() if refined_query else current_query
                self.logger.info({"message": "Refined query", "query": current_query})

        final_result = "\n".join(results)
        self.search_cache[cache_key] = final_result
        self.logger.info({"message": "Cached search results", "query": query})
        self.console.print("""DeepSearch:\n""",style="#2ca88b")
        self.console.print(final_result,style="#2ca88b")
        return final_result

    def think_mode(self, task_description: str, context: str = "") -> str:
        """Process a task in Think mode with dynamic planning and iterative refinement."""
        plan_task = Task(
            description=(
                f"Task: {task_description}\nContext: {context}\n"
                "Generate a step-by-step plan to execute the task, including tool usage and dependencies."
            ),
            agent=self.agent,
            expected_output="A list of steps with tool assignments and dependencies."
        )
        crew = Crew(agents=[self.agent], tasks=[plan_task], verbose=False)
        plan = crew.kickoff()
        steps = plan.split("\n") if plan else ["Execute task directly"]

        thoughts = [f"Plan:\n{plan}"]
        for step in steps:
            if not step.strip():
                continue
            thoughts.append(f"Step: {step}\nProcessing...")
            try:
                task = Task(
                    description=f"{step}\nContext: {context}",
                    agent=self.agent,
                    expected_output="Result of the step execution."
                )
                crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
                result = crew.kickoff()
                thoughts.append(f"Result: {result}\n")
            except Exception as e:
                thoughts.append(f"Error in step: {str(e)}\n")
                self.logger.error({"error": "Think mode step failed", "step": step, "details": str(e)})
                break

        eval_task = Task(
            description=(
                f"Evaluate the results:\n{'\n'.join(thoughts)}\n"
                "Provide a final refined output or suggest additional steps if needed."
            ),
            agent=self.agent,
            expected_output="Final task output or additional steps."
        )
        crew = Crew(agents=[self.agent], tasks=[eval_task], verbose=False)
        final_result = crew.kickoff()
        thoughts.append(f"Final Evaluation: {final_result}")
        self.console.print("Think:\n")
        for thought in thoughts:
            self.console.print(thought,style='#2ca88b')
        return "\n".join(thoughts)

    def execute_task(self, task_request: TaskRequest, task_id: str,
                     progress_callback: Optional[Callable[[str, float, str], None]] = None) -> Dict[str, Any]:
        """Execute a task with optional DeepSearch and Think modes."""
        start_time = datetime.now()
        self.logger.info({"message": "Executing task", "task_id": task_id, "description": task_request.description})

        if progress_callback:
            progress_callback(task_id, 0.1, task_request.description)

        if task_request.description.startswith("Process image:"):
            result = self.process_image(task_request.description.split(":", 1)[1].strip())
            success = "Error" not in result
            execution_time = (datetime.now() - start_time).total_seconds()
            if not success:
                self.console.print(result,style="#ff1500")
            else:
                self.console.print(result,style='#2ca88b')
            return {
                "task_id": task_id,
                "result": result,
                "success": success,
                "execution_time": execution_time
            }
        elif task_request.description.startswith("Process PDF:"):
            result = self.process_pdf(task_request.description.split(":", 1)[1].strip())
            success = "Error" not in result
            execution_time = (datetime.now() - start_time).total_seconds()
            if not success:
                self.console.print(result,style="#ff1500")
            else:
                self.console.print(result,style='#2ca88b')
            return {
                "task_id": task_id,
                "result": result,
                "success": success,
                "execution_time": execution_time
            }

        context = ""
        if task_request.use_deepsearch:
            try:
                context = f"DeepSearch Results:\n{self.deep_search(task_request.description)}\n"
                if progress_callback:
                    progress_callback(task_id, 0.5, task_request.description)
            except Exception as e:
                context = f"DeepSearch Error: {str(e)}\n"
                self.logger.error({"error": "DeepSearch failed", "task_id": task_id, "details": str(e)})

        result = ""
        tools_to_try = task_request.preferred_tools + task_request.retry_tools
        for attempt, tool in enumerate(tools_to_try or [None], 1):
            try:
                if task_request.use_think:
                    result = self.think_mode(task_request.description, context)
                else:
                    full_description = f"{task_request.description}\n{context}" if context else task_request.description
                    task = Task(
                        description=full_description,
                        agent=self.agent,
                        expected_output="A comprehensive response to the task."
                    )
                    crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
                    result = str(crew.kickoff())
                break
            except Exception as e:
                self.logger.error(
                    {"error": f"Attempt {attempt} failed", "task_id": task_id, "tool": tool, "details": str(e)})
                if attempt == len(tools_to_try) or not tools_to_try:
                    try:
                        task = Task(
                            description=task_request.description,
                            agent=self.agent,
                            expected_output="A simplified response to the task."
                        )
                        crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
                        result = str(crew.kickoff())
                        break
                    except Exception as final_e:
                        result = f"Task Execution Error: {str(final_e)}"
                        break
                continue

        success = "Error" not in result
        execution_time = (datetime.now() - start_time).total_seconds()

        # Use thread-local connection for database operations
        conn = self._get_db_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO feedback (task_id, task_description, result, success, timestamp, execution_time, feedback_rating) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (task_id, task_request.description, result, success, start_time, execution_time,
                     task_request.feedback_rating)
                )
                for tool_name in task_request.preferred_tools + task_request.retry_tools:
                    conn.execute(
                        "INSERT INTO metrics (task_id, tool_name, execution_time, success, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (task_id, tool_name,
                         execution_time / len(task_request.preferred_tools + task_request.retry_tools or [1]), success,
                         start_time)
                    )
            conn.commit()
        except sqlite3.ProgrammingError as e:
            self.logger.error({"error": "Database operation failed", "task_id": task_id, "details": str(e)})
            result = f"Database Error: {str(e)}\nOriginal Result: {result}"
            success = False

        if progress_callback:
            progress_callback(task_id, 1.0, task_request.description)
        if not success:
            self.console.print(result, style="#ff1500")
        else:
            self.console.print(result, style='#2ca88b')
        return {
            "task_id": task_id,
            "result": result,
            "success": success,
            "execution_time": execution_time
        }

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def plan_subtasks(self, user_input: str) -> List[TaskRequest]:
        """Use the LLM to generate a list of TaskRequest objects for subtasks."""
        cache_key = f"plan:{user_input}"
        if cache_key in self.plan_cache:
            self.logger.info({"message": "Returning cached subtask plan", "input": user_input})
            return [TaskRequest(**task) for task in self.plan_cache[cache_key]]

        available_tools = [tool.name for tool in self.tools]
        task = Task(
            description=(
                f"User Input: {user_input}\n"
                f"Available Tools: {available_tools}\n"
                "Break down the input into a list of subtasks. For each subtask, provide:\n"
                "- description: A clear description of the subtask.\n"
                "- use_deepsearch: Boolean indicating if DeepSearch is needed.\n"
                "- use_think: Boolean indicating if Think mode is needed.\n"
                "- priority: Integer (1=low, 10=high) based on importance or dependency.\n"
                "- preferred_tools: List of tool names to use (from available tools).\n"
                "- retry_tools: List of alternative tools to try if preferred tools fail.\n"
                "- depends_on: List of task IDs this subtask depends on (use placeholders like 'task1').\n"
                "- condition: Optional condition for execution (e.g., 'success(task1)').\n"
                "- timeout: Integer timeout in seconds, estimated based on task complexity (e.g., 300 for simple, 600 for complex).\n"
                "Return the result as a JSON array of objects."
            ),
            agent=self.agent,
            expected_output="A JSON array of subtask objects."
        )
        try:
            crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
            result = crew.kickoff()
            if hasattr(result, 'raw'):
                result_str = result.raw
            else:
                result_str = str(result)
            subtasks = parse_task_json(result_str)
            for subtask in subtasks:
                subtask["preferred_tools"] = [
                    tool for tool in subtask.get("preferred_tools", [])
                    if tool in available_tools
                ]
                subtask["retry_tools"] = [
                    tool for tool in subtask.get("retry_tools", [])
                    if tool in available_tools and tool not in subtask.get("preferred_tools", [])
                ]
                subtask["timeout"] = max(subtask.get("timeout", self.config.default_task_timeout), 60)
            validated_subtasks = [TaskRequest(**subtask) for subtask in subtasks]
            self.plan_cache[cache_key] = subtasks
            self.logger.info(
                {"message": "Cached subtask plan", "input": user_input, "subtasks": len(validated_subtasks)})
            for i in validated_subtasks:
                self.console.print(str(i),style='#2ca88b')
            return validated_subtasks
        except ValueError as e:
            self.logger.error(
                {"error": "Failed to parse subtask plan", "details": str(e), "result_type": type(result).__name__})
            for i in result:
                self.console.print(str(i), style="#ff1500")
            return [TaskRequest(description=user_input, priority=1, timeout=self.config.default_task_timeout)]

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def summarize_responses(self, user_input: str, subtask_responses: List[Dict[str, Any]]) -> str:
        """Summarize subtask responses and user input using the LLM."""
        successful_responses = [r for r in subtask_responses if r["success"]]
        response_summary = "\n".join(
            f"Subtask {r['task_id']} (Description: {r['result'].split('\n')[0][:50]}...): {r['result']}"
            for r in successful_responses
        ) or "No successful subtask responses."
        failed_responses = "\n".join(
            f"Subtask {r['task_id']} failed: {r['result']}"
            for r in subtask_responses if not r["success"]
        )
        task = Task(
            description=(
                f"User Input: {user_input}\n"
                f"Successful Subtask Responses:\n{response_summary}\n"
                f"Failed Subtask Responses:\n{failed_responses}\n"
                "Summarize the subtask results, prioritizing successful outcomes, and provide a cohesive response "
                "that addresses the user's input. Include actionable insights and recommendations for any failures."
            ),
            agent=self.agent,
            expected_output="A summarized response with insights and recommendations."
        )
        try:
            crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
            result = crew.kickoff()
            if hasattr(result, 'raw'):
                return result.raw
            self.console.print(str(result), style='#2ca88b')
            return str(result)
        except Exception as e:
            self.logger.error({"error": "Failed to summarize responses", "details": str(e)})
            self.console.print(f"Summary Error: {str(e)}\nRaw Successful Responses:\n{response_summary}\nFailed Responses:\n{failed_responses}", style="#ff1500")
            return f"Summary Error: {str(e)}\nRaw Successful Responses:\n{response_summary}\nFailed Responses:\n{failed_responses}"

    def process_user_input(
            self,
            user_input: str,
            progress_callback: Optional[Callable[[str, float, str], None]] = None
    ) -> Dict[str, Any]:
        """Process a user input by generating subtasks, executing them, and summarizing the results."""
        self.logger.info({"message": "Processing user input", "input": user_input})
        task_group_id = str(uuid.uuid4())

        user_input = user_input.strip()
        if not user_input or len(user_input) > 10000:
            self.logger.error({"error": "Invalid user input", "details": "Empty or too long"})
            return {"user_input": user_input, "task_group_id": task_group_id, "subtask_responses": [],
                    "summary": "Error: Invalid input"}
        if any(char in user_input for char in ["<", ">", ";", "&", "|", "`"]):
            self.logger.error({"error": "Invalid user input", "details": "Contains potentially malicious characters"})
            return {"user_input": user_input, "task_group_id": task_group_id, "subtask_responses": [],
                    "summary": "Error: Malicious input detected"}

        subtasks = self.plan_subtasks(user_input)
        self.logger.info({"message": "Generated subtasks", "task_group_id": task_group_id, "count": len(subtasks)})

        task_id_map = {f"task{i + 1}": str(uuid.uuid4()) for i in range(len(subtasks))}
        for subtask in subtasks:
            subtask.depends_on = [task_id_map.get(dep, dep) for dep in subtask.depends_on]

        for task in subtasks:
            task_id = task_id_map.get(task.description, str(uuid.uuid4()))
            self.task_queue.put((task.priority, (task, task_id)))
            self.logger.info({"message": "Submitted subtask", "task_id": task_id, "description": task.description,
                              "priority": task.priority})

        subtask_responses = []
        completed_tasks = {}
        pending_tasks = subtasks.copy()

        while pending_tasks:
            executable_tasks = []
            while not self.task_queue.empty():
                priority, (task, task_id) = self.task_queue.get()
                if all(dep in completed_tasks for dep in task.depends_on):
                    executable_tasks.append((task, task_id))
                else:
                    self.task_queue.put((priority, (task, task_id)))

            if not executable_tasks:
                self.logger.warning(
                    {"message": "No executable tasks; possible dependency cycle", "task_group_id": task_group_id})
                break

            def execute_with_condition(task: TaskRequest, task_id: str):
                if task.condition:
                    condition_met = all(
                        completed_tasks.get(dep, {}).get("success", False)
                        for dep in task.depends_on
                        if f"success({dep})" in task.condition
                    )
                    if not condition_met:
                        self.logger.info({"message": "Skipping task due to unmet condition", "task_id": task_id,
                                          "condition": task.condition})
                        return {"task_id": task_id, "result": "Skipped due to condition", "success": False,
                                "execution_time": 0}
                return self.execute_task(task, task_id, progress_callback)

            futures = [
                self.executor.submit(execute_with_condition, task, task_id)
                for task, task_id in executable_tasks[:self.config.max_concurrent_tasks]
            ]
            for future in as_completed(futures):
                result = future.result()
                task, task_id = next((t, tid) for t, tid in executable_tasks if
                                     t.description in result["result"] or tid == result["task_id"])
                subtask_responses.append(result)
                completed_tasks[task_id] = result
                pending_tasks.remove(task)

        summary = self.summarize_responses(user_input, subtask_responses)
        self.logger.info({"message": "Completed processing", "task_group_id": task_group_id})
        self.console.print(str(summary), style='#2ca88b')
        return {
            "user_input": user_input,
            "task_group_id": task_group_id,
            "subtask_responses": subtask_responses,
            "summary": summary
        }


def general_agent(user_input):
    """Demonstrate the agent's capabilities with example user inputs."""
    config = AgentConfig(
        nextcloud_username=os.getenv("NEXTCLOUD_USERNAME", ""),
        nextcloud_password=SecretStr(os.getenv("NEXTCLOUD_PASSWORD", "")),
        openweather_api_key=SecretStr(os.getenv("OPENWEATHER_API_KEY", "")) if os.getenv(
            "OPENWEATHER_API_KEY") else None
    )
    agent = GeneralPurposeAgent(config)

    def progress_callback(task_id: str, progress: float, description: str):
        try:
            priority = next(t.priority for t, _ in agent.task_queue.queue if t.description == description)
        except StopIteration:
            priority = "N/A"
        tools = ", ".join(tool.name for tool in agent.tools) or "none"
        print(
            f"Task {task_id} (Priority: {priority}, Tools: {tools}, {description[:50]}...): {progress * 100:.0f}% complete")

    agent.init_browser()
    try:
        result = agent.process_user_input(user_input, progress_callback)
    finally:
        agent.close_browser()
    return result['summary']

if __name__ == "__main__":
    result=general_agent("Research the latest AI advancements, summarize their impact on cloud storage")
    print(result)