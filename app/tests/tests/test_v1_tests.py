import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AnswerOption,
    CompletedModule,
    Course,
    Module,
    Question,
    Test,
    User,
)


@pytest.mark.asyncio(loop_scope="session")
class TestGetModuleTest:
    """Test suite for GET /api/v1/tests/module/{module_id}"""

    async def test_get_module_test_success(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test getting test for a module"""
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
            description="Test",
            position=0,
        )
        session.add(module)
        await session.flush()

        # Create test
        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test Description",
        )
        session.add(test)
        await session.flush()

        # Create questions
        question = Question(
            test_id=test.unique_id,
            question_text="What is 2+2?",
        )
        session.add(question)
        await session.flush()

        # Create answer options
        option1 = AnswerOption(
            question_id=question.unique_id,
            answer_text="3",
            is_correct=False,
        )
        option2 = AnswerOption(
            question_id=question.unique_id,
            answer_text="4",
            is_correct=True,
        )
        session.add_all([option1, option2])
        await session.commit()

        response = await client.get(
            f"/api/v1/tests/module/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Module Test"
        assert len(data["questions"]) == 1
        assert len(data["questions"][0]["answer_options"]) == 2

    async def test_get_module_test_not_found(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test getting test for module without test"""
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
        await session.commit()

        response = await client.get(
            f"/api/v1/tests/module/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 404

    async def test_get_module_test_no_access(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test getting test without course access"""
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
        await session.flush()

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.commit()

        response = await client.get(
            f"/api/v1/tests/module/{module.unique_id}",
            headers=default_user_headers,
        )
        assert response.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
class TestCheckSingleAnswer:
    """Test suite for POST /api/v1/tests/{test_id}/answer"""

    async def test_check_answer_correct(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test checking a correct answer"""
        # Setup test data
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

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.flush()

        question = Question(
            test_id=test.unique_id,
            question_text="What is 2+2?",
        )
        session.add(question)
        await session.flush()

        correct_option = AnswerOption(
            question_id=question.unique_id,
            answer_text="4",
            is_correct=True,
            explanation="2+2 equals 4",
        )
        wrong_option = AnswerOption(
            question_id=question.unique_id,
            answer_text="5",
            is_correct=False,
        )
        session.add_all([correct_option, wrong_option])
        await session.commit()

        response = await client.post(
            f"/api/v1/tests/{test.unique_id}/answer",
            json={
                "question_id": question.unique_id,
                "selected_option_id": correct_option.unique_id,
            },
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is True
        assert data["correct_option"]["explanation"] == "2+2 equals 4"

    async def test_check_answer_incorrect(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test checking an incorrect answer"""
        # Setup test data
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

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.flush()

        question = Question(
            test_id=test.unique_id,
            question_text="What is 2+2?",
        )
        session.add(question)
        await session.flush()

        correct_option = AnswerOption(
            question_id=question.unique_id,
            answer_text="4",
            is_correct=True,
        )
        wrong_option = AnswerOption(
            question_id=question.unique_id,
            answer_text="5",
            is_correct=False,
        )
        session.add_all([correct_option, wrong_option])
        await session.commit()

        response = await client.post(
            f"/api/v1/tests/{test.unique_id}/answer",
            json={
                "question_id": question.unique_id,
                "selected_option_id": wrong_option.unique_id,
            },
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is False
        assert data["correct_option"]["option_id"] == correct_option.unique_id

    async def test_check_answer_invalid_question(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test checking answer with invalid question"""
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

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.commit()

        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.post(
            f"/api/v1/tests/{test.unique_id}/answer",
            json={
                "question_id": fake_uuid,
                "selected_option_id": fake_uuid,
            },
            headers=default_user_headers,
        )
        assert response.status_code == 400


@pytest.mark.asyncio(loop_scope="session")
class TestSubmitTest:
    """Test suite for POST /api/v1/tests/{test_id}/submit"""

    async def test_submit_test_passing(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test submitting test with passing score"""
        # Setup test data
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

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.flush()

        # Create 2 questions
        q1 = Question(test_id=test.unique_id, question_text="Q1")
        q2 = Question(test_id=test.unique_id, question_text="Q2")
        session.add_all([q1, q2])
        await session.flush()

        # Add options
        q1_correct = AnswerOption(
            question_id=q1.unique_id, answer_text="Correct", is_correct=True
        )
        q1_wrong = AnswerOption(
            question_id=q1.unique_id, answer_text="Wrong", is_correct=False
        )
        q2_correct = AnswerOption(
            question_id=q2.unique_id, answer_text="Correct", is_correct=True
        )
        q2_wrong = AnswerOption(
            question_id=q2.unique_id, answer_text="Wrong", is_correct=False
        )
        session.add_all([q1_correct, q1_wrong, q2_correct, q2_wrong])
        await session.commit()

        # Submit with all correct answers
        response = await client.post(
            f"/api/v1/tests/{test.unique_id}/submit",
            json={
                "answers": [
                    {
                        "question_id": q1.unique_id,
                        "selected_option_id": q1_correct.unique_id,
                    },
                    {
                        "question_id": q2.unique_id,
                        "selected_option_id": q2_correct.unique_id,
                    },
                ]
            },
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is True
        assert data["score_percentage"] == 100.0
        assert data["module_completed"] is True

    async def test_submit_test_failing(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test submitting test with failing score"""
        # Setup test data
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

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.flush()

        # Create 2 questions
        q1 = Question(test_id=test.unique_id, question_text="Q1")
        q2 = Question(test_id=test.unique_id, question_text="Q2")
        session.add_all([q1, q2])
        await session.flush()

        # Add options
        q1_correct = AnswerOption(
            question_id=q1.unique_id, answer_text="Correct", is_correct=True
        )
        q1_wrong = AnswerOption(
            question_id=q1.unique_id, answer_text="Wrong", is_correct=False
        )
        q2_correct = AnswerOption(
            question_id=q2.unique_id, answer_text="Correct", is_correct=True
        )
        q2_wrong = AnswerOption(
            question_id=q2.unique_id, answer_text="Wrong", is_correct=False
        )
        session.add_all([q1_correct, q1_wrong, q2_correct, q2_wrong])
        await session.commit()

        # Submit with all wrong answers
        response = await client.post(
            f"/api/v1/tests/{test.unique_id}/submit",
            json={
                "answers": [
                    {
                        "question_id": q1.unique_id,
                        "selected_option_id": q1_wrong.unique_id,
                    },
                    {
                        "question_id": q2.unique_id,
                        "selected_option_id": q2_wrong.unique_id,
                    },
                ]
            },
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is False
        assert data["score_percentage"] == 0.0
        assert data["module_completed"] is False

    async def test_submit_test_missing_answers(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test submitting test with missing answers"""
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

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.flush()

        q1 = Question(test_id=test.unique_id, question_text="Q1")
        q2 = Question(test_id=test.unique_id, question_text="Q2")
        session.add_all([q1, q2])
        await session.flush()

        q1_correct = AnswerOption(
            question_id=q1.unique_id, answer_text="Correct", is_correct=True
        )
        session.add(q1_correct)
        await session.commit()

        # Submit with only one answer
        response = await client.post(
            f"/api/v1/tests/{test.unique_id}/submit",
            json={
                "answers": [
                    {
                        "question_id": q1.unique_id,
                        "selected_option_id": q1_correct.unique_id,
                    },
                ]
            },
            headers=default_user_headers,
        )
        assert response.status_code == 400


@pytest.mark.asyncio(loop_scope="session")
class TestGetModuleTestStatus:
    """Test suite for GET /api/v1/tests/module/{module_id}/status"""

    async def test_get_test_status_with_test(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test getting status for module with test"""
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

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.commit()

        response = await client.get(
            f"/api/v1/tests/module/{module.unique_id}/status",
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_test"] is True
        assert data["completed"] is False

    async def test_get_test_status_without_test(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user_headers: dict,
    ) -> None:
        """Test getting status for module without test"""
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

        response = await client.get(
            f"/api/v1/tests/module/{module.unique_id}/status",
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_test"] is False
        assert data["completed"] is False

    async def test_get_test_status_completed(
        self,
        client: AsyncClient,
        session: AsyncSession,
        default_user: User,
        default_user_headers: dict,
    ) -> None:
        """Test getting status for completed test"""
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

        test = Test(
            module_id=module.unique_id,
            title="Module Test",
            description="Test",
        )
        session.add(test)
        await session.flush()

        # Mark module as completed
        completed = CompletedModule(
            user_id=default_user.unique_id,
            module_id=module.unique_id,
        )
        session.add(completed)
        await session.commit()

        response = await client.get(
            f"/api/v1/tests/module/{module.unique_id}/status",
            headers=default_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_test"] is True
        assert data["completed"] is True
        assert data["completed_at"] is not None
