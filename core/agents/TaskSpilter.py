import asyncio
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langchain.tools.base import Tool
from core.memory.memory_agent import MemorySettings
from typing import List, Dict, Callable
import logging
from langchain.prompts import ChatPromptTemplate
from core.Agent_models import get_model  # Assumed to return an LLM chain
import re, json
from typing_extensions import TypedDict
from functools import lru_cache
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentConfig(BaseModel):
    name: str
    description: str
    examples: List[str]
    keywords: List[str]
    fun:Callable[[str],str]

# --- Agent Tool Wrappers ---
def make_tool(agent_name: str, agent_func: Callable[[str], str]) -> Tool:
    def tool_func(input: str) -> str:
        logger.info(f"Routing to {agent_name}: {input}")
        return agent_func(input)

    return Tool(
        name=agent_name,
        description=f"{agent_name} handles related tasks",
        func=tool_func
    )

# --- Coordinating Agent ---
class TaskSpliterAgent:
    def __init__(self):
        # Simulate multiple agents

        self.llm = get_model()

        # Prompt for task splitting (concise with few-shot examples)
        self.split_prompt = ChatPromptTemplate.from_messages([
            ("system", """
Split the input into distinct tasks. Each task is a single action/request.
Examples:
- Input: "Set a reminder and analyze photo, explain AI"
  Output: {{"tasks": ["Set a reminder", "Analyze photo", "Explain AI"]}}
- Input: "What is quantum mechanics?"
  Output: {{"tasks": ["What is quantum mechanics?"]}}

Return JSON: {{"tasks": ["task1", "task2", ...]}}
"""),
            ("human", "{input}")
        ])


    def initiate_chat(self, user_input: str) -> List[str]:
        chain = self.split_prompt | self.llm
        try:
            response = chain.invoke({"input": user_input})
            logger.debug(f"LLM task split response: {response.content}")
            match = re.search(r'\{.*?\}', response.content, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                tasks = parsed.get("tasks", [])
                if not tasks:
                    logger.warning("No tasks found in LLM response. Treating input as single task.")
                    return [user_input]
                return [task.strip() for task in tasks if task.strip()]
        except Exception as e:
            logger.warning(f"Task splitting failed: {e}. Treating input as single task.")
        return [user_input]




# --- Example Execution ---
if __name__ == "__main__":
    from config import SessionManager
    s=SessionManager()
    s.create_session("tdawood140@gmail.com")
    def main():
        agent = TaskSpliterAgent()
        user_input = "Set a reminder for my workout and analyze this photo, then tell me about quantum mechanics"
        return agent.initiate_chat(user_input)


    result = main()
    # Result is returned instead of printed
    print(result)