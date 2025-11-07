import time
from typing import Any

import pytest
from fastapi import status
from freezegun import freeze_time
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages
from app.core.config import get_settings
from app.core.security.jwt import verify_jwt_token
from app.main import app
from app.models import RefreshToken, User
from app.tests.conftest import TEST_USER_PASSWORD


@pytest.mark.asyncio(loop_scope="session")
class TestUserLogin:
    """Comprehensive tests for user login and token generation."""

    # POSITIVE TESTS

    async def test_login_with_valid_credentials(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test successful login with valid credentials."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )

        if response.status_code != status.HTTP_200_OK:
            print(f"Error response: {response.json()}")

        assert response.status_code == status.HTTP_200_OK
        token_data = response.json()

        # Verify response structure
        assert token_data["token_type"] == "Bearer"
        assert "access_token" in token_data
        assert "expires_at" in token_data
        assert "refresh_token" in token_data
        assert "refresh_token_expires_at" in token_data

    async def test_login_returns_valid_jwt_token(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test that login returns a valid JWT token."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        token_data = response.json()

        # Verify JWT token is valid
        token_payload = verify_jwt_token(token_data["access_token"])
        assert token_payload.sub == default_user.unique_id

    async def test_login_sets_http_only_cookie(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test that login sets HttpOnly cookie with access token."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_200_OK

        # Check if access_token cookie is set
        cookies = response.cookies
        assert "access_token" in cookies

        # Check cookie attributes
        access_token_cookie = cookies.get("access_token")
        assert access_token_cookie is not None

    async def test_login_creates_refresh_token_in_db(
        self,
        client: AsyncClient,
        default_user: User,
        session: AsyncSession,
    ) -> None:
        """Test that login creates refresh token record in database."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        token_data = response.json()

        # Verify refresh token exists in database
        token_count = await session.scalar(
            select(func.count()).where(
                RefreshToken.refresh_token == token_data["refresh_token"]
            )
        )
        assert token_count == 1

    @freeze_time("2023-01-01")
    async def test_login_token_has_correct_expiry_time(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test that login token has correct expiry time."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        token_data = response.json()

        current_timestamp = int(time.time())
        expected_expiry = (
            current_timestamp + get_settings().security.jwt_access_token_expire_secs
        )

        assert token_data["expires_at"] == expected_expiry

    @freeze_time("2023-01-01")
    async def test_login_refresh_token_has_correct_expiry_time(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test that refresh token has correct expiry time."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        token_data = response.json()

        current_timestamp = int(time.time())
        expected_refresh_expiry = (
            current_timestamp + get_settings().security.refresh_token_expire_secs
        )

        assert token_data["refresh_token_expires_at"] == expected_refresh_expiry

    # NEGATIVE TESTS

    async def test_login_with_wrong_password(
        self,
        client: AsyncClient,
        default_user: User,
        invalid_login_data: dict[str, Any],
    ) -> None:
        """Test login with wrong password returns 400."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": invalid_login_data["wrong_password"]["password"],
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": api_messages.PASSWORD_INVALID}

    async def test_login_with_wrong_email(
        self,
        client: AsyncClient,
        invalid_login_data: dict[str, Any],
    ) -> None:
        """Test login with wrong email returns 400."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": invalid_login_data["wrong_email"]["email"],
                "password": invalid_login_data["wrong_email"]["password"],
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": api_messages.PASSWORD_INVALID}

    async def test_login_with_nonexistent_user(
        self,
        client: AsyncClient,
    ) -> None:
        """Test login with non-existent user returns 400."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": "nonexistent@example.com",
                "password": "Password123!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": api_messages.PASSWORD_INVALID}

    async def test_login_with_missing_fields(
        self,
        client: AsyncClient,
    ) -> None:
        """Test login with missing fields returns 422."""
        # Test missing password
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": "test@example.com",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test missing email
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "password": "Password123!",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # SECURITY TESTS

    async def test_login_timing_attack_protection(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test that login timing is consistent for wrong password vs non-existent user."""
        start_time = time.time()
        response1 = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": "WrongPassword123!",
            },
        )
        wrong_password_time = time.time() - start_time

        # Time for non-existent user
        start_time = time.time()
        response2 = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": "nonexistent@example.com",
                "password": "Password123!",
            },
        )
        nonexistent_user_time = time.time() - start_time

        # Both should return 400
        assert response1.status_code == status.HTTP_400_BAD_REQUEST
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

        # Timing should be similar (within reasonable tolerance)
        time_difference = abs(wrong_password_time - nonexistent_user_time)
        assert time_difference < 1.0  # 1s tolerance

    async def test_login_sql_injection_attempt(
        self,
        client: AsyncClient,
    ) -> None:
        """Test login with SQL injection attempt is handled safely."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": "'; DROP TABLE users; --",
                "password": "Password123!",
            },
        )

        # Should be treated as unprocessable entity due to pydantic validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {
                    "ctx": {
                        "reason": "An email address must have an @-sign.",
                    },
                    "input": "'; DROP TABLE users; --",
                    "loc": ["body", "email"],
                    "msg": "value is not a valid email address: An email address must have an @-sign.",
                    "type": "value_error",
                },
            ]
        }

    # DATABASE INTEGRATION TESTS

    async def test_login_refresh_token_has_correct_fields(
        self,
        client: AsyncClient,
        default_user: User,
        session: AsyncSession,
    ) -> None:
        """Test that refresh token in database has correct fields."""
        response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        token_data = response.json()

        # Get refresh token from database
        refresh_token = await session.scalar(
            select(RefreshToken).where(
                RefreshToken.refresh_token == token_data["refresh_token"]
            )
        )

        assert refresh_token is not None
        assert refresh_token.user_id == default_user.unique_id
        assert refresh_token.exp == token_data["refresh_token_expires_at"]
        assert not refresh_token.used

    async def test_login_multiple_times_creates_multiple_refresh_tokens(
        self,
        client: AsyncClient,
        default_user: User,
        session: AsyncSession,
    ) -> None:
        """Test that multiple logins create multiple refresh tokens."""
        # First login
        response1 = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second login
        response2 = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )
        assert response2.status_code == status.HTTP_200_OK

        # Verify both refresh tokens exist
        token_count = await session.scalar(
            select(func.count()).where(RefreshToken.user_id == default_user.unique_id)
        )
        assert token_count == 2  # noqa: PLR2004
