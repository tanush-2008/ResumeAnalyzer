"""Password hashing + JWT issuance/verification for the optional user-login feature."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger("resume_analyzer.auth")

_DEFAULT_SECRET = "dev-only-insecure-secret-change-me"
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEFAULT_SECRET)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _check_secret_key() -> None:
    """Fail fast rather than silently signing production tokens with a
    publicly-known default secret."""
    if SECRET_KEY != _DEFAULT_SECRET:
        return
    if os.environ.get("APP_ENV", "development").lower() == "production":
        raise RuntimeError(
            "JWT_SECRET_KEY is unset while APP_ENV=production. Refusing to start: "
            "set a strong, unique JWT_SECRET_KEY before deploying."
        )
    logger.warning(
        "JWT_SECRET_KEY is not set - using an insecure default. This is fine for "
        "local development only; set JWT_SECRET_KEY before deploying."
    )


_check_secret_key()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
