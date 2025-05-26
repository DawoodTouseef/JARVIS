# jarvis_integration/models/alias.py
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from jarvis_integration.internals.db import Base
from jarvis_integration.internals.register import define_table
import uuid

@define_table("Alias")
class Alias(Base):
    __tablename__ = "aliases"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"))
    alias: Mapped[str] = mapped_column(String, nullable=False)
    command: Mapped[str] = mapped_column(String, nullable=False)
    user: Mapped["User"] = relationship("User")