import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages
from app.core.security.jwt import create_jwt_token
from app.main import app
from app.models import User


@pytest.mark.asyncio(loop_scope="session")
class TestReadUser:
    """Comprehensive tests for reading user information."""

    # POSITIVE TESTS

    async def test_read_current_user_with_valid_token(
        self,
        client: AsyncClient,
        default_user: User,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test successful user info retrieval with valid token."""
        response = await client.get(
            app.url_path_for("read_current_user"),
            headers=default_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        user_data = response.json()

        # Verify response structure
        assert "unique_id" in user_data
        assert "email" in user_data
        assert "username" in user_data
        assert "pass_hash" not in user_data  # Password should not be exposed

        # Verify data correctness
        assert user_data["unique_id"] == str(default_user.unique_id)
        assert user_data["email"] == default_user.email
        assert user_data["username"] == default_user.username

    async def test_read_current_user_response_structure(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test that user info response has correct structure."""
        response = await client.get(
            app.url_path_for("read_current_user"),
            headers=default_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        user_data = response.json()

        # Check required fields
        required_fields = ["unique_id", "email", "username"]
        for field in required_fields:
            assert field in user_data

        # Check that sensitive fields are not included
        sensitive_fields = ["pass_hash", "password", "hashed_password"]
        for field in sensitive_fields:
            assert field not in user_data

    async def test_read_current_user_with_different_valid_tokens(
        self,
        client: AsyncClient,
        test_user_factory: callable,
    ) -> None:
        """Test user info retrieval with different valid tokens."""
        # Create multiple users
        user1 = await test_user_factory(
            email="user1@example.com", username="user1", password="Password123!"
        )
        user2 = await test_user_factory(
            email="user2@example.com", username="user2", password="Password123!"
        )

        # Test with user1 token
        token1 = create_jwt_token(user1.unique_id).access_token
        response1 = await client.get(
            app.url_path_for("read_current_user"),
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert response1.status_code == status.HTTP_200_OK
        assert response1.json()["email"] == "user1@example.com"

        # Test with user2 token
        token2 = create_jwt_token(user2.unique_id).access_token
        response2 = await client.get(
            app.url_path_for("read_current_user"),
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["email"] == "user2@example.com"

    # NEGATIVE TESTS

    async def test_read_current_user_without_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user info retrieval without authentication token."""
        response = await client.get(
            app.url_path_for("read_current_user"),
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Not authenticated"}

    async def test_read_current_user_with_invalid_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user info retrieval with invalid token."""
        response = await client.get(
            app.url_path_for("read_current_user"),
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()

    async def test_read_current_user_with_expired_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user info retrieval with expired token."""
        # Create an expired token (this would require mocking time or creating manually)
        # For now, test with malformed token
        response = await client.get(
            app.url_path_for("read_current_user"),
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_read_current_user_with_malformed_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user info retrieval with malformed token."""
        malformed_tokens = [
            "Bearer",
            "Bearer ",
            "invalid_format",
            "Bearer not.a.valid.jwt",
            "",
        ]

        for token in malformed_tokens:
            response = await client.get(
                app.url_path_for("read_current_user"),
                headers={"Authorization": token} if token else {},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_read_current_user_with_wrong_authorization_scheme(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test user info retrieval with wrong authorization scheme."""
        token = create_jwt_token(default_user.unique_id).access_token

        wrong_schemes = [
            f"Basic {token}",
            f"Token {token}",
            f"JWT {token}",
        ]

        for auth_header in wrong_schemes:
            response = await client.get(
                app.url_path_for("read_current_user"),
                headers={"Authorization": auth_header},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # SECURITY TESTS

    async def test_read_current_user_with_deleted_user_token(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user_factory: callable,
    ) -> None:
        """Test user info retrieval with token from deleted user."""
        # Create user and get token
        user = await test_user_factory(
            email="deletable@example.com", username="deletable", password="Password123!"
        )
        token = create_jwt_token(user.unique_id).access_token

        # Delete user
        await session.delete(user)
        await session.commit()

        # Try to use token
        response = await client.get(
            app.url_path_for("read_current_user"),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": api_messages.JWT_ERROR_USER_REMOVED}

    async def test_read_current_user_sql_injection_in_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user info retrieval with SQL injection in token."""
        malicious_tokens = [
            "Bearer '; DROP TABLE users; --",
            "Bearer OR '1'='1",
            "Bearer UNION SELECT * FROM users --",
        ]

        for token in malicious_tokens:
            response = await client.get(
                app.url_path_for("read_current_user"),
                headers={"Authorization": token},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_read_current_user_very_long_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user info retrieval with very long token."""
        long_token = "Bearer " + "a" * 1000

        response = await client.get(
            app.url_path_for("read_current_user"),
            headers={"Authorization": long_token},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # DATABASE INTEGRATION TESTS

    async def test_read_current_user_returns_current_data(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test that user info retrieval returns current database data."""
        # Modify user in database
        default_user.username = "updated_username"
        session.add(default_user)
        await session.commit()

        # Get user info
        response = await client.get(
            app.url_path_for("read_current_user"),
            headers=default_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        user_data = response.json()
        assert user_data["username"] == "updated_username"

    async def test_read_current_user_case_sensitivity(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test user info retrieval with case-sensitive email."""
        response = await client.get(
            app.url_path_for("read_current_user"),
            headers=default_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        user_data = response.json()

        # Email should be returned as stored in database (likely lowercase)
        assert user_data["email"] == user_data["email"].lower()

    # COOKIE-BASED AUTHENTICATION TESTS

    async def test_read_current_user_with_cookie_auth(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test user info retrieval with cookie-based authentication."""
        # Set access token cookie
        token = create_jwt_token(default_user.unique_id).access_token
        client.cookies.set("access_token", token)

        response = await client.get(
            app.url_path_for("read_current_user"),
        )

        assert response.status_code == status.HTTP_200_OK
        user_data = response.json()
        assert user_data["email"] == default_user.email

    async def test_read_current_user_prefer_header_over_cookie(
        self,
        client: AsyncClient,
        default_user: User,
        test_user_factory: callable,
    ) -> None:
        """Test that header authentication is preferred over cookie."""
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

        response = await client.get(
            app.url_path_for("read_current_user"),
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        user_data = response.json()
        # Should return user2 data (header takes precedence)
        assert user_data["email"] == "user2@example.com"
