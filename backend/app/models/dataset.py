import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DatasetFormat(StrEnum):
    JSON = "JSON"
    CSV = "CSV"
    GEOJSON = "GEOJSON"
    GEOTIFF = "GEOTIFF"
    NETCDF = "NETCDF"
    SHAPEFILE_ZIP = "SHAPEFILE_ZIP"


class DatasetKind(StrEnum):
    CLIMATE_INDICATOR = "CLIMATE_INDICATOR"


class DatasetStatus(StrEnum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"  # rejected by validation; kept for the audit trail
    VALIDATED = "VALIDATED"  # valid, not currently published
    PUBLISHED = "PUBLISHED"  # the version the portal is serving
    SUPERSEDED = "SUPERSEDED"  # replaced by a newer published version


class Dataset(Base, TimestampMixin):
    """One uploaded dataset file and its validation / publication state."""

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[DatasetKind] = mapped_column(
        Enum(DatasetKind, name="dataset_kind"), default=DatasetKind.CLIMATE_INDICATOR
    )
    # Climate theme key (e.g. "heat-waves") for CLIMATE_INDICATOR datasets.
    theme: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    format: Mapped[DatasetFormat] = mapped_column(
        Enum(DatasetFormat, name="dataset_format"), nullable=False
    )
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status"), default=DatasetStatus.UPLOADED
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Validation messages (list of strings) when status is FAILED.
    validation_errors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # Short description of a valid file: years, metrics, site count, source.
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
