from pydantic import  Field,BaseModel
from langchain_community.tools import GmailSearch
from langchain_community.tools import GmailGetMessage
from langchain_community.tools import GmailSendMessage
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import (
    create_async_playwright_browser
)
from standard_tools import *
from config import ALLOW_DANGEROUS_REQUEST
from langchain_community.agent_toolkits.openapi.toolkit import RequestsToolkit
from langchain_community.utilities.requests import TextRequestsWrapper
from langchain_community.tools import HumanInputRun
from langchain_community.tools import YouTubeSearchTool
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langchain_community.utilities import StackExchangeAPIWrapper
from langchain_community.tools import StackExchangeTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from config import stop_event




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
    """Stop ongoing conversation or task."""
    stop_event.set()
    return "Conversation stopped. You may start a new request."

# Tools (Including Stop Command)
class StopTool(BaseTool):
    name: str = "Stop Assistant"
    description: str = "Stops the current conversation or action."
    def _run(self) -> str:
        return stop_conversation()

# Tool Selection with Dynamic Routing
class ToolRouter:
    def __init__(self):
        async_browser = create_async_playwright_browser()
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
        playwright_tools = toolkit.get_tools()
        toolkit = RequestsToolkit(
            requests_wrapper=TextRequestsWrapper(headers={}),
            allow_dangerous_requests=ALLOW_DANGEROUS_REQUEST,
        )
        requests_tools = toolkit.get_tools()
        self.tools = [
            ArxivQueryRun(),
            CalculatorTool(),
            mouse_scroll,
            move_on_a_icon_on_the_screen,
            click_on_a_icon_on_the_screen,
            move_on_a_text_on_the_screen,
            click_on_a_text_on_the_screen,
            GmailSearch(),
            GmailGetMessage(),
            GmailSendMessage(),
            HumanInputRun(),
            YouTubeSearchTool(),
            YahooFinanceNewsTool(),
            StackExchangeTool(api_wrapper=StackExchangeAPIWrapper()),
            WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(doc_content_chars_max=250)),
            StopTool()
        ] + the_standard_tools + playwright_tools +  requests_tools
        if  load_api_key() is not None:
            self.tools+[search_on_internet,generate_code_with_aim_team]

    def get_tools(self) -> List[BaseTool]:
        return self.tools
