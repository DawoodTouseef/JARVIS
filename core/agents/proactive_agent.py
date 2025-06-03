import os
import json
import asyncio
import aiohttp
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from autogen import AssistantAgent, UserProxyAgent,LLMConfig
from mem0 import MemoryClient
from core.tools.home_assistant_tool import HomeAssistant
import re
from config import JARVIS_DIR
from core.Agent_models import get_model_from_database
from jarvis_integration.models.users import Users
from jarvis_integration.models.preferences import Preferences
from core.memory.memory_agent import MemorySettings

home_assistant=HomeAssistant()
home_assistant.load_ha()


MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
memory_client=MemorySettings()
memory_client._initialize_memory()

model=get_model_from_database()
llm_config = LLMConfig(api_type="openai", model=model.name, api_key=model.api_key, base_url=model.url)

# Google Calendar setup
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
def get_calendar_service():
    creds = None
    toke_file=os.path.join(JARVIS_DIR, "data", "token.json")
    GOOGLE_CREDENTIALS_FILE=os.path.join(JARVIS_DIR, "data", "credentials.json")
    if os.path.exists(toke_file):
        creds = Credentials.from_authorized_user_file(toke_file, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(toke_file, "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

async def get_weather(location):
        from langchain_community.tools.openweathermap import OpenWeatherMapQueryRun
        from langchain_community.utilities.openweathermap import OpenWeatherMapAPIWrapper
        prefs=Preferences
        session=""
        user_id = Users.get_user_by_email(session.get_email()).id
        news = prefs.get_preferences_by_user_id(user_id, skip=0, limit=50)
        filtered_news = next((exp for exp in news if exp.setting_key == "openweather"), None)
        openweather = os.getenv("OPENWEATHER_API_KEY") or filtered_news.setting_value.get("api_key") or None
        if openweather is not None:
            weather=OpenWeatherMapQueryRun(
                api_wrapper=OpenWeatherMapAPIWrapper(openweathermap_api_key=openweather
                                                     ))
            return weather._run(location=location)


# MQTT for Frigate
def on_connect(client, userdata, flags, rc):
    client.subscribe("frigate/events")

def on_message(client, userdata, msg):
    event = json.loads(msg.payload.decode())
    if event["type"] == "new" and event["event"]["label"] == "person":
        user_proxy.send(recipient=main_agent, message="Proactive Alert: Person detected at the door!")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# AutoGen Agents
main_agent = AssistantAgent(
    name="JARVIS",
    system_message="You are JARVIS, a proactive AI assistant inspired by Iron Man. Coordinate with other agents to anticipate user needs, manage smart home devices via Home Assistant, check weather, monitor calendar, and provide security alerts from Frigate. Use memory to personalize responses.",
    llm_config=llm_config,
    human_input_mode="NEVER",
)

command_parser_agent = AssistantAgent(
    name="CommandParserAgent",
    system_message="Parse user commands and generate structured JSON responses. Supported actions: 'turn_on', 'turn_off', 'check_schedule', 'check_weather', 'run_script'. For 'turn_on'/'turn_off', include 'entity' (e.g., 'light.bedroom_light'). For 'check_weather', include 'city' if specified. For 'run_script', include 'script' (e.g., 'good_morning'). Example: {'action': 'turn_on', 'entity': 'light.bedroom_light'}",
    llm_config=llm_config,
    code_execution_config=False,
)

weather_agent = AssistantAgent(
    name="WeatherAgent",
    system_message="Fetch and analyze weather data from OpenWeatherMap to provide proactive suggestions. Use user-preferred city from memory.",
    llm_config=llm_config,
    code_execution_config=False,
)

calendar_agent = AssistantAgent(
    name="CalendarAgent",
    system_message="Manage Google Calendar events and provide reminders.",
    llm_config=llm_config,
    code_execution_config=False,
)

home_agent = AssistantAgent(
    name="HomeAgent",
    system_message="Control Home Assistant devices and scripts based on commands received. Use 'hass.turn_on(entity)', 'hass.turn_off(entity)', or 'hass.run_script(script)' to execute actions.",
    llm_config=llm_config,
    code_execution_config={"work_dir": ".", "use_docker": False},
)

user_proxy = UserProxyAgent(
    name="UserProxy",
    human_input_mode="ALWAYS",
    code_execution_config=False,
)

async def check_weather_proactively():
    memories = memory_client.search_memory("preferred city for weather")
    city = memories[0]["memory"].get("city", "London") if memories else "London"
    weather = await get_weather(city)
    if weather.get("weather", [{}])[0].get("main") == "Rain":
        return f"It’s going to rain in {city} soon. Would you like me to remind you to take an umbrella?"
    return None

async def check_calendar_proactively():
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + "Z"
    tomorrow = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    events_result = service.events().list(
        calendarId="primary", timeMin=now, timeMax=tomorrow, singleEvents=True, orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])
    if events:
        event = events[0]
        start = event["start"].get("dateTime", event["start"].get("date"))
        return f"Reminder: You have '{event['summary']}' at {start}."
    return None

async def check_home_state_proactively():
    memories = memory_client.search_memory("morning routine time")
    routine_hour = int(memories[0]["memory"].get("hour", 7)) if memories else 7
    current_hour = datetime.now().hour
    if current_hour == routine_hour:
        user_proxy.initiate_chat(
            recipient=home_agent,
            message=json.dumps({"action": "run_script", "script": "good_morning"})
        )
        return "Good morning! I’ve started your morning routine."
    return None

async def proactive_loop():
    while True:
        # Check weather
        weather_message = await check_weather_proactively()
        if weather_message:
            user_proxy.send(recipient=main_agent, message=weather_message)

        # Check calendar
        calendar_message = await check_calendar_proactively()
        if calendar_message:
            user_proxy.send(recipient=main_agent, message=calendar_message)

        # Check home state
        home_message = await check_home_state_proactively()
        if home_message:
            user_proxy.send(recipient=main_agent, message=home_message)

        await asyncio.sleep(60)  # Check every 60 seconds
