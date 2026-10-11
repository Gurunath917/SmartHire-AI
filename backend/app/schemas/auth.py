"""
Pydantic schemas for authentication endpoints.
These define what the API accepts (request) and returns (response).
Passwords are NEVER included in any response schema.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.models.user import UserRole


# ── Request schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Body for POST /api/auth/register"""
    full_name: str
    email: EmailStr
    password: str
    role: UserRole  # CANDIDATE or RECRUITER (ADMIN created manually)

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Full name must be under 255 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must be under 128 characters")
        return v

    @field_validator("role")
    @classmethod
    def role_not_admin(cls, v: UserRole) -> UserRole:
        if v == UserRole.ADMIN:
            raise ValueError("Cannot self-register as ADMIN")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Arjun Sharma",
                "email": "arjun@example.com",
                "password": "SecurePass@123",
                "role": "CANDIDATE",
            }
        }
    }


class LoginRequest(BaseModel):
    """Body for POST /api/auth/login"""
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "arjun@example.com",
                "password": "SecurePass@123",
            }
        }
    }


# ── Response schemas ──────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned on successful login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # seconds until expiry
    user_id: int
    full_name: str
    email: str
    role: UserRole


class UserResponse(BaseModel):
    """Safe user object — never includes password."""
    id: int
    full_name: str
    email: str
    user_role: UserRole   # matches the ORM column name
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @property
    def role(self) -> UserRole:
        return self.user_role


class MessageResponse(BaseModel):
    """Generic success message response."""
    message: str
    success: bool = True
