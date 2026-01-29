import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"
# bcrypt truncates silently past 72 bytes, so reject longer passwords instead.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(userid: uuid.UUID) -> str:
    expiry = datetime.now(UTC) + timedelta(minutes=settings.jwt_ttl_minutes)
    payload = {"sub": str(userid), "exp": expiry}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def read_token(token: str) -> uuid.UUID | None:
    """Return the user id, or None if the token is missing, malformed, or expired."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret.get_secret_value(), algorithms=[ALGORITHM]
        )
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
