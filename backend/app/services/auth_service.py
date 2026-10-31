"""Authentication and user-management business logic.

All password/token handling lives here so routes stay thin. Plaintext
passwords are never stored, returned, or logged.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole, UserStatus


class AuthServiceError(Exception):
    """Base class for expected authentication failures."""


class EmailAlreadyRegistered(AuthServiceError):
    pass


class InvalidCredentials(AuthServiceError):
    pass


class AccountNotActive(AuthServiceError):
    pass


class InvalidRefreshToken(AuthServiceError):
    pass


class InvalidResetToken(AuthServiceError):
    pass


class UserNotFound(AuthServiceError):
    pass


class NotStaffAccount(AuthServiceError):
    pass


def _now() -> datetime:
    """Naive local time, matching MySQL DATETIME columns on this host."""
    return datetime.now()


def normalize_email(email: str) -> str:
    return str(email).strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def _create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    role: UserRole,
) -> User:
    email = normalize_email(email)
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegistered

    user = User(
        full_name=full_name.strip(),
        email=email,
        hashed_password=hash_password(password),
        role=role.value,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # race with a concurrent registration
        db.rollback()
        raise EmailAlreadyRegistered from exc
    db.refresh(user)
    return user


def register_customer(db: Session, *, full_name: str, email: str, password: str) -> User:
    return _create_user(
        db,
        full_name=full_name,
        email=email,
        password=password,
        role=UserRole.CUSTOMER,
    )


def create_staff(db: Session, *, full_name: str, email: str, password: str) -> User:
    return _create_user(
        db,
        full_name=full_name,
        email=email,
        password=password,
        role=UserRole.STAFF,
    )


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        # Burn a hash verification so unknown emails take similar time.
        verify_password(password, hash_password("TimingOnly!123"))
        raise InvalidCredentials

    valid, needs_rehash = verify_password(password, user.hashed_password)
    if not valid:
        raise InvalidCredentials
    if user.status != UserStatus.ACTIVE.value:
        raise AccountNotActive
    if needs_rehash:
        user.hashed_password = hash_password(password)
        db.commit()
    return user


def start_session(db: Session, user: User) -> tuple[str, str]:
    """Create an access JWT plus a rotating opaque refresh token."""
    raw_refresh = generate_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_refresh),
            expires_at=_now() + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    access_token = create_access_token(user_id=user.id, role=user.role)
    return access_token, raw_refresh


def rotate_session(db: Session, raw_refresh: str) -> tuple[User, str, str]:
    """Validate and revoke the supplied refresh token, then issue a new pair."""
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_opaque_token(raw_refresh)
        )
    )
    now = _now()
    if record is None or record.revoked_at is not None or record.expires_at <= now:
        raise InvalidRefreshToken

    user = db.get(User, record.user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise InvalidRefreshToken

    record.revoked_at = now
    access_token, new_refresh = start_session(db, user)
    return user, access_token, new_refresh


def revoke_session(db: Session, raw_refresh: str | None) -> None:
    if not raw_refresh:
        return
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_opaque_token(raw_refresh)
        )
    )
    if record is None or record.revoked_at is not None:
        return
    record.revoked_at = _now()
    db.commit()


def _revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


def request_password_reset(db: Session, email: str) -> str | None:
    """Return a raw reset token for delivery, or None for unknown accounts.

    Unknown/disabled accounts intentionally return the same generic response to
    the caller to avoid account enumeration.
    """
    user = get_user_by_email(db, email)
    if user is None or user.status != UserStatus.ACTIVE.value:
        return None

    now = _now()
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw_token = generate_opaque_token(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=now
            + timedelta(minutes=settings.password_reset_token_expire_minutes),
        )
    )
    db.commit()
    return raw_token


def reset_password(db: Session, *, raw_token: str, new_password: str) -> User:
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_opaque_token(raw_token)
        )
    )
    now = _now()
    if record is None or record.used_at is not None or record.expires_at <= now:
        raise InvalidResetToken

    user = db.get(User, record.user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise InvalidResetToken

    user.hashed_password = hash_password(new_password)
    record.used_at = now
    _revoke_all_refresh_tokens(db, user.id)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


def set_staff_status(db: Session, user_id: int, status: UserStatus) -> User:
    """Admins may only change the status of staff accounts."""
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFound
    if user.role != UserRole.STAFF.value:
        raise NotStaffAccount

    user.status = status.value
    if status != UserStatus.ACTIVE:
        _revoke_all_refresh_tokens(db, user.id)
    db.commit()
    db.refresh(user)
    return user
