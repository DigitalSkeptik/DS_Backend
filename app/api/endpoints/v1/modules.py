from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import CompletedModule, Course, Module, Test, User
from app.schemas.responses import ModuleDetailResponse, ModuleResponse

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
    403: {
        "description": "Access denied",
        "content": {
            "application/json": {
                "example": {"detail": api_messages.MODULE_ACCESS_DENIED}
            }
        },
    },
}


@router.get(
    "/courses/{course_id}/modules",
    response_model=list[ModuleResponse],
    responses={404: {"description": "Course not found"}},
    description="Get all modules for a course (basic info)",
)
async def get_course_modules(
    course_id: str,
    session: AsyncSession = Depends(deps.get_session),
) -> list[ModuleResponse]:
    """Get all modules for a course with basic info"""
    course = await session.scalar(
        select(Course).where(Course.unique_id == course_id, Course.is_active)
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    result = await session.execute(
        select(Module).where(Module.course_id == course_id).order_by(Module.position)
    )
    modules = result.scalars().all()

    return [
        ModuleResponse(
            unique_id=module.unique_id,
            course_id=module.course_id,
            title=module.title,
            description=module.description,
            position=module.position,
        )
        for module in modules
    ]


@router.get(
    "/modules/{module_id}",
    response_model=ModuleDetailResponse,
    responses=MODULE_RESPONSES,
    description="Get module by ID with full content (requires course purchase)",
)
async def get_module(
    module_id: str,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> ModuleDetailResponse:
    """Get module with full content if user has purchased the course"""
    module = await session.scalar(
        select(Module)
        .options(selectinload(Module.course))
        .where(Module.unique_id == module_id)
    )

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.MODULE_NOT_FOUND,
        )

    if not module.course.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    has_access = await deps.verify_course_access(
        module.course_id, current_user, session
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_messages.MODULE_ACCESS_DENIED,
        )

    completed_module = await session.scalar(
        select(CompletedModule).where(
            CompletedModule.user_id == current_user.unique_id,
            CompletedModule.module_id == module_id,
        )
    )
    is_completed = completed_module is not None

    test = await session.scalar(select(Test).where(Test.module_id == module_id))
    has_test = test is not None

    test_completed = False
    if has_test and is_completed:
        test_completed = True

    return ModuleDetailResponse(
        unique_id=module.unique_id,
        course_id=module.course_id,
        title=module.title,
        description=module.description,
        content_json=module.content_json,
        position=module.position,
        is_completed=is_completed,
        has_test=has_test,
        test_completed=test_completed,
    )
