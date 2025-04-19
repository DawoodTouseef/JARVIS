from __future__ import annotations

from coder.core.agents.agent import Agent, AgentRole
from coder.core.storage import Storages


class Engineer(Agent):
    def __init__(
        self,
        storages: Storages,
        debug_mode: bool = False,
        name: str | None = None,
        profile: str | None = None,
    ) -> None:
        super().__init__(AgentRole.ENGINEER, storages, debug_mode, name, profile)
