"""Password hashing and token primitives.

Passwords use Argon2id. Access tokens are short-lived JWTs. Refresh and
password-reset tokens are opaque random values stored only as SHA-256 hashes.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

# OWASP-recommended Argon2id parameters (64 MiB, 3 iterations, 2 lanes).
_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


class TokenError(Exception):
    """Raised when an access token is missing, invalid, or expired."""


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> tuple[bool, bool]:
    """Verify a password.

    Returns (is_valid, needs_rehash) so callers can transparently upgrade
    hashes when Argon2 parameters change.
    """
    try:
        _password_hasher.verify(hashed_password, password)
        return True, _password_hasher.check_needs_rehash(hashed_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False


def create_access_token(
    *,
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expires_at,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid or expired access token.") from exc

    if payload.get("type") != "access":
        raise TokenError("Invalid token type.")
    return payload


def generate_opaque_token(nbytes: int = 48) -> str:
    """Generate a high-entropy token for refresh / password-reset links."""
    return secrets.token_urlsafe(nbytes)


def hash_opaque_token(token: str) -> str:
    """SHA-256 is sufficient for high-entropy random tokens (unlike passwords)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
