import random
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import CompletedModule, Module, Question, Test, User
from app.schemas.requests import TestAnswerRequest, TestSubmissionRequest
from app.schemas.responses import (
    AnswerOptionResponse,
    CorrectAnswerResponse,
    ModuleTestStatusResponse,
    QuestionResponse,
    QuestionResultResponse,
    TestResponse,
    TestSubmissionResponse,
)

router = APIRouter()

TEST_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Test or module not found",
        "content": {
            "application/json": {
                "examples": {
                    "test not found": {
                        "summary": api_messages.TEST_NOT_FOUND,
                        "value": {"detail": api_messages.TEST_NOT_FOUND},
                    },
                    "module not found": {
                        "summary": api_messages.MODULE_NOT_FOUND,
                        "value": {"detail": api_messages.MODULE_NOT_FOUND},
                    },
                    "no test": {
                        "summary": api_messages.TEST_MODULE_HAS_NO_TEST,
                        "value": {"detail": api_messages.TEST_MODULE_HAS_NO_TEST},
                    },
                }
            }
        },
    },
    403: {
        "description": "Access denied",
        "content": {
            "application/json": {"example": {"detail": api_messages.TEST_ACCESS_DENIED}}
        },
    },
}

SUBMIT_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Invalid submission",
        "content": {
            "application/json": {
                "examples": {
                    "invalid submission": {
                        "summary": api_messages.TEST_INVALID_SUBMISSION,
                        "value": {"detail": api_messages.TEST_INVALID_SUBMISSION},
                    },
                    "invalid option": {
                        "summary": api_messages.TEST_INVALID_OPTION,
                        "value": {"detail": api_messages.TEST_INVALID_OPTION},
                    },
                }
            }
        },
    },
    404: {
        "description": "Test not found",
        "content": {
            "application/json": {"example": {"detail": api_messages.TEST_NOT_FOUND}}
        },
    },
    403: {
        "description": "Access denied",
        "content": {
            "application/json": {"example": {"detail": api_messages.TEST_ACCESS_DENIED}}
        },
    },
}

PASSING_THRESHOLD = 70


@router.get(
    "/module/{module_id}",
    response_model=TestResponse,
    responses=TEST_RESPONSES,
    description="Retrieve test for module with randomized questions",
)
async def get_module_test(
    module_id: str,
    module: Module = Depends(deps.get_module_with_access_check),
    session: AsyncSession = Depends(deps.get_session),
) -> TestResponse:
    # Load test with questions and answer options
    test = await session.scalar(
        select(Test)
        .options(selectinload(Test.questions).selectinload(Question.answer_options))
        .where(Test.module_id == module_id)
    )

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_MODULE_HAS_NO_TEST,
        )

    # Randomize question order
    questions = list(test.questions)
    random.shuffle(questions)

    # Build response (without is_correct and explanation)
    return TestResponse(
        test_id=test.unique_id,
        module_id=test.module_id,
        title=test.title,
        description=test.description,
        questions=[
            QuestionResponse(
                question_id=q.unique_id,
                question_text=q.question_text,
                answer_options=[
                    AnswerOptionResponse(
                        option_id=opt.unique_id, answer_text=opt.answer_text
                    )
                    for opt in q.answer_options
                ],
            )
            for q in questions
        ],
    )


@router.post(
    "/{test_id}/answer",
    response_model=QuestionResultResponse,
    responses=SUBMIT_RESPONSES,
    description="Validate a single answer and return correctness with explanation (stateless)",
)
async def check_single_answer(
    test_id: str,
    data: TestAnswerRequest,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> QuestionResultResponse:
    # Load test with related data
    test = await session.scalar(
        select(Test)
        .options(
            selectinload(Test.module).selectinload(Module.course),
            selectinload(Test.questions).selectinload(Question.answer_options),
        )
        .where(Test.unique_id == test_id)
    )
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_NOT_FOUND,
        )

    # Verify access
    has_access = await deps.verify_course_access(
        test.module.course_id, current_user, session
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_messages.TEST_ACCESS_DENIED,
        )

    # Validate that question belongs to this test
    question = next(
        (q for q in test.questions if q.unique_id == data.question_id), None
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.TEST_INVALID_SUBMISSION,
        )

    # Validate selected option belongs to this question
    selected_option = next(
        (o for o in question.answer_options if o.unique_id == data.selected_option_id),
        None,
    )
    if not selected_option:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.TEST_INVALID_OPTION,
        )

    # Find correct option
    correct_option = next((o for o in question.answer_options if o.is_correct), None)
    is_correct = bool(selected_option.is_correct)

    return QuestionResultResponse(
        question_id=question.unique_id,
        question_text=question.question_text,
        selected_option_id=data.selected_option_id,
        is_correct=is_correct,
        correct_option=CorrectAnswerResponse(
            option_id=correct_option.unique_id if correct_option else "",
            answer_text=correct_option.answer_text if correct_option else "",
            explanation=getattr(correct_option, "explanation", None)
            if correct_option
            else None,
        ),
    )


@router.post(
    "/{test_id}/submit",
    response_model=TestSubmissionResponse,
    responses=SUBMIT_RESPONSES,
    description="Submit test answers and get results",
)
async def submit_test(
    test_id: str,
    submission: TestSubmissionRequest,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> TestSubmissionResponse:
    # Load test with all related data
    test = await session.scalar(
        select(Test)
        .options(
            selectinload(Test.module).selectinload(Module.course),
            selectinload(Test.questions).selectinload(Question.answer_options),
        )
        .where(Test.unique_id == test_id)
    )

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=api_messages.TEST_NOT_FOUND
        )

    # Verify access to course
    has_access = await deps.verify_course_access(
        test.module.course_id, current_user, session
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_messages.TEST_ACCESS_DENIED,
        )

    # Validate submission
    question_ids = {q.unique_id for q in test.questions}
    submitted_ids = {ans.question_id for ans in submission.answers}

    if question_ids != submitted_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.TEST_INVALID_SUBMISSION,
        )

    # Build answer map for quick lookup
    answer_map = {ans.question_id: ans.selected_option_id for ans in submission.answers}

    # Score the test
    results = []
    correct_count = 0

    for question in test.questions:
        selected_id = answer_map[question.unique_id]

        # Find selected option and correct option
        selected_option = None
        correct_option = None

        for opt in question.answer_options:
            if opt.unique_id == selected_id:
                selected_option = opt
            if opt.is_correct:
                correct_option = opt

        if not selected_option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_messages.TEST_INVALID_OPTION,
            )

        is_correct = selected_option.is_correct
        if is_correct:
            correct_count += 1

        results.append(
            QuestionResultResponse(
                question_id=question.unique_id,
                question_text=question.question_text,
                selected_option_id=selected_id,
                is_correct=is_correct,
                correct_option=CorrectAnswerResponse(
                    option_id=correct_option.unique_id,
                    answer_text=correct_option.answer_text,
                    explanation=correct_option.explanation,
                ),
            )
        )

    # Calculate score
    total_questions = len(test.questions)
    score_percentage = (correct_count / total_questions) * 100
    passed = score_percentage >= PASSING_THRESHOLD

    # Mark module as completed if passed
    module_completed = False
    if passed:
        # Check if already completed
        existing = await session.scalar(
            select(CompletedModule).where(
                CompletedModule.user_id == current_user.unique_id,
                CompletedModule.module_id == test.module_id,
            )
        )

        if not existing:
            completed = CompletedModule(
                user_id=current_user.unique_id, module_id=test.module_id
            )
            session.add(completed)
            await session.commit()
            module_completed = True

    return TestSubmissionResponse(
        test_id=test_id,
        score_percentage=round(score_percentage, 2),
        passed=passed,
        passing_threshold=PASSING_THRESHOLD,
        total_questions=total_questions,
        correct_answers=correct_count,
        module_completed=module_completed,
        results=results,
    )


@router.get(
    "/module/{module_id}/status",
    response_model=ModuleTestStatusResponse,
    description="Check if user has completed module's test",
)
async def get_module_test_status(
    module_id: str,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> ModuleTestStatusResponse:
    # Check if module has a test
    test = await session.scalar(select(Test).where(Test.module_id == module_id))

    has_test = test is not None

    # Check completion
    completed_module = await session.scalar(
        select(CompletedModule).where(
            CompletedModule.user_id == current_user.unique_id,
            CompletedModule.module_id == module_id,
        )
    )

    return ModuleTestStatusResponse(
        module_id=module_id,
        has_test=has_test,
        completed=completed_module is not None,
        completed_at=completed_module.create_time if completed_module else None,
    )
