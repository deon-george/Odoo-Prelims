"""Shared FastAPI dependencies, including JWT authentication and RBAC."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole, UserStatus

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Access token returned by POST /api/auth/login.",
)


def _unauthorized(detail: str = "Authentication required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (TokenError, KeyError, TypeError, ValueError) as exc:
        raise _unauthorized("Invalid or expired access token.") from exc

    user = db.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise _unauthorized("Invalid or expired access token.")
    return user


def require_roles(*roles: UserRole | str) -> Callable[[User], User]:
    """Return a dependency that allows only the listed roles.

    Role is read from the database on every request, so a forged JWT ``role``
    claim cannot escalate privileges.
    """
    allowed = {role.value if isinstance(role, UserRole) else role for role in roles}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return dependency
