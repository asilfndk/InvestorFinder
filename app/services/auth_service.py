"""
Authentication service for user registration, login, and JWT handling.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.database.models import User
from app.models.auth import UserCreate, UserResponse, Token, TokenData
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_secret_key(self) -> str:
        """Get JWT secret key from settings."""
        secret = getattr(settings, 'jwt_secret_key', None)
        if not secret:
            # Fallback to a default for development (should be set in production)
            secret = "dev-secret-key-change-in-production"
        return secret

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, self._get_secret_key(), algorithm=ALGORITHM)

        return encoded_jwt

    def decode_token(self, token: str) -> Optional[TokenData]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token, self._get_secret_key(), algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            email: str = payload.get("email")

            if user_id is None:
                return None

            return TokenData(user_id=user_id, email=email)
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """Register a new user."""
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise AppException(
                code="user_exists",
                message="A user with this email already exists"
            )

        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            email=user_data.email,
            name=user_data.name,
            hashed_password=self.get_password_hash(user_data.password),
            is_active=True,
            created_at=datetime.utcnow()
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"New user registered: {user.email}")

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at
        )

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = await self.get_user_by_email(email)

        if not user:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    async def login(self, email: str, password: str) -> Token:
        """Login a user and return a JWT token."""
        user = await self.authenticate_user(email, password)

        if not user:
            raise AppException(
                code="invalid_credentials",
                message="Invalid email or password"
            )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.id, "email": user.email},
            expires_delta=access_token_expires
        )

        logger.info(f"User logged in: {user.email}")

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )


# Dependency for getting auth service
async def get_auth_service():
    """Dependency to get AuthService with database session."""
    async for session in get_db():
        yield AuthService(session)
