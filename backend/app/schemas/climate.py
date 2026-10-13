import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.climate import ClimateIndicatorType


class ClimateObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    wetland_id: uuid.UUID
    indicator_type: ClimateIndicatorType
    observed_at: datetime
    value: float
    unit: str
    source: str
