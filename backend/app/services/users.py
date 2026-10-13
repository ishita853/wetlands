import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import Role, hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


def seed_initial_admin(db: Session) -> User | None:
    """Creates the first administrator while the users table is empty.

    The account is flagged `must_change_password`, so the configured initial
    password only works long enough to set a new one.
    """
    if not (settings.INITIAL_ADMIN_USERNAME and settings.INITIAL_ADMIN_PASSWORD):
        return None
    if db.scalar(select(func.count()).select_from(User)):
        return None
    user = User(
        username=settings.INITIAL_ADMIN_USERNAME,
        hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
        role=Role.SUPER_ADMIN,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    logger.warning(
        "Created initial administrator %r; the password must be changed at first sign-in.",
        user.username,
    )
    return user
