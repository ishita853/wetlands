import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.dataset import DatasetFormat, DatasetKind, DatasetStatus


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    kind: DatasetKind
    theme: str | None = None
    format: DatasetFormat
    status: DatasetStatus
    original_filename: str
    size_bytes: int
    sha256: str
    validation_errors: list[str] | None = None
    summary: dict[str, Any] | None = None
    published_at: datetime | None = None
    created_at: datetime
    uploaded_by_username: str | None = None


class ClimateThemeStatus(BaseModel):
    theme: str
    title: str
    published: DatasetRead | None = None
