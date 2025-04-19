
from pydantic import Field,BaseModel
from typing_extensions import Type

from langchain.tools import BaseTool




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