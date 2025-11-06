from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages
from app.core import database_session
from app.core.security.jwt import verify_jwt_token
from app.models import Module, PurchasedCourse, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/access-token")


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with database_session.get_async_session() as session:
        yield session


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_session),
) -> User:
    token_payload = verify_jwt_token(token)

    user = await session.scalar(select(User).where(User.unique_id == token_payload.sub))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.JWT_ERROR_USER_REMOVED,
        )
    return user


async def verify_course_access(
    course_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> bool:
    """Verify user has purchased the course"""
    purchase = await session.scalar(
        select(PurchasedCourse).where(
            PurchasedCourse.user_id == current_user.unique_id,
            PurchasedCourse.course_id == course_id,
        )
    )
    return purchase is not None


async def get_module_with_access_check(
    module_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Module:
    """Get module and verify user has purchased the course"""
    from sqlalchemy.orm import selectinload

    # Load module with course relationship
    module = await session.scalar(
        select(Module)
        .options(selectinload(Module.course))
        .where(Module.unique_id == module_id)
    )

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Module not found"
        )

    # Check if user purchased the course
    has_access = await verify_course_access(module.course_id, current_user, session)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must purchase this course to access its tests",
        )

    return module
