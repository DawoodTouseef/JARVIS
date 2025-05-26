from jarvis_integration.internals.db import Base, JSONField
from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from jarvis_integration.internals.register import define_table
import uuid
from datetime import datetime
from jarvis_integration.internals.db import get_db

@define_table("SensorReading")
class SensorReading(Base):
    __tablename__ = "sensor_reading"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONField, nullable=True, default=dict)

    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="readings")


@define_table("Sensor")
class Sensor(Base):
    __tablename__ = "sensor"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)  # e.g. sensor.temp_living_room
    device_class: Mapped[Optional[str]] = mapped_column(String, nullable=True)   # e.g. temperature, humidity
    state_class: Mapped[Optional[str]] = mapped_column(String, nullable=True)    # e.g. measurement, total_increasing
    unit_of_measurement: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g. °C, %
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONField, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to sensor readings
    readings: Mapped[List["SensorReading"]] = relationship(
        "SensorReading",
        back_populates="sensor",
        cascade="all, delete-orphan"
    )


class SensorModel(BaseModel):
    id: str
    name: str
    entity_id: str
    device_class: Optional[str]
    state_class: Optional[str]
    unit_of_measurement: Optional[str]
    location: Optional[str]
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SensorReadingModel(BaseModel):
    id: int
    sensor_id: str
    timestamp: datetime
    value: float
    metadata: Optional[dict]

    model_config = ConfigDict(from_attributes=True)


class SensorTable:
    def insert_new_sensor(
        self,
        name: str,
        entity_id: str,
        device_class: Optional[str] = None,
        state_class: Optional[str] = None,
        unit_of_measurement: Optional[str] = None,
        location: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Optional[SensorModel]:
        """Insert a new sensor into the database."""
        try:
            with get_db() as db:
                sensor = Sensor(
                    name=name,
                    entity_id=entity_id,
                    device_class=device_class,
                    state_class=state_class,
                    unit_of_measurement=unit_of_measurement,
                    location=location,
                    metadata=metadata or {},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(sensor)
                db.commit()
                db.refresh(sensor)
                return SensorModel.model_validate(sensor)
        except Exception as e:
            print(f"Error inserting sensor: {e}")
            return None

    def get_sensor_by_id(self, id: str) -> Optional[SensorModel]:
        try:
            with get_db() as db:
                sensor = db.query(Sensor).filter_by(id=id).first()
                return SensorModel.model_validate(sensor) if sensor else None
        except Exception as e:
            print(f"Error getting sensor by ID: {e}")
            return None

    def get_sensor_by_entity_id(self, entity_id: str) -> Optional[SensorModel]:
        try:
            with get_db() as db:
                sensor = db.query(Sensor).filter_by(entity_id=entity_id).first()
                return SensorModel.model_validate(sensor) if sensor else None
        except Exception as e:
            print(f"Error getting sensor by entity_id: {e}")
            return None

    def insert_reading_for_sensor(
        self,
        sensor_id: str,
        value: float,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None
    ) -> Optional[SensorReadingModel]:
        try:
            with get_db() as db:
                reading = SensorReading(
                    sensor_id=sensor_id,
                    value=value,
                    timestamp=timestamp or datetime.utcnow(),
                    metadata=metadata or {}
                )
                db.add(reading)
                db.commit()
                db.refresh(reading)
                return SensorReadingModel.model_validate(reading)
        except Exception as e:
            print(f"Error inserting sensor reading: {e}")
            return None

    def get_latest_reading_for_sensor(self, sensor_id: str) -> Optional[SensorReadingModel]:
        try:
            with get_db() as db:
                reading = (
                    db.query(SensorReading)
                    .filter_by(sensor_id=sensor_id)
                    .order_by(SensorReading.timestamp.desc())
                    .first()
                )
                return SensorReadingModel.model_validate(reading) if reading else None
        except Exception as e:
            print(f"Error getting latest reading: {e}")
            return None

    def get_sensor_readings(self, sensor_id: str, skip: int = 0, limit: int = 100) -> List[SensorReadingModel]:
        try:
            with get_db() as db:
                readings = (
                    db.query(SensorReading)
                    .filter_by(sensor_id=sensor_id)
                    .order_by(SensorReading.timestamp.desc())
                    .offset(skip)
                    .limit(limit)
                    .all()
                )
                return [SensorReadingModel.model_validate(r) for r in readings]
        except Exception as e:
            print(f"Error getting sensor readings: {e}")
            return []

    def delete_sensor_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Sensor).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception as e:
            print(f"Error deleting sensor: {e}")
            return False

Sensors = SensorTable()
