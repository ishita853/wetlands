from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbSession
from app.core.config import settings
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    password_policy_errors,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, CurrentUser, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID = "Incorrect username or password."


def _token_for(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.username, user.role, user.token_version),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        must_change_password=user.must_change_password,
    )


def _aware(value: datetime | None) -> datetime | None:
    # SQLite returns naive datetimes; treat stored values as UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username.strip()))
    now = datetime.now(UTC)

    if user is None or not user.is_active:
        verify_password(payload.password, DUMMY_HASH)  # equalise timing
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID)

    locked_until = _aware(user.locked_until)
    if locked_until and locked_until > now:
        minutes = max(1, round((locked_until - now).total_seconds() / 60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in about {minutes} minute(s).",
        )

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID)

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    return _token_for(user)


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUserDep) -> CurrentUser:
    return CurrentUser(
        username=user.username, role=user.role, must_change_password=user.must_change_password
    )


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    payload: ChangePasswordRequest, user: CurrentUserDep, db: DbSession
) -> TokenResponse:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The current password is incorrect."
        )
    problems = password_policy_errors(
        payload.new_password, username=user.username, current=payload.current_password
    )
    if problems:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=problems)

    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    user.token_version += 1  # signs out every other session
    db.commit()
    return _token_for(user)
