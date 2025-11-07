import logging
import os
import uuid
from collections.abc import AsyncGenerator, Callable
from typing import Any, Dict, Optional

import pytest
import pytest_asyncio
import sqlalchemy
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.core import database_session
from app.core.config import get_settings
from app.core.security.jwt import create_jwt_token
from app.core.security.password import get_password_hash
from app.main import app as fastapi_app
from app.models import Base, User

# Test data constants
TEST_USER_ID = "b75365d9-7bf9-4f54-add5-aeab333a087b"
TEST_USER_EMAIL = "geralt@wiedzmin.pl"
TEST_USER_PASSWORD = "Geralt123!"
TEST_USER_ACCESS_TOKEN = create_jwt_token(TEST_USER_ID).access_token

# Additional test users for comprehensive testing
TEST_USER_2_ID = "a75365d9-7bf9-4f54-add5-aeab333a087c"
TEST_USER_2_EMAIL = "yennefer@vingerberg.pl"
TEST_USER_2_PASSWORD = "Yennefer123!"

TEST_USER_3_ID = "c75365d9-7bf9-4f54-add5-aeab333a087d"
TEST_USER_3_EMAIL = "triss@maribor.pl"
TEST_USER_3_PASSWORD = "Triss123!"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def fixture_setup_new_test_database() -> None:
    """Set up test database for the test session."""
    worker_name = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    test_db_name = f"test_db_{worker_name}"

    # create new test db using connection to current database
    conn = await database_session._ASYNC_ENGINE.connect()
    await conn.execution_options(isolation_level="AUTOCOMMIT")
    await conn.execute(sqlalchemy.text(f"DROP DATABASE IF EXISTS {test_db_name}"))
    await conn.execute(sqlalchemy.text(f"CREATE DATABASE {test_db_name}"))
    await conn.close()

    session_mpatch = pytest.MonkeyPatch()
    session_mpatch.setenv("DATABASE__DB", test_db_name)
    session_mpatch.setenv("SECURITY__PASSWORD_BCRYPT_ROUNDS", "4")

    # force settings to use now monkeypatched environments
    get_settings.cache_clear()

    # monkeypatch test database engine
    engine = database_session.new_async_engine(get_settings().sqlalchemy_database_uri)

    session_mpatch.setattr(
        database_session,
        "_ASYNC_ENGINE",
        engine,
    )
    session_mpatch.setattr(
        database_session,
        "_ASYNC_SESSIONMAKER",
        async_sessionmaker(engine, expire_on_commit=False),
    )

    # create app tables in test database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def fixture_clean_get_settings_between_tests() -> AsyncGenerator[None]:
    """Clean settings between tests."""
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture(name="session", scope="function")
async def fixture_session_with_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[AsyncSession]:
    """Provide a database session with rollback for each test."""
    # we want to monkeypatch get_async_session with one bound to session
    # that we will always rollback on function scope

    connection = await database_session._ASYNC_ENGINE.connect()
    transaction = await connection.begin()

    session = AsyncSession(bind=connection, expire_on_commit=False)

    monkeypatch.setattr(
        database_session,
        "get_async_session",
        lambda: session,
    )

    yield session

    logging.critical("Rolling back transaction")
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(name="client", scope="function")
async def fixture_client(session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Provide an HTTP client for testing."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as aclient:
        aclient.headers.update({"Host": "localhost"})
        yield aclient


@pytest_asyncio.fixture(name="default_hashed_password", scope="session")
async def fixture_default_hashed_password() -> str:
    """Provide a default hashed password for testing."""
    return get_password_hash(TEST_USER_PASSWORD)


@pytest_asyncio.fixture(name="default_user", scope="function")
async def fixture_default_user(
    session: AsyncSession, default_hashed_password: str
) -> AsyncGenerator[User]:
    """Create a default user for testing."""
    default_user = User(
        unique_id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        username="geralt",
        pass_hash=default_hashed_password,
    )
    session.add(default_user)

    await session.commit()
    await session.refresh(default_user)

    yield default_user


@pytest_asyncio.fixture(name="default_user_headers", scope="function")
async def fixture_default_user_headers(default_user: User) -> Dict[str, str]:
    """Provide headers with default user authentication."""
    return {"Authorization": f"Bearer {TEST_USER_ACCESS_TOKEN}"}


@pytest_asyncio.fixture(name="test_user_factory", scope="function")
async def fixture_test_user_factory(
    session: AsyncSession,
) -> AsyncGenerator[Callable[..., Any]]:
    """Factory for creating test users with custom parameters."""

    async def create_user(
        email: str, username: str, password: str, unique_id: str | None = None
    ) -> User:
        """Create a test user with given parameters."""
        if unique_id is None:
            unique_id = str(uuid.uuid4())

        user = User(
            unique_id=unique_id,
            email=email,
            username=username,
            pass_hash=get_password_hash(password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    yield create_user


@pytest_asyncio.fixture(name="authenticated_client", scope="function")
async def fixture_authenticated_client(
    client: AsyncClient, test_user_factory: Callable[..., Any]
) -> AsyncGenerator[AsyncClient]:
    """Provide an authenticated client with a test user."""
    user = await test_user_factory(
        email="auth@test.com", username="authuser", password="AuthPass123!"
    )
    token = create_jwt_token(user.unique_id).access_token
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client


# Test data fixtures for different scenarios
@pytest.fixture(name="valid_registration_data", scope="session")
def fixture_valid_registration_data() -> Dict[str, Any]:
    """Provide valid registration data for testing."""
    return {"email": "user@example.com", "password": "String123!", "username": "string"}


@pytest.fixture(name="invalid_registration_data", scope="session")
def fixture_invalid_registration_data() -> Dict[str, Dict[str, Any]]:
    """Provide various invalid registration data scenarios."""
    return {
        "missing_email": {"password": "String123!", "username": "string2"},
        "missing_username": {"email": "user3@example.com", "password": "String123!"},
        "missing_password": {"email": "user3@example.com", "username": "string2"},
        "invalid_email": {
            "email": "user3__example.com",
            "password": "String123!",
            "username": "string2",
        },
        "simple_password": {
            "email": "user3@example.com",
            "password": "string",
            "username": "s",
        },
        "empty_body": {},
        "sql_injection_email": {
            "email": "'; DROP TABLE users; --",
            "password": "String123!",
            "username": "s",
        },
        "uppercase_email": {
            "email": "USER@EXAMPLE.COM",
            "password": "Password123!",
            "username": "user",
        },
        "min_length_password": {
            "email": "user@example.com",
            "password": "Pass12!",
            "username": "testuser",
        },
        "cyrillic_password": {
            "email": "user@example.com",
            "password": "Пароль123!",
            "username": "name",
        },
        "cyrillic_username": {
            "email": "user@example.com",
            "password": "Пароль123!",
            "username": "имя",
        },
        "cyrillic_email": {
            "email": "юзер@маил.сом",
            "password": "password",
            "username": "имя",
        },
    }


@pytest.fixture(name="valid_login_data", scope="session")
def fixture_valid_login_data() -> Dict[str, Any]:
    """Provide valid login data for testing."""
    return {"email": "useeeer@mail.ru", "password": "Password123!"}


@pytest.fixture(name="invalid_login_data", scope="session")
def fixture_invalid_login_data() -> Dict[str, Dict[str, Any]]:
    """Provide various invalid login data scenarios."""
    return {
        "wrong_password": {"email": "useeeer@mail.ru", "password": "WrongPass123!"},
        "wrong_email": {"email": "useer@mail.ru", "password": "Password123!"},
    }


@pytest.fixture(name="valid_password_reset_data", scope="session")
def fixture_valid_password_reset_data() -> Dict[str, Any]:
    """Provide valid password reset data for testing."""
    return {"new_password": "String123!", "cyrillic_password": "Пароль123!"}


@pytest.fixture(name="invalid_password_reset_data", scope="session")
def fixture_invalid_password_reset_data() -> Dict[str, Any]:
    """Provide invalid password reset data for testing."""
    return {
        "password": "stringaaaa"  # Empty password case
    }
