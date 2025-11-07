from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages, deps
from app.core.security.password import get_password_hash, is_password_too_simple
from app.models import RefreshToken, User
from app.schemas.requests import UserUpdatePasswordRequest
from app.schemas.responses import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse, description="Get current user")
async def read_current_user(
    current_user: User = Depends(deps.get_current_user),
) -> User:
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete current user",
)
async def delete_current_user(
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> None:
    await session.execute(
        delete(RefreshToken).where(RefreshToken.user_id == current_user.unique_id)
    )
    await session.execute(delete(User).where(User.unique_id == current_user.unique_id))
    await session.commit()


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Update current user password",
)
async def reset_current_user_password(
    user_update_password: UserUpdatePasswordRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    # Log the password being validated for debugging
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"Validating password: {user_update_password.password}")

    pass_check_result = is_password_too_simple(user_update_password.password)
    logger.debug(f"Password validation result: {pass_check_result}")

    if pass_check_result:
        detail = (
            pass_check_result[1]
            if isinstance(pass_check_result, tuple)
            else api_messages.PASSWORD_INVALID
        )
        logger.debug(f"Password rejected: {detail}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    logger.debug("Password accepted, updating hash")
    current_user.pass_hash = get_password_hash(user_update_password.password)
    session.add(current_user)
    await session.commit()
