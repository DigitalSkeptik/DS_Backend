#!/usr/bin/env python
import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core import database_session
from app.core.security.password import get_password_hash
from app.models import (
    AnswerOption,
    Course,
    Module,
    PurchasedCourse,
    Question,
    Test,
    User,
)


async def seed() -> None:
    async with database_session.get_async_session() as session:
        # 1) Ensure demo user exists
        email = "demo@example.com"
        password_plain = "DemoPass123!"
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                username="demo",
                pass_hash=get_password_hash(password_plain),
            )
            session.add(user)
            # Flush to assign primary keys (unique_id)
            await session.flush()

        # 2) Ensure course exists
        course_title = "Python Basics (FREE)"
        course = await session.scalar(
            select(Course).where(Course.title == course_title)
        )
        if course is None:
            course = Course(
                title=course_title,
                description="Introductory Python course",
                price=Decimal("0.00"),
                is_active=True,
                img_id=None,
            )
            session.add(course)
            await session.flush()

        # 3) Ensure a module exists
        module_title = "Introduction"
        module = await session.scalar(
            select(Module).where(
                Module.title == module_title, Module.course_id == course.unique_id
            )
        )
        if module is None:
            module = Module(
                course_id=course.unique_id,
                title=module_title,
                description="Start here to learn the basics",
                content_json={},
                position=1,
            )
            session.add(module)
            await session.flush()

        # 4) Ensure a test with questions and answers exists
        test_title = "Intro Test"
        test = await session.scalar(
            select(Test).where(
                Test.module_id == module.unique_id, Test.title == test_title
            )
        )
        if test is None:
            test = Test(
                module_id=module.unique_id,
                title=test_title,
                description="Test your knowledge of Python basics",
            )
            session.add(test)
            await session.flush()

            # Question 1
            q1 = Question(
                test_id=test.unique_id,
                question_text="What is Python?",
            )
            session.add(q1)
            await session.flush()
            session.add_all(
                [
                    AnswerOption(
                        question_id=q1.unique_id,
                        answer_text="A high-level programming language",
                        is_correct=True,
                        explanation="Python is a high-level, interpreted programming language.",
                    ),
                    AnswerOption(
                        question_id=q1.unique_id,
                        answer_text="A snake",
                        is_correct=False,
                    ),
                    AnswerOption(
                        question_id=q1.unique_id,
                        answer_text="A database",
                        is_correct=False,
                    ),
                    AnswerOption(
                        question_id=q1.unique_id,
                        answer_text="An operating system",
                        is_correct=False,
                    ),
                ]
            )

            # Question 2
            q2 = Question(
                test_id=test.unique_id,
                question_text="Which file extension is used for Python modules?",
            )
            session.add(q2)
            await session.flush()
            session.add_all(
                [
                    AnswerOption(
                        question_id=q2.unique_id,
                        answer_text=".py",
                        is_correct=True,
                        explanation=".py is the standard file extension for Python modules.",
                    ),
                    AnswerOption(
                        question_id=q2.unique_id,
                        answer_text=".js",
                        is_correct=False,
                    ),
                    AnswerOption(
                        question_id=q2.unique_id,
                        answer_text=".java",
                        is_correct=False,
                    ),
                    AnswerOption(
                        question_id=q2.unique_id,
                        answer_text=".rb",
                        is_correct=False,
                    ),
                ]
            )

            # Question 3
            q3 = Question(
                test_id=test.unique_id,
                question_text="Which keyword defines a function in Python?",
            )
            session.add(q3)
            await session.flush()
            session.add_all(
                [
                    AnswerOption(
                        question_id=q3.unique_id,
                        answer_text="def",
                        is_correct=True,
                        explanation="Functions in Python are defined with the 'def' keyword.",
                    ),
                    AnswerOption(
                        question_id=q3.unique_id,
                        answer_text="func",
                        is_correct=False,
                    ),
                    AnswerOption(
                        question_id=q3.unique_id,
                        answer_text="function",
                        is_correct=False,
                    ),
                    AnswerOption(
                        question_id=q3.unique_id,
                        answer_text="lambda",
                        is_correct=False,
                    ),
                ]
            )

        # 5) Ensure purchased course exists for the demo user
        purchase = await session.scalar(
            select(PurchasedCourse).where(
                PurchasedCourse.user_id == user.unique_id,
                PurchasedCourse.course_id == course.unique_id,
            )
        )
        if purchase is None:
            purchase = PurchasedCourse(
                user_id=user.unique_id,
                course_id=course.unique_id,
            )
            session.add(purchase)

        # Commit all changes
        await session.commit()

        # Console output for convenience
        print("Seed complete.")
        print(f"User email: {email}  password: {password_plain}")
        print(f"Course: {course.title} ({course.unique_id})")
        print(f"Module: {module.title} ({module.unique_id})")
        print(f"Test: {test.title} ({test.unique_id})")


async def main() -> None:
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
