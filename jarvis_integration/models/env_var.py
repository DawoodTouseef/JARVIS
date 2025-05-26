from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from jarvis_integration.internals.db import Base
from jarvis_integration.internals.register import define_table
import logging

# Configure logging
logger = logging.getLogger(__name__)

####################
# EnvVars DB Schema
####################

@define_table("EnvVars")
class EnvVars(Base):
    __tablename__ = "env_vars"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=True)
    value: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="env_vars")