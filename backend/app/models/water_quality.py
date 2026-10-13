import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WaterQualityObservation(Base, TimestampMixin):
    """Placeholder model for a water-quality parameter observation tied to
    a wetland. Fields will be extended in a future step, including
    integration with the existing Earth Engine water-quality application.
    """

    __tablename__ = "water_quality_observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    wetland_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("wetlands.id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parameter: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
