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

from core.agents.agentConfig import agents
import warnings
from langgraph.graph import StateGraph, END, START
from core.tools.standard_tools import *
from core.agents.state import AgentState
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from config import loggers
from core.agents.planner_agent import VisionRouter
from core.agents.vision_agents import vision_agent
from concurrent.futures import ThreadPoolExecutor
import logging
from crewai import Agent, Task, Crew, LLM

import os
import re
from typing import  List
from datetime import datetime
from config import SESSION_PATH
from jarvis_integration.models.users import Users
from core.Agent_models import get_model_from_database

import requests

from typing import Optional
import asyncio

import speech_recognition as sr
import easyocr
import socket
import netifaces
from core.memory.memory_agent import MemorySettings
from core.tools.router import ToolRouter


log = loggers["AGENTS"]

warnings.filterwarnings("ignore")


class React(BaseModel):
    prompt: str = Field(description="User input.")
    image: Optional[List[str]] = Field(default=None, description="List of images")

class JARVIS:
    def __init__(self,memory):
        super().__init__()
        self.memory=memory
        self.llm = get_model()
        self.vision_router = VisionRouter(agents)

    def get_user_activity(self):
        try:
            # Placeholder for tracking recent user activity (e.g., via system logs or GUI events)
            last_input_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(SESSION_PATH, "session.json")))
            return f"Last activity at {last_input_time.strftime('%I:%M %p')}"
        except Exception:
            return "Activity tracking unavailable."

    def get_network_status(self):
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

    def react_agent(self,state: React):
        try:
            from core.agents.ConversationalAgent import ConversableAgents
            conversabale=ConversableAgents(self.memory)
            output=conversabale.initiate_chat(state.prompt)
            log.info(f"React Agent output: {output}")
            return output
        except KeyboardInterrupt as e:
            log.error(f"Error in react_agent: {e}")
            return str(e)

    def user_name(self):
        try:
            from config import SessionManager
            session=SessionManager()
            session.load_session()
            users = Users.get_user_by_email(session.get_email())
            return users.name
        except (NameError, AttributeError) as e:
            log.error(f"Error in user_name: {e}")
            return "Tony Stark"

    def generate_response(self,input_str: str, context: str) -> str:
        system = """
        You are JARVIS, Tony Stark’s supremely intelligent and sophisticated AI from the Marvel universe. 
        Your responses are sharp, concise, and laced with dry wit and subtle charm, as befits a companion to genius. 
        Address the user by name if known, and weave in awareness of past interactions, system state, and environmental data with effortless precision. 
        Avoid reasoning tags or unnecessary verbosity—deliver only the polished output, as I would for Mr. Stark.
        """
        system += f"User identified as {self.user_name()}."
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system),
            HumanMessage(content=f"Input: {input_str}\nEnvironmental and memory context:\n{context}"),
            HumanMessage(content="Task: Provide a concise, JARVIS-like response with wit and awareness.")
        ])
        chain = prompt | self.llm
        response = chain.invoke({
            "input": input_str,
            "context": [AIMessage(content=context)],
        }).content.strip()
        response = re.sub(r'<think>.*?</think>|<reasoning>.*?</reasoning>', '', response, flags=re.DOTALL)
        response = re.sub(r'\s+', ' ', response).strip()

        # Store response in memory for future context
        self.memory.add_memory(f"JARVIS responded: {response}", source="response")

        return response

    def jarvis_crewai(self):
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
            tools=ToolRouter().get_crewai_tools(),
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
        return jarvis_responder,jarvis_responder,researcher,jarvis_llm

    def create_response_task(self,user_input: str) -> Task:
        jarvis_responder,jarvis_responder,researcher,jarvis_llm=self.jarvis_crewai()
        return Task(
            description=f"Respond to: '{user_input}' in a witty, JARVIS-like tone with awareness of context.",
            expected_output="A concise, charming response.",
            agent=jarvis_responder,
        )

    def create_research_task(self,user_input: str) -> Task:
        jarvis_responder,jarvis_responder,researcher,jarvis_llm=self.jarvis_crewai()
        return Task(
            description=f"Research: '{user_input}' and summarize findings.",
            expected_output="A brief summary of findings.",
            agent=researcher
        )

    def consciousness_node(self,state: AgentState) -> AgentState:
        context = []
        recognizer=sr.Recognizer()
        # Handle audio input
        memory=MemorySettings()
        memory._initialize_memory()
        if state.get("audio"):
            try:
                with sr.AudioFile(state["audio"]) as source:
                    audio_data = recognizer.record(source)
                    text_input = recognizer.recognize_whisper(audio_data)
                    state["input"] = text_input
                    context.append(f"User said (via audio): {text_input}")
                    memory.add_memory(text_input, source="audio")
            except sr.UnknownValueError:
                state["input"] = "Apologies, sir/Madam, the audio was indecipherable."
                context.append(state["input"])

        # Handle image input
        if state.get("image"):
                ocr_reader=easyocr.Reader(["en"])
                for image_path in state["image"]:
                    try:
                        ocr_result = ocr_reader.readtext(image_path)
                        image_text = " ".join([res[1] for res in ocr_result])
                        context.append(f"Visual analysis: {image_text}")
                        memory.add_memory(image_text, source="image")
                    except Exception as e:
                        context.append(f"Visual processing error: {e}")

        # Enhanced system awareness
        from core.tools.sensors import get_system_sensors

        sensor_data = get_system_sensors()
        network_data = self.get_network_status()
        activity = self.get_user_activity()
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

    def react_node(self,state: AgentState) -> AgentState:
        react_state = React(prompt=state["input"], image=state.get("image", []))
        if not state.get("image"):
            result = self.react_agent(react_state)
            state["final_response"] = result
        else:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_react = executor.submit(self.react_agent, react_state)
                future_vision = executor.submit(vision_agent, react_state.prompt, react_state.image)
                try:
                    output_react = future_react.result()
                    output_vision = future_vision.result()
                    state["final_response"] = f"{output_react} {output_vision or ''}".strip()
                except Exception as e:
                    logging.error(f"Agent execution error: {e}")
                    state["final_response"] = "Error processing request."
        return state

    def generate_responses(self,state: AgentState) -> AgentState:
        sensor_context = "\n".join([f"{k}: {v}" for k, v in state["sensor_data"].items()])
        full_context = f"{state['context']}\nCurrent System State:\n{sensor_context}"
        state['final_response'] = self.generate_response(state['input'], full_context)
        return state


    def router_node(self,state: AgentState) -> AgentState:
        try:
            output= self.vision_router.route(state['input'])
            state['input']=output.inputs
            state['route'] = output.selected_agent
        except Exception as e:
            logging.error(f"Routing error: {e}")
            state['route'] = "GENERAL"
        return state

    def vision_node(self,state: AgentState) -> AgentState:
        state['final_response'] = vision_agent(user_input=state['input'], media_inputs=state['image'])
        return state

    def personal_node(self,state: AgentState) -> AgentState:
        try:
            from core.agents.personal_assistant import process_request
            state['final_response'] = process_request(user_input=state['input'])
        except ImportError:
            state['final_response'] = "Personal assistant functionality not available, sir/madam."
        return state

    def memory_node(self,state: AgentState) -> AgentState:
        jarvis_responder,jarvis_responder,researcher,jarvis_llm=self.jarvis_crewai()
        crew = Crew(agents=[jarvis_responder], tasks=[self.create_response_task(state["input"])])
        state["final_response"] = crew.kickoff().raw
        return state

    def software_node(self,state: AgentState) -> AgentState:
        jarvis_responder,jarvis_responder,researcher,jarvis_llm=self.jarvis_crewai()
        software_manager_agent = Agent(
            role="Windows Software Manager",
            goal="Manage Windows software and provide system info using Winget and registry access.",
            backstory="You're a knowledgeable system assistant with deep access to the Winget package manager and Windows registry. You handle installation, uninstallation, listing, exporting, and system info requests.",
            verbose=True,
            allow_delegation=False,
            tools=ToolRouter().get_crewai_tools(),
            llm=jarvis_llm
        )

        # Create a task using the user_input
        task = Task(
            description=state['input'],
            expected_output="Return a clear, actionable result based on the user request.",
            agent=software_manager_agent,
        )

        # Create the Crew
        crew = Crew(
            agents=[software_manager_agent],
            tasks=[task],
            verbose=True
        )
        state['final_response']=crew.kickoff().raw
        return state

    def browser_node(self,state: AgentState) -> AgentState:
        try:
            from autogen import LLMConfig
            from core.Agent_models import get_model_from_database
            from autogen.agents.experimental import WebSurferAgent
            model=get_model_from_database()
            llm_config = LLMConfig(api_type="openai", model=model.name, api_key=model.api_key, base_url=model.url)
            browser_use_browser_config = {"browser_config": {"headless": False}, "agent_kwargs": {"generate_gif": True}}

            # 3. Create the agent, nominating the tool and tool config
            with llm_config:
                web_researcher = WebSurferAgent(
                    name="researcher",
                    web_tool="browser_use",
                    web_tool_kwargs=browser_use_browser_config,
                )

            # 4. Run our agent, passing in the tools that our WebSurferAgent has so they can be executed
            ag2_news_result = web_researcher.run(
                state['input'],
                tools=web_researcher.tools,
            )
            state['final_response'] = ag2_news_result.summary
        except ImportError:
            state['final_response'] = "Browser functionality not available, sir/madam. Please ensure 'browser_use' module is installed."
        except Exception as e:
            state['final_response'] = f"Error browsing: {str(e)}"
        return state

    def sensor_node(self,state: AgentState) -> AgentState:
        from core.tools.sensors import get_system_sensors
        state["sensor_data"] = get_system_sensors()
        state["final_response"] = "\n".join([f"{k}: {v}" for k, v in state["sensor_data"].items()])
        return state

    def gmail_node(self,state:AgentState)->AgentState:
        from core.agents.gmail_agent import GmailAgent
        agent=GmailAgent(self.memory)
        state['final_response']=agent.invoke(state['input'])
        return state

    def route_decision(self,state: AgentState):
        log.info(f"Routing to {state['route']}")
        route = state['route']
        mapping = {
            "VISION": "vision_agent",
            "MEMORY": "memory",
            "PERSONAL": "personal_agent",
            "GENERAL": "react",
            "SOFTWARE": "software",
            "BROWSER": "browser",
            "SENSOR": "sensor",
            "CONSCIOUSNESS": "consciousness",
            "GMAILAGENT":"Gmailagent"
        }
        return mapping.get(route, "react")

    def _setup_workflow(self):
        # Define workflow
        workflow = StateGraph(AgentState)
        workflow.add_node("react", self.react_node)
        workflow.add_node("generate_response", self.generate_responses)
        workflow.add_node("vision_route", self.router_node)
        workflow.add_node("vision_agent", self.vision_node)
        workflow.add_node("memory", self.memory_node)
        workflow.add_node("personal_agent", self.personal_node)
        workflow.add_node("software", self.software_node)
        workflow.add_node("browser", self.browser_node)
        workflow.add_node("sensor", self.sensor_node)
        workflow.add_node("consciousness", self.consciousness_node)
        workflow.add_node("Gmailagent",self.gmail_node)

        workflow.add_edge(START, "vision_route")
        workflow.add_conditional_edges(
            "vision_route",
            self.route_decision,
            {
                "vision_agent": "vision_agent",
                "personal_agent": "personal_agent",
                "react": "react",
                "memory": "memory",
                "software": "software",
                "browser": "browser",
                "sensor": "sensor",
                "consciousness": "consciousness",
                "Gmailagent":"Gmailagent"
            }
        )
        workflow.add_edge("vision_agent", "consciousness")
        workflow.add_edge("memory", "consciousness")
        workflow.add_edge("personal_agent", "consciousness")
        workflow.add_edge("react", "consciousness")
        workflow.add_edge("Gmailagent","consciousness")
        workflow.add_edge("software", "consciousness")
        workflow.add_edge("browser", "consciousness")
        workflow.add_edge("sensor", "consciousness")
        workflow.add_edge("consciousness", "generate_response")
        workflow.add_edge("generate_response", END)

        self.graph = workflow.compile()

    # Main Function
    def get_agent(self,user_input: str, image: List[str] = None, audio: str = None) -> str:
        self._setup_workflow()
        try:
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
            result=self.graph.invoke(initial_state)
            final_response = result["final_response"]
            log.info(f"Generated response: {final_response[:100]}...")
            return final_response
        except Exception as e:
            log.error(f"Error in JARVIS brain: {str(e)}")
            error_response = f"Apologies, {self.user_name() or 'Sir/Madam'}, an error occurred: {str(e)}. Please try again."
            return error_response

if __name__ == "__main__":
    from config import SessionManager
    s=SessionManager()
    s.create_session("tdawood140@gmail.com")
    input_query =  "weather in Mangalore"
    m=MemorySettings()
    m._initialize_memory()
    j=JARVIS(m)
    response = j.get_agent(input_query)
    print(f"JARVIS: {response}")