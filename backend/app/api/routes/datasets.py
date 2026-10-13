from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.dataset import Dataset, DatasetStatus

router = APIRouter(prefix="/datasets", tags=["datasets"])


class PublishedDataset(BaseModel):
    """Public catalogue entry — no uploader or storage details."""

    name: str
    theme: str | None
    description: str | None
    summary: dict | None
    published_at: str | None


@router.get("", response_model=list[PublishedDataset])
def list_published_datasets(db: DbSession) -> list[PublishedDataset]:
    rows = db.scalars(
        select(Dataset).where(Dataset.status == DatasetStatus.PUBLISHED).order_by(Dataset.theme)
    ).all()
    return [
        PublishedDataset(
            name=d.name,
            theme=d.theme,
            description=d.description,
            summary=d.summary,
            published_at=d.published_at.isoformat() if d.published_at else None,
        )
        for d in rows
    ]
