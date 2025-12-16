"""
Authentication Pydantic models and schemas.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8,
                          description="Password must be at least 8 characters")
    name: str = Field(..., min_length=2, max_length=100)


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        default=3600, description="Token expiration in seconds")


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    """User response model (without password)."""
    id: str
    email: str
    name: str
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """User model with hashed password (internal use)."""
    hashed_password: str
