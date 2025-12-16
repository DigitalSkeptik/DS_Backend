from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import Course, Module, Question, Test, User
from app.schemas.admin_requests import (
    ModuleCreateRequest,
    ModuleReorderRequest,
    ModuleUpdateRequest,
)
from app.schemas.admin_responses import (
    AdminAnswerOptionResponse,
    AdminBulkOperationResponse,
    AdminModuleListResponse,
    AdminModuleResponse,
    AdminQuestionResponse,
    AdminTestResponse,
)

router = APIRouter()

MODULE_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Module or course not found",
        "content": {
            "application/json": {
                "examples": {
                    "module not found": {
                        "summary": "Module not found",
                        "value": {"detail": api_messages.MODULE_NOT_FOUND},
                    },
                    "course not found": {
                        "summary": "Course not found",
                        "value": {"detail": api_messages.COURSE_NOT_FOUND},
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
                    "module has test": {
                        "summary": "Cannot delete module with test",
                        "value": {"detail": api_messages.MODULE_HAS_TEST},
                    },
                    "invalid position": {
                        "summary": "Invalid position value",
                        "value": {"detail": api_messages.INVALID_POSITION},
                    },
                }
            }
        },
    },
}


@router.get(
    "/courses/{course_id}/modules",
    response_model=list[AdminModuleListResponse],
    responses={404: {"description": "Course not found"}},
    description="Get all modules for a course (admin view)",
)
async def get_course_modules(
    course_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> list[AdminModuleListResponse]:
    """Get all modules for a course"""
    course = await session.scalar(select(Course).where(Course.unique_id == course_id))
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    result = await session.execute(
        select(Module)
        .options(selectinload(Module.tests).selectinload(Test.questions))
        .where(Module.course_id == course_id)
        .order_by(Module.position)
    )
    modules = result.scalars().all()

    return [
        AdminModuleListResponse(
            unique_id=module.unique_id,
            course_id=module.course_id,
            title=module.title,
            description=module.description,
            position=module.position,
            has_test=len(module.tests) > 0 if module.tests else False,
            create_time=module.create_time,
            update_time=module.update_time,
        )
        for module in modules
    ]


@router.get(
    "/modules/{module_id}",
    response_model=AdminModuleResponse,
    responses=MODULE_RESPONSES,
    description="Get module by ID (admin view)",
)
async def get_module(
    module_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminModuleResponse:
    """Get module with all details"""
    module = await session.scalar(
        select(Module)
        .options(
            selectinload(Module.course),
            selectinload(Module.tests)
            .selectinload(Test.questions)
            .selectinload(Question.answer_options),
        )
        .where(Module.unique_id == module_id)
    )

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.MODULE_NOT_FOUND,
        )

    test_responses = []
    if module.tests:
        for test in module.tests:
            test_responses.append(
                AdminTestResponse(
                    unique_id=test.unique_id,
                    module_id=test.module_id,
                    title=test.title,
                    description=test.description,
                    questions=[
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
                    ],
                    create_time=test.create_time,
                    update_time=test.update_time,
                )
            )

    return AdminModuleResponse(
        unique_id=module.unique_id,
        course_id=module.course_id,
        title=module.title,
        description=module.description,
        content_json=module.content_json,
        position=module.position,
        tests=test_responses,
        create_time=module.create_time,
        update_time=module.update_time,
    )


@router.post(
    "/courses/{course_id}/modules",
    response_model=AdminModuleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Course not found"}},
    description="Create a new module in a course",
)
async def create_module(
    course_id: str,
    module_data: ModuleCreateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminModuleResponse:
    """Create a new module"""
    course = await session.scalar(select(Course).where(Course.unique_id == course_id))
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    module = Module(
        course_id=course_id,
        title=module_data.title,
        description=module_data.description,
        content_json=module_data.content_json,
        position=module_data.position,
    )
    session.add(module)
    await session.commit()

    await session.refresh(module)
    return await get_module(module.unique_id, current_admin, session)


@router.put(
    "/modules/{module_id}",
    response_model=AdminModuleResponse,
    responses=MODULE_RESPONSES,
    description="Update a module",
)
async def update_module(
    module_id: str,
    module_data: ModuleUpdateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminModuleResponse:
    """Update an existing module"""
    module = await session.scalar(select(Module).where(Module.unique_id == module_id))
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.MODULE_NOT_FOUND,
        )

    update_data = module_data.model_dump(exclude_unset=True)
    if update_data:
        await session.execute(
            update(Module).where(Module.unique_id == module_id).values(**update_data)
        )

    await session.commit()
    return await get_module(module_id, current_admin, session)


@router.delete(
    "/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=MODULE_RESPONSES,
    description="Delete a module",
)
async def delete_module(
    module_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> None:
    """Delete a module"""
    module = await session.scalar(
        select(Module)
        .options(selectinload(Module.tests))
        .where(Module.unique_id == module_id)
    )
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.MODULE_NOT_FOUND,
        )

    if module.tests and len(module.tests) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.MODULE_HAS_TEST,
        )

    await session.execute(delete(Module).where(Module.unique_id == module_id))
    await session.commit()


@router.post(
    "/courses/{course_id}/modules/reorder",
    response_model=AdminBulkOperationResponse,
    responses={404: {"description": "Course not found"}},
    description="Reorder modules in a course",
)
async def reorder_modules(
    course_id: str,
    reorder_data: ModuleReorderRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminBulkOperationResponse:
    """Reorder modules in a course"""
    course = await session.scalar(select(Course).where(Course.unique_id == course_id))
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    success_count = 0
    error_count = 0
    errors = []

    for module_id, position in reorder_data.module_positions.items():
        if position < 0:
            error_count += 1
            errors.append(f"Invalid position for module {module_id}")
            continue

        module = await session.scalar(
            select(Module).where(
                Module.unique_id == module_id, Module.course_id == course_id
            )
        )
        if not module:
            error_count += 1
            errors.append(f"Module {module_id} not found in course")
            continue

        await session.execute(
            update(Module)
            .where(Module.unique_id == module_id)
            .values(position=position)
        )
        success_count += 1

    await session.commit()

    return AdminBulkOperationResponse(
        success_count=success_count,
        error_count=error_count,
        errors=errors,
    )
