"""Authentication routes: register, login, refresh, logout, me, reset."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "sms_refresh_token"
COOKIE_PATH = "/api/auth"
COOKIE_MAX_AGE = settings.refresh_token_expire_days * 24 * 60 * 60


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=COOKIE_PATH,
        domain=settings.cookie_domain,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=COOKIE_PATH,
        domain=settings.cookie_domain,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


def _token_response(user: User, access_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer account",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    try:
        user = auth_service.register_customer(
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


@router.post("/login", response_model=TokenResponse, summary="Sign in")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user = auth_service.authenticate(
            db,
            email=str(payload.email),
            password=payload.password,
        )
    except auth_service.InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except auth_service.AccountNotActive as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active. Please contact an administrator.",
        ) from exc

    access_token, raw_refresh = auth_service.start_session(db, user)
    _set_refresh_cookie(response, raw_refresh)
    return _token_response(user, access_token)


@router.post("/refresh", response_model=TokenResponse, summary="Rotate session")
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user, access_token, new_refresh = auth_service.rotate_session(db, refresh_token)
    except auth_service.InvalidRefreshToken as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    _set_refresh_cookie(response, new_refresh)
    return _token_response(user, access_token)


@router.post("/logout", response_model=MessageResponse, summary="Sign out")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> MessageResponse:
    auth_service.revoke_session(db, refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=UserOut, summary="Current user")
def read_current_user(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a password reset",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    generic = (
        "If an account exists for that email, a password reset link has been sent."
    )
    raw_token = auth_service.request_password_reset(db, str(payload.email))
    if raw_token is not None:
        try:
            send_password_reset_email(
                auth_service.normalize_email(str(payload.email)),
                raw_token,
            )
        except Exception:  # noqa: BLE001 - never leak delivery details to callers
            logger.exception("Password reset email delivery failed.")
    return MessageResponse(message=generic)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset a password with a single-use token",
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        auth_service.reset_password(
            db,
            raw_token=payload.token,
            new_password=payload.new_password,
        )
    except auth_service.InvalidResetToken as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has expired.",
        ) from exc
    return MessageResponse(
        message="Your password has been reset. You can now sign in."
    )
