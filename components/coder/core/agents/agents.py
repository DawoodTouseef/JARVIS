from dataclasses import dataclass

from components.coder.core.agents.agent import Agent
from components.coder.core.agents.architect import Architect
from components.coder.core.agents.designer import Designer
from components.coder.core.agents.engineer import Engineer
from components.coder.core.agents.product_owner import ProductOwner
from components.coder.core.agents.project_manager import ProjectManager
from components.coder.core.agents.qa_engineer import QAEngineer


@dataclass
class Agents:
    product_owner: ProductOwner
    engineer: Engineer
    architect: Architect
    designer: Designer
    qa_engineer: QAEngineer
    project_manager: ProjectManager

    def to_array(self) -> list[Agent]:
        return list(vars(self).values())

    def get_agent_by_role(self, role: str):
        for attribute in self.__dict__.values():
            if hasattr(attribute, "role") and attribute.role.name == role:
                return attribute
        return self.project_manager

    def set_executors(self, working_directory: str):
        for agent in self.to_array():
            agent.set_executor(working_directory)
