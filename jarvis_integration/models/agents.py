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
from jarvis_integration.internals.db import Base,get_db,JSONField
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text,ForeignKey
from typing import Optional
import time
from sqlalchemy.inspection import inspect
from jarvis_integration.internals.register import define_table
####################
# Agents DB Schema
####################

@define_table("Agents")
class Agents(Base):
    __tablename__="Agents"

    id = Column(String, primary_key=True)
    user_id = ForeignKey("user.id")
    name = Column(String)
    description = Column(Text)
    file=Column(JSONField)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    settings = Column(JSONField, nullable=True)


class AgentsSettings(BaseModel):

    model_config = ConfigDict(extra="allow")
    pass


class AgentModel(BaseModel):
    id:str
    name:str
    description:str
    file:dict

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    settings: Optional[AgentsSettings] = None




class AgentsTable:
    def insert_new_agent(
            self,
            id:str,
            name:str,
            description:str,
            file:dict,
        )->Optional[AgentModel]:
        with get_db() as db:
            agent = AgentModel(
                **{
                    "id": id,
                    "name": name,
                    "description":description,
                    "file":file,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = Agents(**agent.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return agent
            else:
                return None

    def to_dict(self,agent):
        return {c.key: getattr(agent, c.key) for c in inspect(agent).mapper.column_attrs}

    def get_agent_by_id(self, id: str) -> Optional[AgentModel]:
        try:
            with get_db() as db:
                agent = db.query(Agents).filter_by(id=id).first()
            return AgentModel.model_validate(self.to_dict(agent))
        except Exception:
            return None

    def get_agents(self, skip: int = 0, limit: int = 50) -> list[AgentModel]:
        with get_db() as db:
            tools = (
                db.query(Agents)
                # .offset(skip).limit(limit)
                .all()
            )

            return [AgentModel.model_validate(self.to_dict(tool)) for tool in tools]

    def get_num_agents(self) -> Optional[int]:
        with get_db() as db:
            return db.query(Agents).count()

    def update_agents_file_by_id(self, id: str, func: str) -> Optional[AgentModel]:
        try:
            with get_db() as db:
                db.query(Agents).filter_by(id=id).update({"file": func})
                db.commit()
                user = db.query(Agents).filter_by(id=id).first()
                return AgentModel.model_validate(user)
        except Exception:
            return None
    def update_agent_by_id(self, id: str, updated: dict) -> Optional[AgentModel]:
        try:
            with get_db() as db:
                db.query(Agents).filter_by(id=id).update(updated)
                db.commit()

                tool = db.query(Agents).filter_by(id=id).first()
                return AgentModel.model_validate(tool)
                # return UserModel(**user.dict())
        except Exception:
            return None
    def delete_agent_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                # Delete User
                db.query(Agents).filter_by(id=id).delete()
                db.commit()
            return True
        except Exception:
            return False

Agent=AgentsTable()