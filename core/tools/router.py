from core.tools.standard_tools import *
from langchain_community.tools import YouTubeSearchTool

from langchain_community.tools import ShellTool
from crewai.tools.base_tool import BaseTool as CrewAIBaseTool, Tool as CrewAITool
from typing import  List
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langchain_community.tools.ddg_search.tool import DuckDuckGoSearchRun
from core.tools.calculator import CalculatorTool
from core.tools.stop import StopTool
from core.tools.winget import create_winget_tools
from core.tools.sensors import create_sensor_tools
from core.tools.scheduler import create_schedule_tools
from core.tools.consciousness import create_consciousness_tools

class ToolRouter:
    def __init__(self):
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
            DuckDuckGoSearchRun(),
        ] +
        create_schedule_tools() +
        create_winget_tools() +
        create_sensor_tools() +
        create_consciousness_tools()
            )
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

if __name__=='__main__':
    t=ToolRouter()
    for i in t.get_crewai_tools():
        print(i.name)