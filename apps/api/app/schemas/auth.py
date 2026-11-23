from __future__ import annotations

from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


class UserRegister(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, description='Valid email address')
    password: str = Field(..., min_length=8, max_length=128, description='Password of at least 8 characters')
    full_name: str = Field(..., min_length=1, max_length=255, description='Full name of the user')

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_REGEX.match(normalized):
            raise ValueError('Invalid email address format.')
        return normalized

    @field_validator('full_name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('Full name cannot be blank.')
        return normalized

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        if len(value) > 128:
            raise ValueError('Password must not exceed 128 characters.')
        return value


class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = Field(default=None, description='Optional refresh token if not supplied via HttpOnly cookie')


class MessageResponse(BaseModel):
    message: str
