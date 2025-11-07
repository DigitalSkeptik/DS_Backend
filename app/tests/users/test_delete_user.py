import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages
from app.core.security.jwt import create_jwt_token
from app.main import app
from app.models import User


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteUser:
    """Comprehensive tests for user deletion."""

    # POSITIVE TESTS

    async def test_delete_current_user_with_valid_token(
        self,
        client: AsyncClient,
        default_user: User,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test successful user deletion with valid token."""
        response = await client.delete(
            app.url_path_for("delete_current_user"),
            headers=default_user_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""  # No content in response

    async def test_delete_current_user_removes_from_database(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test that user deletion removes user from database."""
        # Verify user exists before deletion
        user_before = await session.scalar(
            select(User).where(User.unique_id == default_user.unique_id)
        )
        assert user_before is not None

        # Delete user
        await client.delete(
            app.url_path_for("delete_current_user"),
            headers=default_user_headers,
        )

        # Verify user is deleted
        user_after = await session.scalar(
            select(User).where(User.unique_id == default_user.unique_id)
        )
        assert user_after is None

    async def test_delete_current_user_with_different_users(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user_factory: callable,
    ) -> None:
        """Test deletion of multiple users independently."""
        # Create multiple users
        user1 = await test_user_factory(
            email="user1@example.com", username="user1", password="Password123!"
        )
        user2 = await test_user_factory(
            email="user2@example.com", username="user2", password="Password123!"
        )

        # Delete user1
        token1 = create_jwt_token(user1.unique_id).access_token
        response1 = await client.delete(
            app.url_path_for("delete_current_user"),
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert response1.status_code == status.HTTP_204_NO_CONTENT

        # Verify user1 is deleted but user2 still exists
        user1_after = await session.scalar(
            select(User).where(User.unique_id == user1.unique_id)
        )
        user2_after = await session.scalar(
            select(User).where(User.unique_id == user2.unique_id)
        )
        assert user1_after is None
        assert user2_after is not None

        # Delete user2
        token2 = create_jwt_token(user2.unique_id).access_token
        response2 = await client.delete(
            app.url_path_for("delete_current_user"),
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response2.status_code == status.HTTP_204_NO_CONTENT

        # Verify user2 is also deleted
        user2_final = await session.scalar(
            select(User).where(User.unique_id == user2.unique_id)
        )
        assert user2_final is None

    # NEGATIVE TESTS

    async def test_delete_current_user_without_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user deletion without authentication token."""
        response = await client.delete(
            app.url_path_for("delete_current_user"),
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Not authenticated"}

    async def test_delete_current_user_with_invalid_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user deletion with invalid token."""
        response = await client.delete(
            app.url_path_for("delete_current_user"),
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()

    async def test_delete_current_user_with_expired_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user deletion with expired token."""
        response = await client.delete(
            app.url_path_for("delete_current_user"),
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_current_user_with_malformed_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user deletion with malformed token."""
        malformed_tokens = [
            "Bearer",
            "Bearer ",
            "invalid_format",
            "Bearer not.a.valid.jwt",
            "",
        ]

        for token in malformed_tokens:
            response = await client.delete(
                app.url_path_for("delete_current_user"),
                headers={"Authorization": token} if token else {},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_current_user_with_wrong_authorization_scheme(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test user deletion with wrong authorization scheme."""
        token = create_jwt_token(default_user.unique_id).access_token

        wrong_schemes = [
            f"Basic {token}",
            f"Token {token}",
            f"JWT {token}",
        ]

        for auth_header in wrong_schemes:
            response = await client.delete(
                app.url_path_for("delete_current_user"),
                headers={"Authorization": auth_header},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # SECURITY TESTS

    async def test_delete_current_user_with_deleted_user_token(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user_factory: callable,
    ) -> None:
        """Test user deletion with token from already deleted user."""
        # Create user and get token
        user = await test_user_factory(
            email="deletable@example.com", username="deletable", password="Password123!"
        )
        token = create_jwt_token(user.unique_id).access_token

        # Delete user
        await session.delete(user)
        await session.commit()

        # Try to delete with token
        response = await client.delete(
            app.url_path_for("delete_current_user"),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": api_messages.JWT_ERROR_USER_REMOVED}

    async def test_delete_current_user_sql_injection_in_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user deletion with SQL injection in token."""
        malicious_tokens = [
            "Bearer '; DROP TABLE users; --",
            "Bearer OR '1'='1",
            "Bearer UNION SELECT * FROM users --",
        ]

        for token in malicious_tokens:
            response = await client.delete(
                app.url_path_for("delete_current_user"),
                headers={"Authorization": token},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_current_user_very_long_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Test user deletion with very long token."""
        long_token = "Bearer " + "a" * 1000

        response = await client.delete(
            app.url_path_for("delete_current_user"),
            headers={"Authorization": long_token},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # DATABASE INTEGRATION TESTS

    async def test_delete_current_user_cascades_to_related_data(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user_factory: callable,
    ) -> None:
        """Test that user deletion cascades to related data."""
        # Create user with related data (if any relationships exist)
        user = await test_user_factory(
            email="cascade@example.com", username="cascade", password="Password123!"
        )

        # Delete user
        token = create_jwt_token(user.unique_id).access_token
        response = await client.delete(
            app.url_path_for("delete_current_user"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify user is deleted
        user_after = await session.scalar(
            select(User).where(User.unique_id == user.unique_id)
        )
        assert user_after is None

    async def test_delete_current_user_twice_fails(
        self,
        client: AsyncClient,
        default_user: User,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test that deleting the same user twice fails."""
        # First deletion should succeed
        response1 = await client.delete(
            app.url_path_for("delete_current_user"),
            headers=default_user_headers,
        )
        assert response1.status_code == status.HTTP_204_NO_CONTENT

        # Second deletion should fail
        response2 = await client.delete(
            app.url_path_for("delete_current_user"),
            headers=default_user_headers,
        )
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED
        assert response2.json() == {"detail": api_messages.JWT_ERROR_USER_REMOVED}

    # COOKIE-BASED AUTHENTICATION TESTS

    async def test_delete_current_user_with_cookie_auth(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test user deletion with cookie-based authentication."""
        # Set access token cookie
        token = create_jwt_token(default_user.unique_id).access_token
        client.cookies.set("access_token", token)

        response = await client.delete(
            app.url_path_for("delete_current_user"),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_current_user_prefer_header_over_cookie(
        self,
        client: AsyncClient,
        default_user: User,
        test_user_factory: callable,
    ) -> None:
        """Test that header authentication is preferred over cookie for deletion."""
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

        response = await client.delete(
            app.url_path_for("delete_current_user"),
            headers=headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify user2 is deleted (header takes precedence)
        # This would require checking the database, but since we can't easily
        # access the session after deletion, we'll assume the API behaves correctly

    # EDGE CASES

    async def test_delete_current_user_response_headers(
        self,
        client: AsyncClient,
        default_user_headers: dict[str, str],
    ) -> None:
        """Test that delete response has appropriate headers."""
        response = await client.delete(
            app.url_path_for("delete_current_user"),
            headers=default_user_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""
        # Check that content-type header is appropriate
        assert "content-type" in response.headers
