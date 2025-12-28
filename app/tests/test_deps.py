import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models import Course, Module, PurchasedCourse, User, UserRole


@pytest.mark.asyncio(loop_scope="session")
class TestDeps:
    """Test suite for dependency injection functions"""

    async def test_get_current_user_optional_no_token(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test get_current_user_optional returns None when no token"""
        from fastapi import Request

        # Create a mock request without token
        request = Request(scope={"type": "http", "headers": []})
        user = await deps.get_current_user_optional(request, session)
        assert user is None

    async def test_verify_course_access_with_purchase(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
    ) -> None:
        """Test verify_course_access returns True when user purchased course"""
        # Create a paid course
        course = Course(
            title="Test Course",
            description="Test",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Create a purchase
        purchase = PurchasedCourse(
            user_id=default_user.unique_id,
            course_id=course.unique_id,
        )
        session.add(purchase)
        await session.commit()

        # Verify access - should return True because user purchased the course
        has_access = await deps.verify_course_access(
            course.unique_id, default_user, session
        )
        assert has_access is True

    async def test_verify_course_access_free_course(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
    ) -> None:
        """Test verify_course_access returns True for free courses"""
        # Create a free course
        course = Course(
            title="Free Course",
            description="Test",
            price=0,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.commit()

        # Verify access
        has_access = await deps.verify_course_access(
            course.unique_id, default_user, session
        )
        assert has_access is True

    async def test_get_module_with_access_check_not_found(
        self,
        session: AsyncSession,
        default_user: User,
    ) -> None:
        """Test get_module_with_access_check raises 404 for non-existent module"""
        # Use a valid UUID format
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        with pytest.raises(HTTPException) as exc_info:
            await deps.get_module_with_access_check(fake_uuid, default_user, session)
        assert exc_info.value.status_code == 404

    async def test_get_module_with_access_check_no_access(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
    ) -> None:
        """Test get_module_with_access_check raises 403 when no access"""
        # Create a paid course
        course = Course(
            title="Paid Course",
            description="Test",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Create a module
        module = Module(
            course_id=course.unique_id,
            title="Test Module",
            description="Test",
            position=0,
        )
        session.add(module)
        await session.commit()

        # Try to access without purchase
        with pytest.raises(HTTPException) as exc_info:
            await deps.get_module_with_access_check(
                module.unique_id, default_user, session
            )
        assert exc_info.value.status_code == 403

    async def test_get_current_admin_user_success(
        self,
        session: AsyncSession,
    ) -> None:
        """Test get_current_admin_user returns user when admin"""
        # Create an admin user
        admin_user = User(
            email="admin@test.com",
            username="admin",
            pass_hash="hashed",
            role=UserRole.ADMIN,
        )
        session.add(admin_user)
        await session.commit()

        # Verify admin access
        result = await deps.get_current_admin_user(admin_user)
        assert result == admin_user
        assert result.role == UserRole.ADMIN

    async def test_get_current_admin_user_forbidden(
        self,
        client: AsyncClient,
        default_user: User,
    ) -> None:
        """Test get_current_admin_user raises 403 for non-admin"""
        with pytest.raises(HTTPException) as exc_info:
            await deps.get_current_admin_user(default_user)
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail
