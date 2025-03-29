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

from typing import List
from datetime import datetime, timedelta
from collections import deque
from functools import lru_cache
import hashlib
from langchain.prompts import ChatPromptTemplate
from core.Agent_models import get_model
from pydantic import BaseModel, Field
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentConfig(BaseModel):
    name: str
    description: str
    examples: List[str]
    keywords: List[str]

class RouterResponse(BaseModel):
    selected_agent: str = Field(description="Name of the selected agent")
    inputs:str = Field(description="Described input to that Agent")

class VisionRouter:
    def __init__(self, agents: List[AgentConfig], config: dict = None):
        self.llm = get_model()
        self.agents = {agent.name: agent for agent in agents}
        self.prompt = self._create_prompt()
        self.history: deque[dict] = deque(maxlen=2000)
        self.ratelimiter: deque[datetime] = deque(maxlen=100)
        self.stats = {
            "total": 0,
            "errors": 0,
            "cached": 0,
            "agent_counts": {agent.name: 0 for agent in agents}
        }
        self.cfg = config or {
            "req_limit": (10, 60),
            "cache_size": 2000,
            "max_input": 1500
        }

    def _create_prompt(self):
            agent_descriptions = "\n".join(
                f"{agent.name}: {agent.description}\nExamples: {', '.join(agent.examples)}"
                for agent in self.agents.values()
            )

            return ChatPromptTemplate.from_messages([
                ("system", self.system_prompt(agent_descriptions)),
                ("human", "{input}")
            ])
    @staticmethod
    def system_prompt(agent_descriptions):
        return f"""**Multi-Agent Routing System**

    Available Agents:
    {agent_descriptions}
    """+"""
    Routing Rules:
    1. Select the most appropriate agent based on input keywords, examples, and priority.
    2. Prioritize planning tasks (e.g., scheduling, reminders) for the PERSONAL agent when detected.
    3. Require explicit visual references for VISION agent; never assume visual context.
    4. Extract specific parameters (e.g., time, date, task) for planning-related inputs.
    5. Return JSON with agent name, tailored input.
    Response Format:
    {{"selected_agent": "agent_name","inputs": "specific_input_for_agent"}}"""

    def extract_json(self,text: str) -> dict:
        """
        Extracts JSON object from text if available.

        Args:
            text (str): Input text containing JSON

        Returns:
            dict: Extracted JSON object or empty dict if not found
        """
        import json
        # Regex pattern to match JSON object
        json_pattern = r'\{.*?\}'
        match = re.search(json_pattern, text, re.DOTALL)

        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return {}
        return {}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.3))
    def _process(self, query: str):
        @lru_cache(maxsize=self.cfg["cache_size"])
        def _cached_execution(hash_str: str):
            try:
                chain = self.prompt | self.llm
                raw_response = chain.invoke({"input": query})
                # Assuming raw_response is a string containing JSON
                return RouterResponse(**self.extract_json(raw_response.content))
            except Exception as ex:
                logger.error(f"Execution error: {ex}")
                raise

        query_hash = hashlib.sha256(query.encode()).hexdigest()
        if result := _cached_execution(query_hash):
            self.stats["cached"] += 1
            return result
        return _cached_execution(query_hash)

    def _clean_input(self, text: str) -> str:
        clean = text.strip().replace('\0', '')[:self.cfg["max_input"]]
        if not clean:
            raise ValueError("Invalid empty input")
        return clean

    def _check_limit(self):
        window = timedelta(seconds=self.cfg["req_limit"][1])
        now = datetime.now()
        while self.ratelimiter and now - self.ratelimiter[0] > window:
            self.ratelimiter.popleft()
        if len(self.ratelimiter) >= self.cfg["req_limit"][0]:
            raise RuntimeError("Rate limit exceeded")

    def route(self, user_input: str) -> RouterResponse:
        self.stats["total"] += 1
        try:
            self._check_limit()
            clean_text = self._clean_input(user_input)

            if any(entry["text"] == clean_text for entry in self.history):
                logger.warning("Duplicate request detected")
                return self.history[-1]["response"]

            self.ratelimiter.append(datetime.now())
            result = self._process(clean_text)

            self.history.append({
                "timestamp": datetime.utcnow(),
                "text": clean_text,
                "response": result,
                "latency": datetime.utcnow().timestamp()
            })

            self.stats["agent_counts"][result.selected_agent] += 1
            return result

        except Exception as err:
            self.stats["errors"] += 1
            logger.error(f"Routing error: {err}")
            raise

    def metrics(self) -> dict:
        return self.stats | {
            "health": self.stats["total"] - self.stats["errors"] / max(1, self.stats["total"]),
            "rps": self.stats["total"] / (
                datetime.now() - self.ratelimiter[0]).total_seconds()
                if self.ratelimiter else 0
        }


if __name__ == "__main__":
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
    router = VisionRouter(agents)
    print(router.route("Jarvis what did i do yesterday?"))