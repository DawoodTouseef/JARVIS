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
from sqlalchemy import BigInteger, Column, String, Text
from typing import Optional
import time
from jarvis_integration.internals.register import define_table

####################
# Tools DB Schema
####################
@define_table("Tool")
class Tool(Base):
    __tablename__="Tools"
    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(Text)
    func=Column(Text)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    settings = Column(JSONField, nullable=True)

class ToolSettings(BaseModel):

    model_config = ConfigDict(extra="allow")
    pass

class ToolModel(BaseModel):
    id:int
    name:str
    description:str
    func:str

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    settings: Optional[ToolSettings] = None



class ToolTable:
    def insert_new_tool(self,
        id: str,
        name: str,
        description: str,
        setting:dict=None,
        func:str=None
    ) -> Optional[ToolModel]:
        with get_db() as db:
            settings=ToolSettings(**setting)
            tool = ToolModel(
                **{
                    "id": id,
                    "name": name,
                    "description":description,
                    "func":func,
                    "last_active_at": int(time.time()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "settings":settings,
                }
            )
            result = Tool(**tool.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return tool
            else:
                return None
    def get_tool_by_id(self, id: str) -> Optional[ToolModel]:
        try:
            with get_db() as db:
                user = db.query(Tool).filter_by(id=id).first()
            return ToolModel.model_validate(user)
        except Exception:
            return None
    def get_tools(self, skip: int = 0, limit: int = 50) -> list[ToolModel]:
        with get_db() as db:
            tools = (
                db.query(Tool)
                # .offset(skip).limit(limit)
                .all()
            )
            return [ToolModel.model_validate(tool) for tool in tools]
    def get_num_tools(self) -> Optional[int]:
        with get_db() as db:
            return db.query(Tool).count()
    def update_tool_func_by_id(self, id: str, func: str) -> Optional[ToolModel]:
        try:
            with get_db() as db:
                db.query(Tool).filter_by(id=id).update({"func": func})
                db.commit()
                user = db.query(Tool).filter_by(id=id).first()
                return ToolModel.model_validate(user)
        except Exception:
            return None
    def update_tool_last_update_by_id(self, id: str) -> Optional[ToolModel]:
        try:
            with get_db() as db:
                db.query(Tool).filter_by(id=id).update(
                    {"last_active_at": int(time.time())}
                )
                db.commit()

                user = db.query(Tool).filter_by(id=id).first()
                return ToolModel.model_validate(user)
        except Exception:
            return None
    def update_tool_by_id(self, id: str, updated: dict) -> Optional[ToolModel]:
        try:
            with get_db() as db:
                db.query(Tool).filter_by(id=id).update(updated)
                db.commit()

                tool = db.query(Tool).filter_by(id=id).first()
                return ToolModel.model_validate(tool)
                # return UserModel(**user.dict())
        except Exception:
            return None
    def delete_tool_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                # Delete User
                db.query(Tool).filter_by(id=id).delete()
                db.commit()

            return True
        except Exception:
            return False


Tools=ToolTable()