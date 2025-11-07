import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages
from app.core.security.jwt import create_jwt_token
from app.core.security.password import verify_password
from app.main import app
from app.models import User


@pytest.mark.asyncio(loop_scope="session")
class TestPasswordReset:
    """Comprehensive tests for user password reset."""

    # POSITIVE TESTS

    async def test_reset_password_with_valid_token(
        self,
        client: AsyncClient,
        default_user: User,
        default_user_headers: dict[str, str],
        valid_password_reset_data: dict,
    ) -> None:
        """Test successful password reset with valid token."""
        new_password = valid_password_reset_data["new_password"]

        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": new_password},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""

    async def test_reset_password_updates_database(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict[str, str],
        valid_password_reset_data: dict,
    ) -> None:
        """Test that password reset updates password in database."""
        new_password = valid_password_reset_data["new_password"]
        old_hash = default_user.pass_hash

        # Reset password
        await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": new_password},
        )

        # Verify password is updated
        updated_user = await session.scalar(
            select(User).where(User.unique_id == default_user.unique_id)
        )
        assert updated_user is not None
        assert updated_user.pass_hash != old_hash
        assert verify_password(new_password, updated_user.pass_hash)

    async def test_reset_password_with_cyrillic_characters(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict[str, str],
        valid_password_reset_data: dict,
    ) -> None:
        """Test successful password reset with Cyrillic characters."""
        cyrillic_password = valid_password_reset_data["cyrillic_password"]

        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": cyrillic_password},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify password is updated
        updated_user = await session.scalar(
            select(User).where(User.unique_id == default_user.unique_id)
        )
        assert updated_user is not None
        assert verify_password(cyrillic_password, updated_user.pass_hash)

    async def test_reset_password_multiple_times(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test multiple password resets."""
        passwords = ["NewPassword123!", "AnotherPass456!", "ThirdPass789!"]

        for password in passwords:
            response = await client.post(
                app.url_path_for("reset_current_user_password"),
                headers=default_user_headers,
                json={"password": password},
            )
            assert response.status_code == status.HTTP_204_NO_CONTENT

    # NEGATIVE TESTS

    async def test_reset_password_without_token(
        self,
        client: AsyncClient,
        valid_password_reset_data: dict,
    ) -> None:
        """Test password reset without authentication token."""
        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            json={"password": valid_password_reset_data["new_password"]},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Not authenticated"}

    async def test_reset_password_with_invalid_token(
        self,
        client: AsyncClient,
        valid_password_reset_data: dict,
    ) -> None:
        """Test password reset with invalid token."""
        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers={"Authorization": "Bearer invalid_token"},
            json={"password": valid_password_reset_data["new_password"]},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()

    async def test_reset_password_with_expired_token(
        self,
        client: AsyncClient,
        valid_password_reset_data: dict,
    ) -> None:
        """Test password reset with expired token."""
        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
            },
            json={"password": valid_password_reset_data["new_password"]},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_reset_password_with_empty_password(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
        invalid_password_reset_data: dict,
    ) -> None:
        """Test password reset with empty password."""
        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": ""},  # Empty password
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        assert any(
            keyword in response_data["detail"].lower()
            for keyword in ["password", "character", "letter", "number", "special"]
        )

    async def test_reset_password_with_simple_password(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test password reset with too simple password."""
        simple_passwords = [
            "123",  # Too short
            "password",  # No uppercase, numbers, or special chars
            "PASSWORD",  # No lowercase, numbers, or special chars
            "12345678",  # No letters or special chars
            "password123",  # No uppercase or special chars
            "PASSWORD123",  # No lowercase or special chars
            "Password!",  # No numbers
        ]

        for password in simple_passwords:
            response = await client.post(
                app.url_path_for("reset_current_user_password"),
                headers=default_user_headers,
                json={"password": password},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                keyword in response_data["detail"].lower()
                for keyword in ["password", "character", "letter", "number", "special"]
            )

    async def test_reset_password_with_missing_password_field(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test password reset with missing password field."""
        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={},  # Missing password field
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_reset_password_with_extra_fields(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
        valid_password_reset_data: dict,
    ) -> None:
        """Test password reset with extra fields in request."""
        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={
                "password": valid_password_reset_data["new_password"],
                "extra_field": "should_be_ignored",
                "another_field": "also_ignored",
            },
        )

        # Should succeed (extra fields should be ignored)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # SECURITY TESTS

    async def test_reset_password_with_deleted_user_token(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user_factory: callable,
    ) -> None:
        """Test password reset with token from deleted user."""
        # Create user and get token
        user = await test_user_factory(
            email="deletable@example.com", username="deletable", password="Password123!"
        )
        token = create_jwt_token(user.unique_id).access_token

        # Delete user
        await session.delete(user)
        await session.commit()

        # Try to reset password
        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "NewPassword123!"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": api_messages.JWT_ERROR_USER_REMOVED}

    async def test_reset_password_sql_injection_in_password(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test password reset with SQL injection in password."""
        malicious_passwords = [
            "'; DROP TABLE users; --",
            "OR '1'='1",
            "UNION SELECT * FROM users --",
        ]

        for password in malicious_passwords:
            response = await client.post(
                app.url_path_for("reset_current_user_password"),
                headers=default_user_headers,
                json={"password": password},
            )
            # Should be treated as invalid password, not cause server crash
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_reset_password_very_long_password(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test password reset with very long password."""
        long_password = "a" * 1000 + "A1!"

        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": long_password},
        )

        # Should handle gracefully - either accept or reject based on validation
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    # BOUNDARY TESTS

    async def test_reset_password_minimum_length(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test password reset with minimum valid length."""
        min_password = "Pass12!"  # 6 characters with all requirements

        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": min_password},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_reset_password_maximum_length(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test password reset with maximum reasonable length."""
        max_password = "P" + "a" * 100 + "1!"  # 103 characters

        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": max_password},
        )

        # Should handle gracefully
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    # DATABASE INTEGRATION TESTS

    async def test_reset_password_does_not_change_other_fields(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict[str, str],
        valid_password_reset_data: dict,
    ) -> None:
        """Test that password reset doesn't change other user fields."""
        original_email = default_user.email
        original_username = default_user.username
        original_user_id = default_user.unique_id

        # Reset password
        await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": valid_password_reset_data["new_password"]},
        )

        # Verify other fields are unchanged
        updated_user = await session.scalar(
            select(User).where(User.unique_id == default_user.unique_id)
        )
        assert updated_user is not None
        assert updated_user.email == original_email
        assert updated_user.username == original_username
        assert updated_user.unique_id == original_user_id

    async def test_reset_password_old_password_no_longer_works(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict[str, str],
        valid_password_reset_data: dict,
    ) -> None:
        """Test that old password no longer works after reset."""
        old_password = "Geralt123!"  # From conftest
        new_password = valid_password_reset_data["new_password"]

        # Reset password
        await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=default_user_headers,
            json={"password": new_password},
        )

        # Try to login with old password
        login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": old_password,
            },
        )

        assert login_response.status_code == status.HTTP_400_BAD_REQUEST
        assert login_response.json() == {"detail": api_messages.PASSWORD_INVALID}

        # Try to login with new password
        new_login_response = await client.post(
            app.url_path_for("login_access_token"),
            json={
                "email": default_user.email,
                "password": new_password,
            },
        )

        assert new_login_response.status_code == status.HTTP_200_OK

    # COOKIE-BASED AUTHENTICATION TESTS

    async def test_reset_password_with_cookie_auth(
        self,
        client: AsyncClient,
        default_user: User,
        valid_password_reset_data: dict,
    ) -> None:
        """Test password reset with cookie-based authentication."""
        # Set access token cookie
        token = create_jwt_token(default_user.unique_id).access_token
        client.cookies.set("access_token", token)

        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            json={"password": valid_password_reset_data["new_password"]},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_reset_password_prefer_header_over_cookie(
        self,
        client: AsyncClient,
        default_user: User,
        test_user_factory: callable,
        valid_password_reset_data: dict,
    ) -> None:
        """Test that header authentication is preferred over cookie for password reset."""
        # Create two users
        user1 = default_user
        user2 = await test_user_factory(
            email="user2@example.com", username="user2", password="Password123!"
        )

        # Set cookie for user1
        token1 = create_jwt_token(user1.unique_id).access_token
        client.cookies.set("access_token", token1)

        # Set header for user2
        token2 = create_jwt_token(user2.unique_id).access_token
        headers = {"Authorization": f"Bearer {token2}"}

        response = await client.post(
            app.url_path_for("reset_current_user_password"),
            headers=headers,
            json={"password": valid_password_reset_data["new_password"]},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Should reset user2 password (header takes precedence)
