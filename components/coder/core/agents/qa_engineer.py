from __future__ import annotations

from components.coder.core.agents.agent import Agent, AgentRole
from components.coder.core.storage import Storages


class QAEngineer(Agent):
    def __init__(
        self,
        storages: Storages,
        debug_mode: bool = False,
        name: str | None = None,
        profile: str | None = None,
    ) -> None:
        super().__init__(AgentRole.QA_ENGINEER, storages, debug_mode, name, profile)
