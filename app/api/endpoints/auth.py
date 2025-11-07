import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages, deps
from app.core.config import get_settings
from app.core.security.jwt import create_jwt_token
from app.core.security.password import (
    DUMMY_PASSWORD,
    get_password_hash,
    is_password_too_simple,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.requests import (
    RefreshTokenRequest,
    UserCreateRequest,
    UserLoginRequest,
)
from app.schemas.responses import AccessTokenResponse, UserResponse

router = APIRouter()

ACCESS_TOKEN_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Invalid email or password",
        "content": {
            "application/json": {"example": {"detail": api_messages.PASSWORD_INVALID}}
        },
    },
}

REFRESH_TOKEN_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Refresh token expired or is already used",
        "content": {
            "application/json": {
                "examples": {
                    "refresh token expired": {
                        "summary": api_messages.REFRESH_TOKEN_EXPIRED,
                        "value": {"detail": api_messages.REFRESH_TOKEN_EXPIRED},
                    },
                    "refresh token already used": {
                        "summary": api_messages.REFRESH_TOKEN_ALREADY_USED,
                        "value": {"detail": api_messages.REFRESH_TOKEN_ALREADY_USED},
                    },
                }
            }
        },
    },
    404: {
        "description": "Refresh token does not exist",
        "content": {
            "application/json": {
                "example": {"detail": api_messages.REFRESH_TOKEN_NOT_FOUND}
            }
        },
    },
}


@router.post(
    "/access-token",
    response_model=AccessTokenResponse,
    responses=ACCESS_TOKEN_RESPONSES,
    description="OAuth2 compatible token, get an access token for future requests using username and password",
)
async def login_access_token(
    form_data: UserLoginRequest,
    response: Response,
    session: AsyncSession = Depends(deps.get_session),
) -> AccessTokenResponse:
    user = await session.scalar(select(User).where(User.email == form_data.email))

    if user is None:
        # this is naive method to not return early
        verify_password(form_data.password, DUMMY_PASSWORD)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_INVALID,
        )

    if not verify_password(form_data.password, user.pass_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_INVALID,
        )

    jwt_token = create_jwt_token(user_id=user.unique_id)

    refresh_token = RefreshToken(
        user_id=user.unique_id,
        refresh_token=secrets.token_urlsafe(32),
        exp=int(time.time() + get_settings().security.refresh_token_expire_secs),
    )
    session.add(refresh_token)
    await session.commit()

    # Set HttpOnly cookie with access token
    response.set_cookie(
        key="access_token",
        value=jwt_token.access_token,
        httponly=True,
        secure=True,  # consider False for local HTTP dev if needed
        samesite="lax",  # set to "none" if cross-site cookies are required (requires HTTPS)
        max_age=get_settings().security.jwt_access_token_expire_secs,
        expires=jwt_token.payload.exp,
        path="/",
    )

    # Keep response body for backward compatibility (frontend may still read it)
    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=refresh_token.refresh_token,
        refresh_token_expires_at=refresh_token.exp,
    )


@router.post(
    "/refresh-token",
    response_model=AccessTokenResponse,
    responses=REFRESH_TOKEN_RESPONSES,
    description="OAuth2 compatible token, get an access token for future requests using refresh token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    response: Response,
    session: AsyncSession = Depends(deps.get_session),
) -> AccessTokenResponse:
    token = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.refresh_token == data.refresh_token)
        .with_for_update(skip_locked=True)
    )

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.REFRESH_TOKEN_NOT_FOUND,
        )
    elif time.time() > token.exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_EXPIRED,
        )
    elif token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_ALREADY_USED,
        )

    # Check if user still exists
    user = await session.scalar(select(User).where(User.unique_id == token.user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.JWT_ERROR_USER_REMOVED,
        )

    token.used = True
    session.add(token)

    jwt_token = create_jwt_token(user_id=token.user_id)

    refresh_token = RefreshToken(
        user_id=token.user_id,
        refresh_token=secrets.token_urlsafe(32),
        exp=int(time.time() + get_settings().security.refresh_token_expire_secs),
    )
    session.add(refresh_token)
    await session.commit()

    # Rotate access token cookie
    response.set_cookie(
        key="access_token",
        value=jwt_token.access_token,
        httponly=True,
        secure=True,  # consider False for local HTTP dev if needed
        samesite="lax",  # set to "none" if cross-site cookies are required (requires HTTPS)
        max_age=get_settings().security.jwt_access_token_expire_secs,
        expires=jwt_token.payload.exp,
        path="/",
    )

    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=refresh_token.refresh_token,
        refresh_token_expires_at=refresh_token.exp,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    description="Create new user",
    status_code=status.HTTP_201_CREATED,
)
async def register_new_user(
    new_user: UserCreateRequest,
    session: AsyncSession = Depends(deps.get_session),
) -> User:
    # Normalize email to lowercase
    normalized_email = new_user.email.lower()

    # Check for non-ASCII characters in email (should return 400)
    try:
        normalized_email.encode("ascii")
    except UnicodeEncodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format",
        )

    # Check if email is already used (use normalized email)
    user = await session.scalar(select(User).where(User.email == normalized_email))

    pass_check_result = is_password_too_simple(new_user.password)
    if pass_check_result:
        detail = (
            pass_check_result[1]
            if isinstance(pass_check_result, tuple)
            else api_messages.PASSWORD_INVALID
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        )

    user = User(
        email=normalized_email,
        username=new_user.username,
        pass_hash=get_password_hash(new_user.password),
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:  # pragma: no cover
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        )

    return user
