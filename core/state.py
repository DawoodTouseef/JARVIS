from typing import  List, Dict

from typing_extensions import TypedDict


from langgraph.graph.message import AnyMessage




class AgentState(TypedDict):
    messages: List[AnyMessage]
    input: str
    final_response: str
    route: str
    image: List[str]
    sensor_data: Dict[str, str]
    audio: str  # Added for audio input
    context: str  # Added for LanceDB context