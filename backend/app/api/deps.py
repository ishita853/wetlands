from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Role, decode_access_token
from app.db.session import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(detail: str = "Not authenticated.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Any signed-in user, including one who still has to change the password."""
    if credentials is None:
        raise _unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Session expired. Sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized() from exc

    user = db.scalar(select(User).where(User.username == payload.get("sub")))
    if user is None or not user.is_active or payload.get("ver") != user.token_version:
        raise _unauthorized("Session is no longer valid. Sign in again.")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """A signed-in data manager/administrator whose password is not pending change."""
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Change the initial password before continuing.",
        )
    if user.role not in (Role.SUPER_ADMIN, Role.DATA_MANAGER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted.")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
AdminDep = Annotated[User, Depends(require_admin)]
