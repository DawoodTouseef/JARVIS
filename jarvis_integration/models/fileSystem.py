import uuid
from sqlalchemy import Boolean,String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from jarvis_integration.internals.db import Base
from jarvis_integration.internals.register import define_table
from typing import  Optional

@define_table("filesystem")
class FileSystem(Base):
    __tablename__ = "filesystem"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("user.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("filesystem.id"), nullable=True)
    is_dir: Mapped[bool] = mapped_column(Boolean, nullable=False)
    real_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    parent: Mapped[Optional["FileSystem"]] = relationship("FileSystem", remote_side=[id])
    user: Mapped[Optional["User"]] = relationship("User", back_populates="files")