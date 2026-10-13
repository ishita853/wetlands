import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import AdminDep, DbSession
from app.core.config import settings
from app.models.dataset import Dataset, DatasetFormat, DatasetKind, DatasetStatus
from app.models.user import User
from app.schemas.dataset import ClimateThemeStatus, DatasetRead
from app.services.datasets.climate import (
    CLIMATE_THEMES,
    publish_climate_file,
    unpublish_climate_file,
    validate_climate_dataset,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_CHUNK = 1024 * 1024


def _read_limited(upload: UploadFile) -> bytes:
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = bytearray()
    while chunk := upload.file.read(_CHUNK):
        data.extend(chunk)
        if len(data) > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"The file is larger than {settings.MAX_UPLOAD_MB} MB.",
            )
    return bytes(data)


def _storage_path(key: str) -> Path:
    return Path(settings.DATA_STORAGE_DIR) / key


def _to_read(dataset: Dataset, usernames: dict[uuid.UUID, str]) -> DatasetRead:
    out = DatasetRead.model_validate(dataset)
    out.uploaded_by_username = usernames.get(dataset.uploaded_by) if dataset.uploaded_by else None
    return out


def _usernames(db: DbSession) -> dict[uuid.UUID, str]:
    return dict(db.execute(select(User.id, User.username)).tuples().all())


def _get_dataset(db: DbSession, dataset_id: uuid.UUID) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    return dataset


def _publish(db: DbSession, dataset: Dataset) -> None:
    raw = _storage_path(dataset.storage_key or "").read_bytes()
    publish_climate_file(raw, dataset.theme or "")
    current = db.scalars(
        select(Dataset).where(
            Dataset.theme == dataset.theme,
            Dataset.status == DatasetStatus.PUBLISHED,
            Dataset.id != dataset.id,
        )
    ).all()
    for previous in current:
        previous.status = DatasetStatus.SUPERSEDED
    dataset.status = DatasetStatus.PUBLISHED
    dataset.published_at = datetime.now(UTC)


@router.get("/datasets", response_model=list[DatasetRead])
def list_datasets(db: DbSession, _: AdminDep) -> list[DatasetRead]:
    datasets = db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    names = _usernames(db)
    return [_to_read(d, names) for d in datasets]


@router.get("/climate-themes", response_model=list[ClimateThemeStatus])
def climate_theme_status(db: DbSession, _: AdminDep) -> list[ClimateThemeStatus]:
    names = _usernames(db)
    out = []
    for key, title in CLIMATE_THEMES.items():
        published = db.scalar(
            select(Dataset).where(Dataset.theme == key, Dataset.status == DatasetStatus.PUBLISHED)
        )
        out.append(
            ClimateThemeStatus(
                theme=key, title=title, published=_to_read(published, names) if published else None
            )
        )
    return out


@router.post("/datasets/climate", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
def upload_climate_dataset(
    db: DbSession,
    user: AdminDep,
    theme: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    publish: Annotated[bool, Form()] = True,
    description: Annotated[str | None, Form(max_length=2000)] = None,
) -> DatasetRead:
    """Validates a climate indicator file, stores it, and (by default) publishes it.

    Invalid files are recorded with status FAILED and their validation errors,
    so the upload history is a complete audit trail.
    """
    if theme not in CLIMATE_THEMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown theme."
        )
    filename = Path(file.filename or "upload.json").name
    if not filename.lower().endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Upload a .json file."
        )

    raw = _read_limited(file)
    result = validate_climate_dataset(raw, theme)

    dataset = Dataset(
        id=uuid.uuid4(),
        name=f"{CLIMATE_THEMES[theme]} — {filename}",
        description=(description or "").strip() or None,
        kind=DatasetKind.CLIMATE_INDICATOR,
        theme=theme,
        format=DatasetFormat.JSON,
        status=DatasetStatus.VALIDATED if result.ok else DatasetStatus.FAILED,
        original_filename=filename,
        size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        validation_errors=None if result.ok else result.errors,
        summary=result.summary,
        uploaded_by=user.id,
    )
    dataset.storage_key = f"datasets/{dataset.id}.json"
    path = _storage_path(dataset.storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)

    db.add(dataset)
    if result.ok and publish:
        _publish(db, dataset)
    db.commit()
    db.refresh(dataset)
    return _to_read(dataset, _usernames(db))


@router.post("/datasets/{dataset_id}/publish", response_model=DatasetRead)
def publish_dataset(dataset_id: uuid.UUID, db: DbSession, _: AdminDep) -> DatasetRead:
    """Publishes a valid upload — also used to roll back to an earlier version."""
    dataset = _get_dataset(db, dataset_id)
    if dataset.status == DatasetStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A file that failed validation cannot be published.",
        )
    _publish(db, dataset)
    db.commit()
    db.refresh(dataset)
    return _to_read(dataset, _usernames(db))


@router.post("/datasets/{dataset_id}/unpublish", response_model=DatasetRead)
def unpublish_dataset(dataset_id: uuid.UUID, db: DbSession, _: AdminDep) -> DatasetRead:
    """Withdraws the published file; the theme page returns to "not loaded"."""
    dataset = _get_dataset(db, dataset_id)
    if dataset.status != DatasetStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This version is not published."
        )
    unpublish_climate_file(dataset.theme or "")
    dataset.status = DatasetStatus.VALIDATED
    dataset.published_at = None
    db.commit()
    db.refresh(dataset)
    return _to_read(dataset, _usernames(db))
