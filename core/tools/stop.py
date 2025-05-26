from core.tools.standard_tools import *
from config import stop_event




class StopTool(BaseTool):
    name: str = "Stop Assistant"
    description: str = "Stops the current conversation or action."
    def _run(self) -> str:
        stop_event.set()
        return "Conversation stopped. You may start a new request."