from collections.abc import Callable
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages
from app.main import app
from app.models import User


@pytest.mark.asyncio(loop_scope="session")
class TestUserRegistration:
    """Comprehensive tests for user registration endpoint."""

    # POSITIVE TESTS

    async def test_register_user_with_duplicate_username_different_email(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user_factory: Callable[..., Any],
    ) -> None:
        """Test successful registration with duplicate username but different email."""
        # Create first user
        await test_user_factory(
            email="first@example.com", username="string", password="ValidPass123!"
        )

        # Register second user with same username but different email
        response = await client.post(
            app.url_path_for("register_new_user"),
            json={
                "email": "user@example.com",
                "password": "String123!",
                "username": "string",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert "unique_id" in response_data
        assert response_data["email"] == "user@example.com"
        assert response_data["username"] == "string"
        assert "pass_hash" not in response_data  # Password should not be exposed

    async def test_register_user_with_all_valid_fields(
        self,
        client: AsyncClient,
        valid_registration_data: dict[str, Any],
    ) -> None:
        """Test successful registration with all valid fields."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=valid_registration_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert "unique_id" in response_data
        assert response_data["email"] == valid_registration_data["email"]
        assert response_data["username"] == valid_registration_data["username"]
        assert "pass_hash" not in response_data  # Password should not be exposed

    async def test_register_user_with_cyrillic_password(
        self,
        client: AsyncClient,
    ) -> None:
        """Test successful registration with Cyrillic characters in password."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json={
                "email": "user@example.com",
                "password": "Пароль123!",
                "username": "name",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert "unique_id" in response_data
        assert response_data["email"] == "user@example.com"
        assert response_data["username"] == "name"
        assert "pass_hash" not in response_data

    async def test_register_user_with_cyrillic_username(
        self,
        client: AsyncClient,
    ) -> None:
        """Test successful registration with Cyrillic characters in username."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json={
                "email": "user@example.com",
                "password": "Пароль123!",
                "username": "имя",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert "unique_id" in response_data
        assert response_data["email"] == "user@example.com"
        assert response_data["username"] == "имя"
        assert "pass_hash" not in response_data

    # NEGATIVE TESTS

    async def test_register_user_with_existing_email(
        self,
        client: AsyncClient,
        test_user_factory: Callable[..., Any],
    ) -> None:
        """Test registration with already existing email returns 400."""
        await test_user_factory(
            email="user@example.com", username="existing_user", password="ValidPass123!"
        )

        response = await client.post(
            app.url_path_for("register_new_user"),
            json={
                "email": "user@example.com",
                "password": "String123!",
                "username": "string",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": api_messages.EMAIL_ADDRESS_ALREADY_USED}

    async def test_register_user_missing_email(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with missing email returns 422."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["missing_email"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "email" in str(response.json())

    async def test_register_user_missing_username(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with missing username returns 422."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["missing_username"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "username" in str(response.json())

    async def test_register_user_missing_password(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with missing password returns 422."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["missing_password"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "password" in str(response.json())

    async def test_register_user_invalid_email_format(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with invalid email format returns 422."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["invalid_email"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "email" in str(response.json())

    async def test_register_user_simple_password(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with too simple password returns 422."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["simple_password"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        assert any(
            keyword in response_data["detail"].lower()
            for keyword in ["password", "character", "letter", "number", "special"]
        )

    async def test_register_user_empty_body(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with empty request body returns 422."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["empty_body"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data

    # SECURITY TESTS

    async def test_register_password_not_exposed_in_response(
        self,
        client: AsyncClient,
        valid_registration_data: dict[str, Any],
    ) -> None:
        """Test that password is not exposed in registration response."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=valid_registration_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert "pass_hash" not in response_data
        assert "password" not in response_data
        assert valid_registration_data["password"] not in str(response_data)

    async def test_register_sql_injection_in_email(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test SQL injection attempt in email field is handled safely."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["sql_injection_email"],
        )

        # Should be treated as invalid email, not cause server crash
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "email" in str(response.json())

    async def test_register_very_long_field_values(
        self,
        client: AsyncClient,
    ) -> None:
        """Test registration with very long field values."""
        long_email = "a" * 250 + "@example.com"
        long_username = "a" * 300
        long_password = "a" * 1000 + "A1!"

        response = await client.post(
            app.url_path_for("register_new_user"),
            json={
                "email": long_email,
                "password": long_password,
                "username": long_username,
            },
        )

        # Should handle long values gracefully
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        ]

    # BOUNDARY TESTS

    async def test_register_uppercase_email(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with uppercase email is handled correctly."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["uppercase_email"],
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert (
            response_data["email"] == "user@example.com"
        )  # Should be normalized to lowercase

    async def test_register_minimum_length_password(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with minimum valid password length."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["min_length_password"],
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert "unique_id" in response_data

    async def test_register_cyrillic_email(
        self,
        client: AsyncClient,
        invalid_registration_data: dict[str, Any],
    ) -> None:
        """Test registration with Cyrillic email returns 400."""
        response = await client.post(
            app.url_path_for("register_new_user"),
            json=invalid_registration_data["cyrillic_email"],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Should be treated as invalid email format

    # DATABASE INTEGRATION TESTS

    async def test_register_user_creates_record_in_db(
        self,
        client: AsyncClient,
        session: AsyncSession,
        valid_registration_data: dict[str, Any],
    ) -> None:
        """Test that successful registration creates user record in database."""
        await client.post(
            app.url_path_for("register_new_user"),
            json=valid_registration_data,
        )

        user_count = await session.scalar(
            select(func.count()).where(User.email == valid_registration_data["email"])
        )
        assert user_count == 1

    async def test_register_user_stores_hashed_password(
        self,
        client: AsyncClient,
        session: AsyncSession,
        valid_registration_data: dict[str, Any],
    ) -> None:
        """Test that password is properly hashed in database."""
        await client.post(
            app.url_path_for("register_new_user"),
            json=valid_registration_data,
        )

        user = await session.scalar(
            select(User).where(User.email == valid_registration_data["email"])
        )
        assert user is not None
        assert user.pass_hash != valid_registration_data["password"]
        assert len(user.pass_hash) > 50  # noqa: PLR2004
