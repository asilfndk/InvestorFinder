"""
Authentication API routes.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.auth import UserCreate, UserLogin, Token, UserResponse
from app.services.auth_service import AuthService, get_auth_service
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user.

    - **email**: Valid email address (must be unique)
    - **password**: At least 8 characters
    - **name**: User's full name (2-100 characters)
    """
    try:
        user = await auth_service.register_user(user_data)
        return user
    except AppException as e:
        if e.code == "user_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=e.message
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login and get an access token.

    - **email**: Registered email address
    - **password**: User's password

    Returns a JWT access token valid for 60 minutes.
    """
    try:
        token = await auth_service.login(credentials.email, credentials.password)
        return token
    except AppException as e:
        if e.code == "invalid_credentials":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"}
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Dependency to get the current authenticated user from JWT token.
    """
    token = credentials.credentials
    token_data = auth_service.decode_token(token)

    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = await auth_service.get_user_by_id(token_data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        created_at=user.created_at
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """
    Get current authenticated user's profile.

    Requires a valid JWT token in the Authorization header.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh the access token.

    Requires a valid JWT token. Returns a new token with extended expiration.
    """
    from datetime import timedelta

    access_token = auth_service.create_access_token(
        data={"sub": current_user.id, "email": current_user.email},
        expires_delta=timedelta(minutes=60)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=3600
    )
