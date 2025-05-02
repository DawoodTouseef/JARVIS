from core.tools.standard_tools import *
from langchain_community.tools import YouTubeSearchTool

from langchain_google_community import GmailToolkit
#from langchain_community.agent_toolkits import O365Toolkit
from langchain_community.tools import ShellTool
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from langchain_community.tools.openweathermap.tool import OpenWeatherMapQueryRun
from crewai.tools.base_tool import BaseTool as CrewAIBaseTool, Tool as CrewAITool
from langchain_google_community.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
from typing import  List
from config import JARVIS_DIR
import os
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from core.tools.calculator import CalculatorTool
from core.tools.stop import StopTool
from core.tools.winget import create_winget_tools
from core.tools.sensors import create_sensor_tools
from core.tools.scheduler import create_schedule_tools
from core.tools.consciousness import create_consciousness_tools

class ToolRouter:
    def __init__(self):
        credentials = get_gmail_credentials(
            token_file=os.path.join(JARVIS_DIR,"data","token.json"),
            scopes=["https://mail.google.com/"],
            client_secrets_file=os.path.join(JARVIS_DIR,"data","credentials.json"),
        )
        api_resource = build_resource_service(credentials=credentials)
        gmail_toolkit = GmailToolkit(api_resource=api_resource)
        self.tools = ([
            CalculatorTool(),
            mouse_scroll,
            move_on_a_icon_on_the_screen,
            click_on_a_icon_on_the_screen,
            move_on_a_text_on_the_screen,
            click_on_a_text_on_the_screen,
            StopTool(),
            ShellTool(),
            YouTubeSearchTool(),
            YahooFinanceNewsTool(),
        ] +
        the_standard_tools +
        create_schedule_tools() +
        create_winget_tools() +
        create_sensor_tools() +
        create_consciousness_tools()+
        gmail_toolkit.get_tools()
            )
        if os.getenv("OPENWEATHER_API_KEY",None) is not None:
            self.tools+[OpenWeatherMapQueryRun(api_wrapper=OpenWeatherMapAPIWrapper(openweathermap_api_key=os.getenv("OPENWEATHER_API_KEY"))),]
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
