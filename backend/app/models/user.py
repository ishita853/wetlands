import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import Role
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Portal administrator / data manager account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Set for the seeded account; the API refuses everything except changing
    # the password until it is cleared.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # Incremented on password change; tokens carrying an older version are rejected.
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
