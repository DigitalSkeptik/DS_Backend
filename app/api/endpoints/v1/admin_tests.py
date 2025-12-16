from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import Module, Question, Test, User
from app.schemas.admin_requests import TestCreateRequest, TestUpdateRequest
from app.schemas.admin_responses import (
    AdminAnswerOptionResponse,
    AdminQuestionResponse,
    AdminTestResponse,
)

router = APIRouter()

TEST_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Test or module not found",
        "content": {
            "application/json": {
                "examples": {
                    "test not found": {
                        "summary": "Test not found",
                        "value": {"detail": api_messages.TEST_NOT_FOUND},
                    },
                    "module not found": {
                        "summary": "Module not found",
                        "value": {"detail": api_messages.MODULE_NOT_FOUND},
                    },
                }
            }
        },
    },
    400: {
        "description": "Bad request",
        "content": {
            "application/json": {
                "examples": {
                    "test has questions": {
                        "summary": "Cannot delete test with questions",
                        "value": {"detail": api_messages.TEST_HAS_QUESTIONS},
                    },
                    "module already has test": {
                        "summary": "Module already has a test",
                        "value": {"detail": "Module already has a test"},
                    },
                }
            }
        },
    },
}


@router.get(
    "/tests/{test_id}",
    response_model=AdminTestResponse,
    responses=TEST_RESPONSES,
    description="Get test by ID (admin view)",
)
async def get_test(
    test_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminTestResponse:
    """Get test with all details"""
    test = await session.scalar(
        select(Test)
        .options(
            selectinload(Test.module),
            selectinload(Test.questions).selectinload(Question.answer_options),
        )
        .where(Test.unique_id == test_id)
    )

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_NOT_FOUND,
        )

    questions = [
        AdminQuestionResponse(
            unique_id=question.unique_id,
            question_text=question.question_text,
            answer_options=[
                AdminAnswerOptionResponse(
                    unique_id=option.unique_id,
                    answer_text=option.answer_text,
                    is_correct=option.is_correct,
                    explanation=option.explanation,
                )
                for option in question.answer_options
            ],
        )
        for question in test.questions
    ]

    return AdminTestResponse(
        unique_id=test.unique_id,
        module_id=test.module_id,
        title=test.title,
        description=test.description,
        questions=questions,
        create_time=test.create_time,
        update_time=test.update_time,
    )


@router.get(
    "/modules/{module_id}/test",
    response_model=AdminTestResponse,
    responses={404: {"description": "Module not found or has no test"}},
    description="Get test for a module (admin view)",
)
async def get_module_test(
    module_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminTestResponse:
    """Get test for a module"""
    test = await session.scalar(
        select(Test)
        .options(
            selectinload(Test.questions).selectinload(Question.answer_options),
        )
        .where(Test.module_id == module_id)
    )

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module has no test",
        )

    questions = [
        AdminQuestionResponse(
            unique_id=question.unique_id,
            question_text=question.question_text,
            answer_options=[
                AdminAnswerOptionResponse(
                    unique_id=option.unique_id,
                    answer_text=option.answer_text,
                    is_correct=option.is_correct,
                    explanation=option.explanation,
                )
                for option in question.answer_options
            ],
        )
        for question in test.questions
    ]

    return AdminTestResponse(
        unique_id=test.unique_id,
        module_id=test.module_id,
        title=test.title,
        description=test.description,
        questions=questions,
        create_time=test.create_time,
        update_time=test.update_time,
    )


@router.post(
    "/modules/{module_id}/test",
    response_model=AdminTestResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Module not found"},
        400: {
            "description": "Module already has a test. Although we technically support multiple tests per module, right now we only allow one."
        },
    },
    description="Create a new test for a module",
)
async def create_test(
    module_id: str,
    test_data: TestCreateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminTestResponse:
    """Create a new test"""
    module = await session.scalar(select(Module).where(Module.unique_id == module_id))
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.MODULE_NOT_FOUND,
        )

    existing_test = await session.scalar(
        select(Test).where(Test.module_id == module_id)
    )
    if existing_test:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Module already has a test",
        )

    test = Test(
        module_id=module_id,
        title=test_data.title,
        description=test_data.description,
    )
    session.add(test)
    await session.commit()

    await session.refresh(test)
    return await get_test(test.unique_id, current_admin, session)


@router.put(
    "/tests/{test_id}",
    response_model=AdminTestResponse,
    responses=TEST_RESPONSES,
    description="Update a test",
)
async def update_test(
    test_id: str,
    test_data: TestUpdateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminTestResponse:
    """Update an existing test"""
    test = await session.scalar(select(Test).where(Test.unique_id == test_id))
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_NOT_FOUND,
        )

    update_data = test_data.model_dump(exclude_unset=True)
    if update_data:
        await session.execute(
            update(Test).where(Test.unique_id == test_id).values(**update_data)
        )

    await session.commit()
    return await get_test(test_id, current_admin, session)


@router.delete(
    "/tests/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=TEST_RESPONSES,
    description="Delete a test",
)
async def delete_test(
    test_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> None:
    """Delete a test"""
    test = await session.scalar(
        select(Test)
        .options(selectinload(Test.questions))
        .where(Test.unique_id == test_id)
    )
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_NOT_FOUND,
        )

    if test.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.TEST_HAS_QUESTIONS,
        )

    await session.execute(delete(Test).where(Test.unique_id == test_id))
    await session.commit()
