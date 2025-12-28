import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Course, CourseTag, Module, Tag


@pytest.mark.asyncio(loop_scope="session")
class TestGetCourses:
    """Test suite for GET /api/v1/courses endpoint"""

    async def test_get_courses_empty_list(self, client: AsyncClient) -> None:
        """Test getting courses when database is empty"""
        response = await client.get("/api/v1/courses")
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_courses_with_data(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test getting courses with data in database"""
        # Create test courses
        course1 = Course(
            title="Test Course 1",
            description="Description 1",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        course2 = Course(
            title="Test Course 2",
            description="Description 2",
            price=2000,
            img_id="img2",
            is_active=True,
        )
        session.add_all([course1, course2])
        await session.commit()

        response = await client.get("/api/v1/courses")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] in ["Test Course 1", "Test Course 2"]
        assert data[1]["title"] in ["Test Course 1", "Test Course 2"]

    async def test_get_courses_only_active(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that only active courses are returned"""
        active_course = Course(
            title="Active Course",
            description="Active",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        inactive_course = Course(
            title="Inactive Course",
            description="Inactive",
            price=2000,
            img_id="img2",
            is_active=False,
        )
        session.add_all([active_course, inactive_course])
        await session.commit()

        response = await client.get("/api/v1/courses")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Active Course"

    async def test_get_courses_with_pagination(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test pagination with skip and limit parameters"""
        # Create 5 courses
        for i in range(5):
            course = Course(
                title=f"Course {i}",
                description=f"Description {i}",
                price=1000 * (i + 1),
                img_id=f"img{i}",
                is_active=True,
            )
            session.add(course)
        await session.commit()

        # Test skip=0, limit=2
        response = await client.get("/api/v1/courses?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test skip=2, limit=2
        response = await client.get("/api/v1/courses?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test skip=4, limit=2 (only 1 remaining)
        response = await client.get("/api/v1/courses?skip=4&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    async def test_get_courses_with_modules_count(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that modules_count is correctly calculated"""
        course = Course(
            title="Course with Modules",
            description="Description",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Add 3 modules
        for i in range(3):
            module = Module(
                course_id=course.unique_id,
                title=f"Module {i}",
                description=f"Module Description {i}",
                position=i,
            )
            session.add(module)
        await session.commit()

        response = await client.get("/api/v1/courses")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["modules_count"] == 3

    async def test_get_courses_with_tags(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that course tags are included in response"""
        course = Course(
            title="Course with Tags",
            description="Description",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Create tags
        tag1 = Tag(content="Python")
        tag2 = Tag(content="FastAPI")
        session.add_all([tag1, tag2])
        await session.flush()

        # Link tags to course
        course_tag1 = CourseTag(course_id=course.unique_id, tag_id=tag1.unique_id)
        course_tag2 = CourseTag(course_id=course.unique_id, tag_id=tag2.unique_id)
        session.add_all([course_tag1, course_tag2])
        await session.commit()

        response = await client.get("/api/v1/courses")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert len(data[0]["tags"]) == 2
        tag_contents = [tag["content"] for tag in data[0]["tags"]]
        assert "Python" in tag_contents
        assert "FastAPI" in tag_contents

    async def test_get_courses_invalid_skip(self, client: AsyncClient) -> None:
        """Test that negative skip parameter is rejected"""
        response = await client.get("/api/v1/courses?skip=-1")
        assert response.status_code == 422

    async def test_get_courses_invalid_limit(self, client: AsyncClient) -> None:
        """Test that invalid limit parameters are rejected"""
        # Limit too small
        response = await client.get("/api/v1/courses?limit=0")
        assert response.status_code == 422

        # Limit too large
        response = await client.get("/api/v1/courses?limit=1001")
        assert response.status_code == 422

    async def test_get_courses_response_structure(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that response has correct structure"""
        course = Course(
            title="Test Course",
            description="Test Description",
            price=1500,
            img_id="test_img",
            is_active=True,
        )
        session.add(course)
        await session.commit()

        response = await client.get("/api/v1/courses")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        course_data = data[0]
        assert "unique_id" in course_data
        assert "title" in course_data
        assert "description" in course_data
        assert "price" in course_data
        assert "img_id" in course_data
        assert "modules_count" in course_data
        assert "tags" in course_data
        assert "is_active" in course_data

        assert course_data["title"] == "Test Course"
        assert course_data["description"] == "Test Description"
        assert course_data["price"] == "1500"  # Price is returned as string
        assert course_data["img_id"] == "test_img"
        assert course_data["is_active"] is True


@pytest.mark.asyncio(loop_scope="session")
class TestGetCourseById:
    """Test suite for GET /api/v1/courses/{course_id} endpoint"""

    async def test_get_course_by_id_success(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test getting a course by ID successfully"""
        course = Course(
            title="Test Course",
            description="Test Description",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.commit()

        response = await client.get(f"/api/v1/courses/{course.unique_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["unique_id"] == course.unique_id
        assert data["title"] == "Test Course"
        assert data["description"] == "Test Description"
        assert data["price"] == "1000"  # Price is returned as string

    async def test_get_course_not_found(self, client: AsyncClient) -> None:
        """Test getting a non-existent course returns 404"""
        # Use a valid UUID format
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/courses/{fake_uuid}")
        assert response.status_code == 404
        assert "detail" in response.json()

    async def test_get_inactive_course_not_found(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that inactive courses return 404"""
        course = Course(
            title="Inactive Course",
            description="Description",
            price=1000,
            img_id="img1",
            is_active=False,
        )
        session.add(course)
        await session.commit()

        response = await client.get(f"/api/v1/courses/{course.unique_id}")
        assert response.status_code == 404

    async def test_get_course_with_modules(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that course modules are included and sorted by position"""
        course = Course(
            title="Course with Modules",
            description="Description",
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

        response = await client.get(f"/api/v1/courses/{course.unique_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["modules"]) == 3
        # Check modules are sorted by position
        assert data["modules"][0]["title"] == "Module 1"
        assert data["modules"][1]["title"] == "Module 2"
        assert data["modules"][2]["title"] == "Module 3"

    async def test_get_course_with_tags(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that course tags are included in detail response"""
        course = Course(
            title="Course with Tags",
            description="Description",
            price=1000,
            img_id="img1",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        tag = Tag(content="Python")
        session.add(tag)
        await session.flush()

        course_tag = CourseTag(course_id=course.unique_id, tag_id=tag.unique_id)
        session.add(course_tag)
        await session.commit()

        response = await client.get(f"/api/v1/courses/{course.unique_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tags"]) == 1
        assert data["tags"][0]["content"] == "Python"

    async def test_get_course_response_structure(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that course detail response has correct structure"""
        course = Course(
            title="Test Course",
            description="Test Description",
            price=1500,
            img_id="test_img",
            is_active=True,
        )
        session.add(course)
        await session.commit()

        response = await client.get(f"/api/v1/courses/{course.unique_id}")
        assert response.status_code == 200
        data = response.json()

        assert "unique_id" in data
        assert "title" in data
        assert "description" in data
        assert "price" in data
        assert "img_id" in data
        assert "modules" in data
        assert "tags" in data
        assert "is_active" in data

        assert isinstance(data["modules"], list)
        assert isinstance(data["tags"], list)
