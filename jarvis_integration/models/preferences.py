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
from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from jarvis_integration.internals.db import Base, get_db, JSONField
from jarvis_integration.internals.register import define_table
from typing import Union
####################
# Preference DB Schema
####################

@define_table("Preference")
class Preference(Base):
    __tablename__ = "preference"

    preference_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    setting_key = Column(String, nullable=False)
    setting_value = Column(JSONField, nullable=True)  # Supports complex settings
    created_at = Column(DateTime, default=datetime.utcnow)

    # Enforce unique setting_key per user
    __table_args__ = (
        UniqueConstraint("user_id", "setting_key", name="uix_user_preference_key"),
        {"mysql_engine": "InnoDB"},
    )

    # Relationship to User
    user = relationship("User", back_populates="preferences")

####################
# Pydantic Model
####################

class PreferenceModel(BaseModel):
    preference_id: str
    user_id: str
    setting_key: str
    setting_value: Union[dict,Optional[list]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

####################
# Preference Table Operations
####################

class PreferenceTable:
    def insert_new_preference(
        self,
        preference_id: str,
        user_id: str,
        setting_key: str,
        setting_value: Optional[dict] = None
    ) -> Optional[PreferenceModel]:
        """Insert a new preference for a user."""
        try:
            with get_db() as db:
                preference = Preference(
                    preference_id=preference_id,
                    user_id=user_id,
                    setting_key=setting_key,
                    setting_value=setting_value,
                    created_at=datetime.utcnow()
                )
                db.add(preference)
                db.commit()
                db.refresh(preference)
                return PreferenceModel.model_validate(preference)
        except Exception as e:
            print(f"Error inserting preference: {e}")
            return None

    def get_preference_by_id(self, preference_id: str) -> Optional[PreferenceModel]:
        """Retrieve a preference by its ID."""
        try:
            with get_db() as db:
                preference = db.query(Preference).filter_by(preference_id=preference_id).first()
                return PreferenceModel.model_validate(preference) if preference else None
        except Exception as e:
            print(f"Error retrieving preference by ID: {e}")
            return None

    def get_preferences_by_user_id(self, user_id: str, skip: int = 0, limit: int = 50) -> List[PreferenceModel]:
        """Retrieve all preferences for a user."""
        try:
            with get_db() as db:
                preferences = (
                    db.query(Preference)
                    .filter_by(user_id=user_id)
                    .offset(skip)
                    .limit(limit)
                    .all()
                )
                return [PreferenceModel.model_validate(pref) for pref in preferences]
        except Exception as e:
            print(f"Error retrieving preferences by user ID: {e}")
            return []

    def get_num_preferences(self, user_id: Optional[str] = None) -> int:
        """Count preferences, optionally filtered by user_id."""
        try:
            with get_db() as db:
                query = db.query(Preference)
                if user_id:
                    query = query.filter_by(user_id=user_id)
                return query.count()
        except Exception as e:
            print(f"Error counting preferences: {e}")
            return 0

    def get_first_preference(self, user_id: Optional[str] = None) -> Optional[PreferenceModel]:
        """Retrieve the first preference, optionally filtered by user_id."""
        try:
            with get_db() as db:
                query = db.query(Preference)
                if user_id:
                    query = query.filter_by(user_id=user_id)
                preference = query.order_by(Preference.created_at).first()
                return PreferenceModel.model_validate(preference) if preference else None
        except Exception as e:
            print(f"Error retrieving first preference: {e}")
            return None

    def update_preference_by_id(self, preference_id: str, updated: dict) -> Optional[PreferenceModel]:
        """Update a preference by its ID."""
        try:
            with get_db() as db:
                preference = db.query(Preference).filter_by(preference_id=preference_id).first()
                if not preference:
                    return None
                for key, value in updated.items():
                    setattr(preference, key, value)
                db.commit()
                db.refresh(preference)
                return PreferenceModel.model_validate(preference)
        except Exception as e:
            print(f"Error updating preference: {e}")
            return None

    def delete_preference_by_id(self, preference_id: str) -> bool:
        """Delete a preference by its ID."""
        try:
            with get_db() as db:
                result = db.query(Preference).filter_by(preference_id=preference_id).delete()
                db.commit()
                return result > 0
        except Exception as e:
            print(f"Error deleting preference: {e}")
            return False

    def delete_preferences_by_user_id(self, user_id: str) -> bool:
        """Delete all preferences for a user."""
        try:
            with get_db() as db:
                result = db.query(Preference).filter_by(user_id=user_id).delete()
                db.commit()
                return result > 0
        except Exception as e:
            print(f"Error deleting preferences by user ID: {e}")
            return False

Preferences = PreferenceTable()
