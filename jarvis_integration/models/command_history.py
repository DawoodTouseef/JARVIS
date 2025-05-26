# jarvis_integration/models/command_history.py
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from jarvis_integration.internals.db import Base
from jarvis_integration.internals.register import define_table
from datetime import datetime
import uuid

@define_table("CommandHistory")
class CommandHistory(Base):
    __tablename__ = "command_history"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"))
    command: Mapped[str] = mapped_column(String, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped["User"] = relationship("User")