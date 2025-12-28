from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security.password import get_password_hash
from app.models import User


async def verify_api_key(
    request: Request,
    session: AsyncSession,
) -> User:
    """Verify API key and return the associated user"""
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required for internal endpoints",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # For demo purposes, we'll use a simple API key validation
    # In production, this should be more secure with proper key management
    expected_api_key = get_settings().security.internal_api_key

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal API key not configured",
        )

    if api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # For internal APIs, we'll use a system admin user
    # In production, you might want to associate API keys with specific service accounts
    system_user = await session.scalar(
        select(User).where(User.email == "system@internal.com")
    )

    if not system_user:
        # Create a system user if it doesn't exist
        system_user = User(
            email="system@internal.com",
            username="system",
            pass_hash=get_password_hash(
                get_settings().security.jwt_secret_key.get_secret_value()
            ),
            role="admin",
        )
        session.add(system_user)
        await session.commit()
        await session.refresh(system_user)

    return system_user


async def get_internal_user(
    request: Request,
    session: AsyncSession,
) -> User:
    """Get authenticated user for internal endpoints"""
    return await verify_api_key(request, session)
