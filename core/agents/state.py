from typing import  List, Dict

from typing_extensions import TypedDict


from langgraph.graph.message import AnyMessage
from typing import Union



class AgentState(TypedDict):
    messages: List[AnyMessage]
    input: Union[str,list]
    final_response: str
    route: str
    image: List[str]
    sensor_data: Dict[str, str]
    audio: str  # Added for audio input
    context: str  # Added for LanceDB context