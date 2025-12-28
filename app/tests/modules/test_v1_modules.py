import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CompletedModule,
    Course,
    Module,
    PurchasedCourse,
    Test,
    User,
)


@pytest.mark.asyncio(loop_scope="session")
class TestGetCourseModules:
    """Test suite for GET /api/v1/modules/courses/{course_id}"""

    async def test_get_course_modules_success(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test getting modules for a course"""
        # Create a course
        course = Course(
            title="Test Course",
            description="Test",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Create modules
        module1 = Module(
            course_id=course.unique_id,
            title="Module 1",
            description="First module",
            position=0,
        )
        module2 = Module(
            course_id=course.unique_id,
            title="Module 2",
            description="Second module",
            position=1,
        )
        session.add_all([module1, module2])
        await session.commit()

        response = await client.get(f"/api/v1/modules/courses/{course.unique_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Module 1"
        assert data[1]["title"] == "Module 2"

    async def test_get_course_modules_not_found(self, client: AsyncClient) -> None:
        """Test getting modules for non-existent course"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/modules/courses/{fake_uuid}")
        assert response.status_code == 404

    async def test_get_course_modules_inactive_course(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test getting modules for inactive course returns 404"""
        course = Course(
            title="Inactive Course",
            description="Test",
            price=1000,
            img_id="img1",
            is_active=False,
        )
        session.add(course)
        await session.commit()

        response = await client.get(f"/api/v1/modules/courses/{course.unique_id}")
        assert response.status_code == 404

    async def test_get_course_modules_empty(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test getting modules for course with no modules"""
        course = Course(
            title="Empty Course",
            description="Test",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.commit()

        response = await client.get(f"/api/v1/modules/courses/{course.unique_id}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_course_modules_sorted_by_position(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test modules are sorted by position"""
        course = Course(
            title="Test Course",
            description="Test",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Add modules in reverse order
        module3 = Module(
            course_id=course.unique_id,
            title="Module 3",
            description="Third",
            position=2,
        )
        module1 = Module(
            course_id=course.unique_id,
            title="Module 1",
            description="First",
            position=0,
        )
        module2 = Module(
            course_id=course.unique_id,
            title="Module 2",
            description="Second",
            position=1,
        )
        session.add_all([module3, module1, module2])
        await session.commit()

        response = await client.get(f"/api/v1/modules/courses/{course.unique_id}")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["title"] == "Module 1"
        assert data[1]["title"] == "Module 2"
        assert data[2]["title"] == "Module 3"


@pytest.mark.asyncio(loop_scope="session")
class TestGetModule:
    """Test suite for GET /api/v1/modules/{module_id}"""

    async def test_get_module_success(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test getting module with access"""
        # Create free course
        course = Course(
            title="Free Course",
            description="Test",
            price=0,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Create module
        module = Module(
            course_id=course.unique_id,
            title="Test Module",
            description="Test Description",
            content_json={"content": "test"},
            position=0,
        )
        session.add(module)
        await session.commit()

        response = await client.get(
            f"/api/v1/modules/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Module"
        assert data["content_json"] == {"content": "test"}
        assert data["is_completed"] is False
        assert data["has_test"] is False

    async def test_get_module_not_found(
        self,
        client: AsyncClient,
        default_user_headers: dict,
    ) -> None:
        """Test getting non-existent module"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/modules/{fake_uuid}",
            headers=default_user_headers,
        )
        assert response.status_code == 404

    async def test_get_module_inactive_course(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test getting module from inactive course"""
        course = Course(
            title="Inactive Course",
            description="Test",
            price=0,
            img_id="img1",
            is_active=False,
        )
        session.add(course)
        await session.flush()

        module = Module(
            course_id=course.unique_id,
            title="Test Module",
            description="Test",
            position=0,
        )
        session.add(module)
        await session.commit()

        response = await client.get(
            f"/api/v1/modules/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 404

    async def test_get_module_no_access(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test getting module without course purchase"""
        # Create paid course
        course = Course(
            title="Paid Course",
            description="Test",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        module = Module(
            course_id=course.unique_id,
            title="Test Module",
            description="Test",
            position=0,
        )
        session.add(module)
        await session.commit()

        response = await client.get(
            f"/api/v1/modules/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 403

    async def test_get_module_with_completion(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test getting completed module"""
        # Create free course
        course = Course(
            title="Free Course",
            description="Test",
            price=0,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        module = Module(
            course_id=course.unique_id,
            title="Test Module",
            description="Test",
            position=0,
        )
        session.add(module)
        await session.flush()

        # Mark as completed
        completed = CompletedModule(
            user_id=default_user.unique_id,
            module_id=module.unique_id,
        )
        session.add(completed)
        await session.commit()

        response = await client.get(
            f"/api/v1/modules/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_completed"] is True

    async def test_get_module_with_test(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test getting module with test"""
        # Create free course
        course = Course(
            title="Free Course",
            description="Test",
            price=0,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        module = Module(
            course_id=course.unique_id,
            title="Test Module",
            description="Test",
            position=0,
        )
        session.add(module)
        await session.flush()

        # Add test
        test = Test(
            module_id=module.unique_id,
            title="Test",
            description="Test",
        )
        session.add(test)
        await session.commit()

        response = await client.get(
            f"/api/v1/modules/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_test"] is True
        assert data["test_completed"] is False

    async def test_get_module_unauthorized(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        """Test getting module without authentication"""
        course = Course(
            title="Free Course",
            description="Test",
            price=0,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        module = Module(
            course_id=course.unique_id,
            title="Test Module",
            description="Test",
            position=0,
        )
        session.add(module)
        await session.commit()

        response = await client.get(f"/api/v1/modules/{module.unique_id}")
        assert response.status_code == 401

    async def test_get_module_with_purchased_course(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test getting module from purchased course"""
        # Create paid course
        course = Course(
            title="Paid Course",
            description="Test",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Purchase course
        purchase = PurchasedCourse(
            user_id=default_user.unique_id,
            course_id=course.unique_id,
        )
        session.add(purchase)
        await session.flush()

        module = Module(
            course_id=course.unique_id,
            title="Test Module",
            description="Test",
            content_json={"lesson": "data"},
            position=0,
        )
        session.add(module)
        await session.commit()

        response = await client.get(
            f"/api/v1/modules/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Module"
        assert data["content_json"] == {"lesson": "data"}
