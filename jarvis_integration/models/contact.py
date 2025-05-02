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
from jarvis_integration.internals.db import Base
from sqlalchemy import  Column, String,Integer,Boolean,ForeignKey
from sqlalchemy.orm import relationship
from jarvis_integration.internals.register import define_table

# Database Models
@define_table("Contact")
class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    is_favorite = Column(Boolean, default=False)
    phone_numbers = relationship("PhoneNumber", back_populates="contact", cascade="all, delete-orphan",lazy="joined")


####################
# PhoneNumber DB Schema
####################
@define_table("phone_numbers")
class PhoneNumber(Base):
    __tablename__ = "phone_numbers"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    number = Column(String, nullable=False)
    contact = relationship("Contact", back_populates="phone_numbers",lazy="joined")

@define_table( "twilio_settings")
class TwilioSettings(Base):
    __tablename__ = "twilio_settings"
    id = Column(Integer, primary_key=True)
    account_sid = Column(String, nullable=False)
    auth_token = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)

@define_table("call_history")
class CallHistory(Base):
    __tablename__ = "call_history"
    id = Column(Integer, primary_key=True)
    contact_name = Column(String)
    contact_number = Column(String, nullable=False)
    call_type = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    duration = Column(String, nullable=True)

