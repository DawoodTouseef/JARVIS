# Copyright 2025 Dawood Thouseef
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from jarvis_integration.internals.db import Base, get_db, JSONField
from pydantic import BaseModel, ConfigDict
from sqlalchemy import  String, DateTime
from typing import Optional, List
from jarvis_integration.internals.register import define_table
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime

####################
# User DB Schema
####################

@define_table("User")
class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    dob: Mapped[str] = mapped_column(String, nullable=True)
    profile_image_url: Mapped[str] = mapped_column(String, nullable=True)
    user_voice: Mapped[str] = mapped_column(String, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONField, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Define relationship to Preference
    preferences: Mapped[List["Preference"]] = relationship(
        "Preference",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    files: Mapped[List["FileSystem"]] = relationship(
        "FileSystem",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Optional: Uncomment for user-specific env_vars
    env_vars: Mapped[List["EnvVars"]] = relationship(
        "EnvVars",
        back_populates="user",
        cascade="all, delete-orphan"
    )
####################
# Pydantic Models
####################

class UserSettings(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

class UserModel(BaseModel):
    id: str
    name: str
    email: str
    password: str
    role: str
    dob: Optional[str] = None
    profile_image_url: Optional[str] = None
    user_voice: Optional[str] = None
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime

    model_config = ConfigDict(from_attributes=True)

####################
# User Table Operations
####################

class UserTable:
    def insert_new_user(
        self,
        id: str,
        name: str,
        email: str,
        password: str,
        role: str = "user",
        dob: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        user_voice: Optional[str] = None,
    ) -> Optional[UserModel]:
        """Insert a new user into the database."""
        try:
            with get_db() as db:
                user = User(
                    id=id,
                    name=name,
                    email=email,
                    password=password,
                    role=role,
                    dob=dob,
                    profile_image_url=profile_image_url,
                    user_voice=user_voice,
                    settings={},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    last_active_at=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return UserModel.model_validate(user)
        except Exception as e:
            print(f"Error inserting user: {e}")
            return None

    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        """Retrieve a user by their ID."""
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            print(f"Error retrieving user by ID: {e}")
            return None
    def get_user_by_name(self, name: str) -> Optional[UserModel]:
        """Retrieve a user by their ID."""
        try:
            with get_db() as db:
                user = db.query(User).filter_by(name=name).first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            print(f"Error retrieving user by ID: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Retrieve a user by their email."""
        try:
            with get_db() as db:
                user = db.query(User).filter_by(email=email).first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            print(f"Error retrieving user by email: {e}")
            return None

    def get_users(self, skip: int = 0, limit: int = 50) -> List[UserModel]:
        """Retrieve a list of users with pagination."""
        try:
            with get_db() as db:
                users = db.query(User).offset(skip).limit(limit).all()
                return [UserModel.model_validate(user) for user in users]
        except Exception as e:
            print(f"Error retrieving users: {e}")
            return []

    def get_num_users(self) -> int:
        """Count the total number of users."""
        try:
            with get_db() as db:
                return db.query(User).count()
        except Exception as e:
            print(f"Error counting users: {e}")
            return 0

    def get_first_user(self) -> Optional[UserModel]:
        """Retrieve the first user by creation date."""
        try:
            with get_db() as db:
                user = db.query(User).order_by(User.created_at).first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            print(f"Error retrieving first user: {e}")
            return None

    def update_user_role_by_id(self, id: str, role: str) -> Optional[UserModel]:
        """Update a user's role by their ID."""
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"role": role, "updated_at": datetime.utcnow()})
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            print(f"Error updating user role: {e}")
            return None

    def update_user_last_active_by_id(self, id: str) -> Optional[UserModel]:
        """Update a user's last active timestamp by their ID."""
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"last_active_at": datetime.utcnow()})
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            print(f"Error updating last active: {e}")
            return None

    def update_user_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        """Update a user's fields by their ID."""
        try:
            updated = updated.copy()
            updated["updated_at"] = datetime.utcnow()
            with get_db() as db:
                db.query(User).filter_by(id=id).update(updated)
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            print(f"Error updating user: {e}")
            return None

    def delete_user_by_id(self, id: str) -> bool:
        """Delete a user by their ID."""
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

Users = UserTable()