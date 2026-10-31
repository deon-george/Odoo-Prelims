"""Admin-only staff management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import StaffCreateRequest, UserOut, UserStatusUpdateRequest
from app.services import auth_service

router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_roles(UserRole.ADMIN)


@router.post(
    "/staff",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff account (admin only)",
)
def create_staff(
    payload: StaffCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> UserOut:
    try:
        user = auth_service.create_staff(
            db,
            full_name=payload.full_name,
            email=str(payload.email),
            password=payload.password,
        )
    except auth_service.EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    return UserOut.model_validate(user)


@router.get(
    "/users",
    response_model=list[UserOut],
    summary="List all accounts (admin only)",
)
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> list[UserOut]:
    return [UserOut.model_validate(user) for user in auth_service.list_users(db)]


@router.patch(
    "/users/{user_id}/status",
    response_model=UserOut,
    summary="Activate or deactivate a staff account (admin only)",
)
def update_staff_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> UserOut:
    try:
        user = auth_service.set_staff_status(db, user_id, payload.status)
    except auth_service.UserNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from exc
    except auth_service.NotStaffAccount as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins can only change the status of staff accounts.",
        ) from exc
    return UserOut.model_validate(user)
