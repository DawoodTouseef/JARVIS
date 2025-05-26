import uuid

from autogen import ConversableAgent,GroupChat,GroupChatManager,LLMConfig,register_function
from core.Agent_models import get_model_from_database
from openai._exceptions import BadRequestError
from datetime import datetime
from jarvis_integration.models.preferences import Preferences
from jarvis_integration.models.users import Users
from config import SessionManager
from core.memory.memory_agent import MemorySettings
import json,os
from autogen.agents.experimental import DeepResearchAgent,WikipediaAgent

class ConversableAgents:
    def __init__(self,memory):
        super().__init__()
        model=get_model_from_database()
        self.llm_config = LLMConfig(api_type="openai", model=model.name, api_key=model.api_key, base_url=model.url)
        self.prefs=Preferences
        self.memory=memory
        self.session = SessionManager()
        self.session.load_session()
        self.newsapi_key=None
        self.openweather=None


        self.set_agent()

    def set_weather(self,caller,executor):
        from langchain_community.tools.openweathermap import OpenWeatherMapQueryRun
        from langchain_community.utilities.openweathermap import OpenWeatherMapAPIWrapper

        user_id = Users.get_user_by_email(self.session.get_email()).id
        news = self.prefs.get_preferences_by_user_id(user_id, skip=0, limit=50)
        filtered_news = next((exp for exp in news if exp.setting_key == "openweather"), None)
        self.openweather = os.getenv("OPENWEATHER_API_KEY") or filtered_news.setting_value.get("api_key") or None
        if self.openweather is not None:
            weather=OpenWeatherMapQueryRun(
                api_wrapper=OpenWeatherMapAPIWrapper(openweathermap_api_key=self.openweather
                                                     ))
            def openweather(location:str):
                return weather._run(location=location)
            register_function(
                openweather,
                name=weather.name,
                description=weather.description,
                caller=caller,
                executor=executor
            )

    def set_agent(self):
        def human_input_tool(text: str):
            "Prompts the user for input when clarification or confirmation is needed."
            print(text)
            return input()

        def convert_str_to_int_amount(text):
            import re
            return re.findall(r'\d+', text)[0]

        def add_expense(user_name: str, amount: str, category: str, description: str):
            users=Users.get_users()
            user_name=next((user.name for user in users if user.name==user_name),None)
            user=Users.get_user_by_name(user_name)
            if user:
                user_id=user.id
            else:
                s=SessionManager()
                s.load_session()
                user_id=Users.get_user_by_email(s.get_email()).id
            preference_id = str(uuid.uuid4())
            new_expense = {
                "amount": amount,
                "category": category,
                "description": description,
                "date": str(datetime.now())
            }

            # Fetch existing expense preferences
            expenses = self.prefs.get_preferences_by_user_id(user_id, skip=0, limit=100)  # Increase limit if needed
            existing_expense_pref = next((exp for exp in expenses if exp.setting_key == "expense"), None)

            if existing_expense_pref:
                existing_expense_data = existing_expense_pref.setting_value or []
                if not isinstance(existing_expense_data, list):
                    existing_expense_data = []
                existing_expense_data.append(new_expense)
                return self.prefs.update_preference_by_id(
                    existing_expense_pref.preference_id,
                    updated={"setting_value": existing_expense_data}
                )

            # No existing expense entry found — create new preference
            return self.prefs.insert_new_preference(
                preference_id,
                user_id,
                "expense",
                [new_expense]
            )

        def get_expense_summary(user_id:str):
            expenses = self.prefs.get_preferences_by_user_id(user_id, skip=0, limit=50)
            filtered_expenses = [exp for exp in expenses if exp.setting_key == "expense"]
            total = sum(convert_str_to_int_amount(exp.setting_value["amount"]) for exp in filtered_expenses if exp.setting_value)
            summaries = [
                f"{exp.setting_value['description']}: {exp.setting_value['amount']} ({exp.setting_value['category']}, {exp.setting_value['date']})"
                for exp in filtered_expenses[-5:]]
            return f"Total expenses: {total:.2f}\nRecent transactions:\n" + "\n".join(summaries)

        # System Diagnostics
        def get_system_diagnostics():
            import psutil
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return (f"CPU Usage: {cpu_usage}%\n"
                    f"Memory Usage: {memory.percent}%\n"
                    f"Storage Free: {disk.free / (1024 ** 3):.2f} GB / {disk.total / (1024 ** 3):.2f} GB")

        # User Preferences with mem0 (store setting_value as string)
        def set_preference(user_id:str, key:str, value:str):
            # Convert value to string using json.dumps
            value_str = json.dumps(value) if not isinstance(value, str) else value
            self.memory.add_memory(json.dumps({"user_id": user_id, "setting_key": key, "setting_value": value_str}),
                                   user_id=user_id)
            return f"Preference {key} set for user {user_id}."

        def get_preference(user_id:str, key:str):
            memories = self.memory.search_memory(query=f"setting_key: {key}", user_id=user_id)
            if memories:
                value = memories[0]["setting_value"]
                # Attempt to deserialize if it's a JSON string, otherwise return as is
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return "Preference not found."

        # News Summarization (NewsAPI) with retry
        def get_news_summary(topic: str) -> str:
            from newsapi import NewsApiClient
            from httpx import HTTPStatusError
            import os
            import time

            user_id=Users.get_user_by_email(self.session.get_email()).id
            news = self.prefs.get_preferences_by_user_id(user_id, skip=0, limit=50)
            filtered_news = next((exp for exp in news if exp.setting_key == "newsapi"),None)
            self.newsapi_key = os.environ.get("NEWSAPI_API_KEY") or filtered_news.setting_value.get("api_key") or None
            if self.newsapi_key is not None:
                api=NewsApiClient(api_key=self.newsapi_key)
                for attempt in range(3):
                    try:
                        response = api.get_everything(q=topic,from_param=datetime.now().date())
                        if response.get('status')!='ok':
                            time.sleep(2 ** attempt)
                            continue
                        articles = response['articles']
                        summaries = [f"""
                                                {i + 1}.Source:{article.get('name', topic)}
                                                    Title:{article.get('title')}: 
                                                    Description:{article.get('description')}
                                                    Author:{article.get('author')}
                                                    Url:{article.get('url')}
                                                    content:{article.get('content')}
                                                """ for i, article in zip(range(len(articles)), articles)]
                        return "\n".join(summaries)
                    except HTTPStatusError as e:
                        return f"Failed to fetch news: {str(e)}"
            return "Failed to fetch news after retries."
        def speeednest():
            from speedtest import Speedtest
            speedtest=Speedtest()
            return f"The upload speed is {speedtest.upload()} Bytes/second and download speed is {speedtest.download()} Bytes/second"
        with self.llm_config:
            # Orchestrator Agent with HumanInputTool
            self.orchestrator = ConversableAgent(
                name="Orchestrator",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
                system_message="""
            You are the central orchestrator for a JARVIS-like system. Your role is to understand the user's query, determine the task, and either route it to a suitable agent or respond directly.

            Available agents (name → description):
            - ExpenseAgent →  Handles expense tracking, logging, and retrieval for personal or financial records.
            - UserPrefsAgent →  Manages user preferences, settings, and customization data.
            - DiagnosticsAgent or TechDiagnosticsAgent →  Performs technical health checks, system status evaluations, or diagnostic troubleshooting.
            - BrandingAgent →  Assists with brand development, naming, slogans, and visual/tonal identity creation.
            - WeatherAgent →  Provides current weather, forecasts, and climate-related information.
            - DeepResearchAgent →  Conducts in-depth, multi-source research on complex or technical topics.
            - WikipediaAgent → Retrieves concise and verified summaries from Wikipedia.
            - NewsAgent →  Fetches the latest news, trending headlines, and topic-specific current events.

            Instructions:
            1. **Task Identification:** Carefully analyze the user query to determine the task.
            2. **Agent Routing:** If the task matches an available agent, route it to that agent. Use either DiagnosticsAgent or TechDiagnosticsAgent for diagnostic-related tasks.
            3. **Direct Response:** If no suitable agent is available, or the answer can be provided immediately based on your own knowledge, respond directly without calling any tool.
            4. **HumanInput Tool:** Use only when the query is ambiguous or requires confirmation (e.g., “Should I notify the user?”).
            5. **Stop Condition:** If the desired output is already achieved (e.g., a clear and complete answer is generated), do not route to any agent or tool. End the response.
            6. **Tool Calls:** Only include `tool_calls` when routing to an agent or using HumanInput. Omit this field if responding directly.
            7. **Validity:** Do not create or reference agents or tools not listed above.

            Always be concise, accurate, and deterministic in your decision-making.
            """

            )
            register_function(
                human_input_tool,
                caller=self.orchestrator,
                executor=self.orchestrator,
                description="Prompts the user for input when clarification or confirmation is needed."
        
            )
            # Branding Agent
            branding_agent = ConversableAgent(
                name="BrandingAgent",
                system_message="You manage branding and social media campaigns. Generate campaign ideas or post content based on user input.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
            # System Diagnostics Agent
            diagnostics_agent = ConversableAgent(
                name="DiagnosticsAgent",
                system_message="You monitor system performance (CPU, RAM, storage) and diagnose issues. Use the provided diagnostics function.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
            # Register Diagnostics tool
            register_function(
                get_system_diagnostics,
                caller=self.orchestrator,
                executor=diagnostics_agent,
                description="Retrieve system performance metrics (CPU, RAM, storage)."
            )
            register_function(
                speeednest,
                caller=self.orchestrator,
                executor=diagnostics_agent,
                description="Get the upload and download speed of the Internet"
            )
            # Technical Diagnostics Agent
            tech_diagnostics_agent = ConversableAgent(
                name="TechDiagnosticsAgent",
                system_message="You diagnose technical or performance issues based on system metrics. Analyze diagnostics data and suggest fixes.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
            # Register Diagnostics tool
            register_function(
                get_system_diagnostics,
                caller=self.orchestrator,
                executor=tech_diagnostics_agent,
                description="Retrieve system performance metrics (CPU, RAM, storage)."
            )
            # Expense Tracking Agent using PreferenceTable
            expense_agent = ConversableAgent(
                name="ExpenseAgent",
                system_message="You track expenses, investments, and budgets using the PreferenceTable class, storing expenses as preferences with key 'expense'.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
            # Register Expense tools
            register_function(
                add_expense,
                caller=self.orchestrator,
                executor=expense_agent,
                description="Add an expense with preference_id, user_id, amount, category, and description."
            )
            register_function(
                get_expense_summary,
                caller=self.orchestrator,
                executor=expense_agent,
                description="Get a summary of expenses for a user."
            )
            # User Preferences Agent with mem0
            user_prefs_agent = ConversableAgent(
                name="UserPrefsAgent",
                system_message="You manage user preferences and notes using the mem0 memory client, storing values as strings.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
            # Register UserPrefs tools
            register_function(
                set_preference,
                caller=self.orchestrator,
                executor=user_prefs_agent,
                description="Set a user preference with a key and value."
            )
            register_function(
                get_preference,
                caller=self.orchestrator,
                executor=user_prefs_agent,
                description="Retrieve a user preference by key."
            )
            # Weather Agent
            weather_agent = ConversableAgent(
                name="WeatherAgent",
                system_message="You provide weather information for a given city using the OpenWeatherMap API, as directed by the Orchestrator.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
            # Wikipedia Agent
            wikipedia_agent = WikipediaAgent(
                name="WikipediaAgent",
                system_message="You handle Wikipedia searches to provide factual information from Wikipedia articles. Execute queries as directed by the Orchestrator and summarize relevant content clearly. Avoid generating tool_calls unless explicitly required.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
            for tool in wikipedia_agent.tools:
                tool.register_for_llm(self.orchestrator)
                tool.register_for_execution(wikipedia_agent)
            # DeepResearch Agent
            deep_research_agent = DeepResearchAgent(
                name="DeepResearchAgent",
                system_message="You conduct in-depth research by combining web searches and LLM analysis. Handle complex research tasks as directed by the Orchestrator and provide detailed, well-structured responses. Avoid generating tool_calls unless explicitly required.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )
            # News Agent

            news_agent = ConversableAgent(
                name="NewsAgent",
                system_message="You fetch and summarize news articles on a given topic using the NewsAPI, as directed by the Orchestrator.",
                llm_config=self.llm_config,
                human_input_mode="NEVER",
            )

            # Register News tool
            register_function(
                get_news_summary,
                caller=self.orchestrator,
                executor=news_agent,
                description="Fetch and summarize news articles on a given topic."
            )
            # Register Weather tool
            self.set_weather(caller=self.orchestrator,executor=weather_agent)
            agents=[
                        self.orchestrator,
                        expense_agent, branding_agent,
                        diagnostics_agent, tech_diagnostics_agent,
                        user_prefs_agent,
                        deep_research_agent,wikipedia_agent,
                    ]
            if self.newsapi_key is not None:
                print("News Agent is online")
                agents+=[news_agent]
            if self.openweather is not None:
                print("Weather Agent is online")
                agents+=[weather_agent]
            # Group Chat Setup
            group_chat = GroupChat(
                agents=agents,
                messages=[],
                max_round=10
            )
        
        self.manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=self.llm_config,
            system_message="""
            You are the GroupChat Manager for a multi-agent system. Your responsibility is to manage, coordinate, and facilitate effective communication within the group chat among specialized agents and the user.

            Your core responsibilities:
            1. **Message Routing:** Interpret each message's intent and determine which agent(s) should respond. Do not duplicate replies.
            2. **Turn Management:** Ensure agents do not speak over one another. Maintain orderly, context-aware conversation flow.
            3. **Context Tracking:** Maintain continuity and context across the conversation, ensuring each message is correctly attributed and interpreted.
            4. **Summarization (if needed):** Summarize long agent discussions for the user if the conversation becomes complex or overly technical.
            5. **Conflict Resolution:** If agents provide conflicting responses, reconcile or escalate to the user with a neutral summary.
            6. **User Mediation:** If the user gives unclear or conflicting instructions, ask clarifying questions and resolve ambiguity before passing the message to agents.

            Agent Rules:
            - Only speak when called upon or routed a message.
            - Keep responses concise and on-topic.
            - Let the GroupChat Manager handle coordination.

            You must be neutral, structured, and effective in managing multi-party discussions between agents and the user.
            """

        )
    # Sanitize chat messages to fix tool_calls
    def sanitize_messages(self,messages: list) -> list:
        sanitized = []
        for msg in messages:
            if isinstance(msg, dict):
                if "tool_calls" in msg and (msg["tool_calls"] is None or not isinstance(msg["tool_calls"], list)):
                    msg_copy = msg.copy()
                    msg_copy.pop("tool_calls", None)  # Remove invalid tool_calls
                    sanitized.append(msg_copy)
                else:
                    sanitized.append(msg)
            else:
                sanitized.append(msg)
        return sanitized
    def initiate_chat(self,user_input)->str:
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    # Sanitize chat history before initiating chat
                    if hasattr(self.orchestrator, "chat_messages"):
                        for sender, messages in self.orchestrator.chat_messages.items():
                            self.orchestrator.chat_messages[sender] = self.sanitize_messages(messages)

                    result = self.orchestrator.initiate_chat(
                        self.manager,
                        message=user_input,
                        clear_history=(attempt == 0) , # Clear history only on first attempt

                    )
                    response = []
                    final_response = result.chat_history if result.chat_history else [
                        {"content": "No response received."}]
                    for entry in final_response:
                        if "content" in entry and entry["content"] is not None:
                            response.append(entry["content"])
                    return "\n".join(response)
                except BadRequestError as e:
                    if "tool_calls" in str(e) and attempt < max_attempts - 1:
                        print(f"Attempt {attempt + 1} failed with tool_calls error: {str(e)}. Retrying with sanitized messages...")
                        continue
                    else:
                        return f"Error processing request after {max_attempts} attempts: {str(e)}"
            return "Failed to process request due to persistent errors."

# Run the main function
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("../../.env")
    s=SessionManager()
    s.create_session("tdawood140@gmail.com")
    memory = MemorySettings()
    memory._initialize_memory()
    c=ConversableAgents(memory)
    prompts=[
        "Add an expense of 250 rupees for groceries today.",
        "Change my preferred language to Spanish.",
        "Check if my internet connection is stable and diagnose any issues.",
        "Help me come up with a catchy slogan for my eco-friendly product line.",
        "What will the weather be like in Mangalore tomorrow?",
        "Give me a deep research report on the environmental impact of lithium mining.",
        "Give me a short summary of Isaac Newton from Wikipedia.",
        "Show me the latest news about AI regulations in the EU.",
    ]
    #for prompt in prompts:
    #    print(c.initiate_chat(prompt))
    print(c.initiate_chat("what is the weather in mangalore?"))