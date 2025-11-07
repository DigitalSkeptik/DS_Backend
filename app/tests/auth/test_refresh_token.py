import time

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
class TestRefreshToken:
    """Comprehensive tests for refresh token functionality."""

    # POSITIVE TESTS

    async def test_refresh_token_with_valid_token(
        self,
        client: AsyncClient,
        default_user: User,
        session: AsyncSession,
    ) -> None:
        """Test successful token refresh with valid refresh token."""
        # First, login to get refresh token
        login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )
        login_data = login_response.json()
        original_refresh_token = login_data["refresh_token"]

        # Use refresh token to get new access token
        refresh_response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": original_refresh_token},
        )

        assert refresh_response.status_code == status.HTTP_200_OK
        refresh_data = refresh_response.json()

        # Verify new token structure
        assert refresh_data["token_type"] == "Bearer"
        assert "access_token" in refresh_data
        assert "expires_at" in refresh_data
        assert "refresh_token" in refresh_data
        assert "refresh_token_expires_at" in refresh_data

        # Verify new access token is valid
        token_payload = verify_jwt_token(refresh_data["access_token"])
        assert token_payload.sub == default_user.unique_id

    async def test_refresh_token_rotates_refresh_token(
        self,
        client: AsyncClient,
        default_user: User,
        session: AsyncSession,
    ) -> None:
        """Test that refresh token rotation works correctly."""
        # First, login to get refresh token
        login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )
        login_data = login_response.json()
        original_refresh_token = login_data["refresh_token"]

        # Use refresh token to get new tokens
        refresh_response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": original_refresh_token},
        )
        refresh_data = refresh_response.json()
        new_refresh_token = refresh_data["refresh_token"]

        # Verify original refresh token is marked as used
        original_token_db = await session.scalar(
            select(RefreshToken).where(
                RefreshToken.refresh_token == original_refresh_token
            )
        )
        assert original_token_db.used is True

        # Verify new refresh token exists and is not used
        new_token_db = await session.scalar(
            select(RefreshToken).where(RefreshToken.refresh_token == new_refresh_token)
        )
        assert new_token_db is not None
        assert new_token_db.used is False
        assert new_token_db.user_id == default_user.unique_id

    async def test_refresh_token_sets_new_cookie(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test that refresh token sets new HttpOnly cookie."""
        # First, login to get refresh token
        login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )
        login_data = login_response.json()

        # Use refresh token to get new tokens
        refresh_response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": login_data["refresh_token"]},
        )

        assert refresh_response.status_code == status.HTTP_200_OK

        # Check if new access_token cookie is set
        cookies = refresh_response.cookies
        assert "access_token" in cookies

    @freeze_time("2023-01-01")
    async def test_refresh_token_has_correct_expiry_times(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test that refresh token returns correct expiry times."""
        # First, login to get refresh token
        login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )
        login_data = login_response.json()

        # Use refresh token to get new tokens
        refresh_response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": login_data["refresh_token"]},
        )
        refresh_data = refresh_response.json()

        current_timestamp = int(time.time())

        # Verify access token expiry
        expected_access_expiry = (
            current_timestamp + get_settings().security.jwt_access_token_expire_secs
        )
        assert refresh_data["expires_at"] == expected_access_expiry

        # Verify refresh token expiry
        expected_refresh_expiry = (
            current_timestamp + get_settings().security.refresh_token_expire_secs
        )
        assert refresh_data["refresh_token_expires_at"] == expected_refresh_expiry

    # NEGATIVE TESTS

    async def test_refresh_token_with_nonexistent_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test refresh with non-existent token returns 404."""
        response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": "nonexistent_token"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": api_messages.REFRESH_TOKEN_NOT_FOUND}

    async def test_refresh_token_with_expired_token(
        self,
        client: AsyncClient,
        default_user: User,
        session: AsyncSession,
    ) -> None:
        """Test refresh with expired token returns 400."""
        # Create an expired refresh token directly in database
        expired_time = int(time.time()) - 3600  # 1 hour ago
        expired_token = RefreshToken(
            user_id=default_user.unique_id,
            refresh_token="expired_token",
            exp=expired_time,
            used=False,
        )
        session.add(expired_token)
        await session.commit()

        response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": "expired_token"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": api_messages.REFRESH_TOKEN_EXPIRED}

    async def test_refresh_token_with_used_token(
        self,
        client: AsyncClient,
        default_user: User,
        session: AsyncSession,
    ) -> None:
        """Test refresh with already used token returns 400."""
        # Create a used refresh token directly in database
        used_token = RefreshToken(
            user_id=default_user.unique_id,
            refresh_token="used_token",
            exp=int(time.time()) + 3600,  # Not expired
            used=True,
        )
        session.add(used_token)
        await session.commit()

        response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": "used_token"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": api_messages.REFRESH_TOKEN_ALREADY_USED}

    async def test_refresh_token_with_empty_request(
        self,
        client: AsyncClient,
    ) -> None:
        """Test refresh with empty request returns 422."""
        response = await client.post(
            app.url_path_for("refresh_token"),
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_refresh_token_with_missing_field(
        self,
        client: AsyncClient,
    ) -> None:
        """Test refresh with missing refresh_token field returns 422."""
        response = await client.post(
            app.url_path_for("refresh_token"),
            json={"other_field": "value"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # SECURITY TESTS

    async def test_refresh_token_prevents_reuse(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test that refresh tokens cannot be reused."""
        # First, login to get refresh token
        login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]

        # First use should succeed
        first_response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": refresh_token},
        )
        assert first_response.status_code == status.HTTP_200_OK

        # Second use should fail
        second_response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": refresh_token},
        )
        assert second_response.status_code == status.HTTP_400_BAD_REQUEST
        assert second_response.json() == {
            "detail": api_messages.REFRESH_TOKEN_ALREADY_USED
        }

    async def test_refresh_token_sql_injection_attempt(
        self,
        client: AsyncClient,
    ) -> None:
        """Test refresh token with SQL injection attempt is handled safely."""
        response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": "'; DROP TABLE refresh_token; --"},
        )

        # Should be treated as non-existent token, not cause server crash
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": api_messages.REFRESH_TOKEN_NOT_FOUND}

    async def test_refresh_token_very_long_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test refresh token with very long token value."""
        long_token = "a" * 1000

        response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": long_token},
        )

        # Should handle gracefully
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # DATABASE INTEGRATION TESTS

    async def test_refresh_token_creates_new_token_record(
        self,
        client: AsyncClient,
        default_user: User,
        session: AsyncSession,
    ) -> None:
        """Test that refresh creates new token record in database."""
        # First, login to get refresh token
        login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": TEST_USER_PASSWORD,
            },
        )
        login_data = login_response.json()

        # Count tokens before refresh
        initial_count = await session.scalar(
            select(func.count()).where(RefreshToken.user_id == default_user.unique_id)
        )

        # Use refresh token
        refresh_response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": login_data["refresh_token"]},
        )
        assert refresh_response.status_code == status.HTTP_200_OK

        # Count tokens after refresh
        final_count = await session.scalar(
            select(func.count()).where(RefreshToken.user_id == default_user.unique_id)
        )

        # Should have one more token (original marked as used, new one created)
        assert final_count == initial_count + 1

    async def test_refresh_token_with_deleted_user(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user_factory: callable,
    ) -> None:
        """Test refresh token with deleted user."""
        # Create user and login
        user = await test_user_factory(
            email="deletable@example.com", username="deletable", password="Password123!"
        )

        login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": user.email,
                "password": "Password123!",
            },
        )
        login_data = login_response.json()

        # Delete user (use delete_current_user function from api/endpoints/users.py)
        _ = await client.delete(
            app.url_path_for("delete_current_user"),
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )

        # Try to use refresh token
        refresh_response = await client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": login_data["refresh_token"]},
        )

        assert refresh_response.status_code == status.HTTP_404_NOT_FOUND
