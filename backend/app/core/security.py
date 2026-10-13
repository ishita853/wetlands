from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt is used directly: passlib is unmaintained and breaks on bcrypt >= 4.1.
_BCRYPT_ROUNDS = 12
# bcrypt only considers the first 72 bytes; longer inputs are rejected by policy.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 12


class Role(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    DATA_MANAGER = "DATA_MANAGER"
    VIEWER = "VIEWER"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode()[:MAX_PASSWORD_BYTES], hashed_password.encode()
        )
    except ValueError:
        return False


# Hash of a random string, verified against when the username does not exist so
# failed logins take the same time whether or not the account exists.
DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


def password_policy_errors(
    password: str, *, username: str, current: str | None = None
) -> list[str]:
    """Returns human-readable reasons the password is not acceptable (empty = OK)."""
    errors: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Use at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        errors.append(f"Use at most {MAX_PASSWORD_BYTES} bytes.")
    classes = [
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ]
    if sum(classes) < 3:
        errors.append("Mix at least three of: lowercase, uppercase, digits, symbols.")
    if username and username.lower() in password.lower():
        errors.append("Do not include the username.")
    if current is not None and password == current:
        errors.append("Choose a password different from the current one.")
    if settings.INITIAL_ADMIN_PASSWORD and password == settings.INITIAL_ADMIN_PASSWORD:
        errors.append("The initial password cannot be reused.")
    return errors


def create_access_token(
    subject: str, role: Role, token_version: int, expires_delta: timedelta | None = None
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        # Bumped on password change so every older token stops working.
        "ver": token_version,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
