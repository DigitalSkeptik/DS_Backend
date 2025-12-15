from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import AnswerOption, Question, Test, User
from app.schemas.admin_requests import (
    AnswerOptionCreateRequest,
    AnswerOptionUpdateRequest,
    QuestionCreateRequest,
    QuestionUpdateRequest,
)
from app.schemas.admin_responses import (
    AdminAnswerOptionResponse,
    AdminQuestionResponse,
)

router = APIRouter()

QUESTION_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Question or test not found",
        "content": {
            "application/json": {
                "examples": {
                    "question not found": {
                        "summary": "Question not found",
                        "value": {"detail": api_messages.QUESTION_NOT_FOUND},
                    },
                    "test not found": {
                        "summary": "Test not found",
                        "value": {"detail": api_messages.TEST_NOT_FOUND},
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
                    "question has answers": {
                        "summary": "Cannot delete question with answer options",
                        "value": {"detail": api_messages.QUESTION_HAS_ANSWERS},
                    },
                }
            }
        },
    },
}

ANSWER_OPTION_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Answer option or question not found",
        "content": {
            "application/json": {
                "examples": {
                    "answer option not found": {
                        "summary": "Answer option not found",
                        "value": {"detail": api_messages.ANSWER_OPTION_NOT_FOUND},
                    },
                    "question not found": {
                        "summary": "Question not found",
                        "value": {"detail": api_messages.QUESTION_NOT_FOUND},
                    },
                }
            }
        },
    },
}


@router.get(
    "/questions/{question_id}",
    response_model=AdminQuestionResponse,
    responses=QUESTION_RESPONSES,
    description="Get question by ID (admin view)",
)
async def get_question(
    question_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminQuestionResponse:
    """Get question with all details"""
    question = await session.scalar(
        select(Question)
        .options(
            selectinload(Question.test),
            selectinload(Question.answer_options),
        )
        .where(Question.unique_id == question_id)
    )

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.QUESTION_NOT_FOUND,
        )

    answer_options = [
        AdminAnswerOptionResponse(
            unique_id=option.unique_id,
            answer_text=option.answer_text,
            is_correct=option.is_correct,
            explanation=option.explanation,
        )
        for option in question.answer_options
    ]

    return AdminQuestionResponse(
        unique_id=question.unique_id,
        question_text=question.question_text,
        answer_options=answer_options,
    )


@router.get(
    "/tests/{test_id}/questions",
    response_model=list[AdminQuestionResponse],
    responses={404: {"description": "Test not found"}},
    description="Get all questions for a test (admin view)",
)
async def get_test_questions(
    test_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> list[AdminQuestionResponse]:
    """Get all questions for a test"""
    test = await session.scalar(select(Test).where(Test.unique_id == test_id))
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_NOT_FOUND,
        )

    result = await session.execute(
        select(Question)
        .options(selectinload(Question.answer_options))
        .where(Question.test_id == test_id)
        .order_by(Question.create_time)
    )
    questions = result.scalars().all()

    return [
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
        for question in questions
    ]


@router.post(
    "/tests/{test_id}/questions",
    response_model=AdminQuestionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Test not found"}},
    description="Create a new question for a test",
)
async def create_question(
    test_id: str,
    question_data: QuestionCreateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminQuestionResponse:
    """Create a new question"""
    test = await session.scalar(select(Test).where(Test.unique_id == test_id))
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_NOT_FOUND,
        )

    question = Question(
        test_id=test_id,
        question_text=question_data.question_text,
    )
    session.add(question)
    await session.commit()

    await session.refresh(question)
    return await get_question(question.unique_id, current_admin, session)


@router.put(
    "/questions/{question_id}",
    response_model=AdminQuestionResponse,
    responses=QUESTION_RESPONSES,
    description="Update a question",
)
async def update_question(
    question_id: str,
    question_data: QuestionUpdateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminQuestionResponse:
    """Update an existing question"""
    question = await session.scalar(
        select(Question).where(Question.unique_id == question_id)
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.QUESTION_NOT_FOUND,
        )

    update_data = question_data.model_dump(exclude_unset=True)
    if update_data:
        await session.execute(
            update(Question)
            .where(Question.unique_id == question_id)
            .values(**update_data)
        )

    await session.commit()
    return await get_question(question_id, current_admin, session)


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=QUESTION_RESPONSES,
    description="Delete a question",
)
async def delete_question(
    question_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> None:
    """Delete a question"""
    question = await session.scalar(
        select(Question)
        .options(selectinload(Question.answer_options))
        .where(Question.unique_id == question_id)
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.QUESTION_NOT_FOUND,
        )

    if question.answer_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.QUESTION_HAS_ANSWERS,
        )

    await session.execute(delete(Question).where(Question.unique_id == question_id))
    await session.commit()


@router.get(
    "/answer-options/{option_id}",
    response_model=AdminAnswerOptionResponse,
    responses=ANSWER_OPTION_RESPONSES,
    description="Get answer option by ID (admin view)",
)
async def get_answer_option(
    option_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminAnswerOptionResponse:
    """Get answer option"""
    option = await session.scalar(
        select(AnswerOption)
        .options(selectinload(AnswerOption.question))
        .where(AnswerOption.unique_id == option_id)
    )

    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.ANSWER_OPTION_NOT_FOUND,
        )

    return AdminAnswerOptionResponse(
        unique_id=option.unique_id,
        answer_text=option.answer_text,
        is_correct=option.is_correct,
        explanation=option.explanation,
    )


@router.post(
    "/questions/{question_id}/answer-options",
    response_model=AdminAnswerOptionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Question not found"}},
    description="Create a new answer option for a question",
)
async def create_answer_option(
    question_id: str,
    option_data: AnswerOptionCreateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminAnswerOptionResponse:
    """Create a new answer option"""
    question = await session.scalar(
        select(Question).where(Question.unique_id == question_id)
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.QUESTION_NOT_FOUND,
        )

    option = AnswerOption(
        question_id=question_id,
        answer_text=option_data.answer_text,
        is_correct=option_data.is_correct,
        explanation=option_data.explanation,
    )
    session.add(option)
    await session.commit()

    await session.refresh(option)
    return await get_answer_option(option.unique_id, current_admin, session)


@router.put(
    "/answer-options/{option_id}",
    response_model=AdminAnswerOptionResponse,
    responses=ANSWER_OPTION_RESPONSES,
    description="Update an answer option",
)
async def update_answer_option(
    option_id: str,
    option_data: AnswerOptionUpdateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminAnswerOptionResponse:
    """Update an existing answer option"""
    option = await session.scalar(
        select(AnswerOption).where(AnswerOption.unique_id == option_id)
    )
    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.ANSWER_OPTION_NOT_FOUND,
        )

    update_data = option_data.model_dump(exclude_unset=True)
    if update_data:
        await session.execute(
            update(AnswerOption)
            .where(AnswerOption.unique_id == option_id)
            .values(**update_data)
        )

    await session.commit()
    return await get_answer_option(option_id, current_admin, session)


@router.delete(
    "/answer-options/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=ANSWER_OPTION_RESPONSES,
    description="Delete an answer option",
)
async def delete_answer_option(
    option_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> None:
    """Delete an answer option"""
    option = await session.scalar(
        select(AnswerOption).where(AnswerOption.unique_id == option_id)
    )
    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.ANSWER_OPTION_NOT_FOUND,
        )

    await session.execute(
        delete(AnswerOption).where(AnswerOption.unique_id == option_id)
    )
    await session.commit()
