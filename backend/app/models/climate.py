import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ClimateIndicatorType(StrEnum):
    DROUGHT = "DROUGHT"
    PRECIPITATION = "PRECIPITATION"
    HEAT_WAVE = "HEAT_WAVE"
    COLD_WAVE = "COLD_WAVE"


class ClimateObservation(Base, TimestampMixin):
    """Placeholder model for a climate indicator observation tied to a
    wetland. Fields will be extended in a future step.
    """

    __tablename__ = "climate_observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    wetland_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("wetlands.id"), nullable=False)
    indicator_type: Mapped[ClimateIndicatorType] = mapped_column(
        Enum(ClimateIndicatorType, name="climate_indicator_type"), nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
