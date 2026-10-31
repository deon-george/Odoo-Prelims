"""Pydantic request/response schemas for authentication and RBAC.

Security notes:
- Registration schemas forbid unknown fields, so a client cannot inject
  ``role``, ``status`` or ``hashed_password``.
- Password fields are validated against the same policy as the CLI.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.password_policy import MAX_PASSWORD_LENGTH, validate_password_strength
from app.models.user import UserStatus


def _clean_full_name(value: str) -> str:
    value = value.strip()
    if not 2 <= len(value) <= 150:
        raise ValueError("Full name must be between 2 and 150 characters.")
    return value


def _clean_password(value: str) -> str:
    errors = validate_password_strength(value)
    if errors:
        raise ValueError(" ".join(errors))
    return value


class RegisterRequest(BaseModel):
    """Public customer self-registration.

    ``extra="forbid"`` is intentional: the role is always set to ``customer``
    server-side and any attempt to send a role is rejected with 422.
    """

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return _clean_full_name(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _clean_password(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=16, max_length=512)
    new_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _clean_password(value)


class StaffCreateRequest(BaseModel):
    """Admin-only staff creation. Role is forced to ``staff`` server-side."""

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return _clean_full_name(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _clean_password(value)


class UserStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: UserStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MessageResponse(BaseModel):
    message: str
