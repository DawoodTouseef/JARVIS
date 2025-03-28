from utils.internals.db import Base,get_db,JSONField
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text
from typing import Optional
import time

####################
# User DB Schema
####################

class User(Base):
    __tablename__ = "user"
    id=Column(String,primary_key=True)
    name=Column(String)
    role=Column(String)
    email=Column(String)
    dob=Column(String,nullable=True)
    user_face = Column(Text,nullable=True)
    user_voice =Column(Text,nullable=True)
    password=Column(String)
    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    settings = Column(JSONField, nullable=True)


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="allow")
    pass

class UserModel(BaseModel):
    id: str
    name: str
    email: str
    dob:str
    role: str = "user"
    user_face: str=None
    user_voice:str=None

    password:str
    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


    settings: Optional[UserSettings] = None


    model_config = ConfigDict(from_attributes=True)


class UserTable:
    def insert_new_user(
        self,
        id: str,
        name: str,
        email: str,
        profile_image_url: str = "/user.png",
        role: str = "user",
        user_voice:str="./user_voice.mp3",
        password:str=None,
        dob:str=None,
    ) -> Optional[UserModel]:
        with get_db() as db:
            user = UserModel(
                **{
                    "id": id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "user_face": profile_image_url,
                    "user_voice":user_voice,
                    "last_active_at": int(time.time()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "password":password,
                    "dob":dob,
                }
            )
            result = User(**user.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return user
            else:
                return None
    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
            return UserModel.model_validate(user)
        except Exception:
            return None
    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(email=email).first()
                return UserModel.model_validate(user)
        except Exception:
            return None


    def get_users(self, skip: int = 0, limit: int = 50) -> list[UserModel]:
        with get_db() as db:
            users = (
                db.query(User)
                # .offset(skip).limit(limit)
                .all()
            )
            return [UserModel.model_validate(user) for user in users]

    def get_num_users(self) -> Optional[int]:
        with get_db() as db:
            return db.query(User).count()

    def get_first_user(self) -> UserModel:
        try:
            with get_db() as db:
                user = db.query(User).order_by(User.created_at).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_role_by_id(self, id: str, role: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"role": role})
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None


    def update_user_last_active_by_id(self, id: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(
                    {"last_active_at": int(time.time())}
                )
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None


    def update_user_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(updated)
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
                # return UserModel(**user.dict())
        except Exception:
            return None

    def delete_user_by_id(self, id: str=None) -> bool:
        try:
            with get_db() as db:
                # Delete User
                db.query(User).filter_by(id=id).delete()
                db.commit()

            return True
        except Exception:
            return False


Users = UserTable()
