from __future__ import annotations

from components.gpt_all_star.core.agents.agent import Agent, AgentRole
from components.gpt_all_star.core.storage import Storages


class ProductOwner(Agent):
    def __init__(
        self,
        storages: Storages,
        debug_mode: bool = False,
        name: str | None = None,
        profile: str | None = None,
    ) -> None:
        super().__init__(AgentRole.PRODUCT_OWNER, storages, debug_mode, name, profile)
