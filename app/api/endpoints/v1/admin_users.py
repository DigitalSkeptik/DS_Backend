from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import (
    CompletedCourse,
    CompletedModule,
    Course,
    Module,
    PurchasedCourse,
    Question,
    Test,
    User,
    UserRole,
)
from app.schemas.admin_requests import UserRoleUpdateRequest
from app.schemas.admin_responses import (
    AdminStatsResponse,
    AdminUserListResponse,
    AdminUserResponse,
)

router = APIRouter()

USER_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "User not found",
        "content": {
            "application/json": {"example": {"detail": api_messages.USER_NOT_FOUND}}
        },
    },
}


@router.get(
    "",
    response_model=list[AdminUserListResponse],
    summary="Получить всех пользователей (админ)",
)
async def get_all_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of users to return"
    ),
    role: UserRole | None = Query(None, description="Filter by user role"),
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> list[AdminUserListResponse]:
    """Get all users with optional role filtering"""
    query = select(User)

    if role:
        query = query.where(User.role == role)

    result = await session.execute(
        query.offset(skip).limit(limit).order_by(User.create_time.desc())
    )
    users = result.scalars().all()

    return [
        AdminUserListResponse(
            unique_id=user.unique_id,
            email=user.email,
            username=user.username,
            role=user.role,
            create_time=user.create_time,
            update_time=user.update_time,
        )
        for user in users
    ]


@router.get(
    "/{user_id}",
    response_model=AdminUserResponse,
    responses=USER_RESPONSES,
    summary="Получить пользователя (админ)",
)
async def get_user(
    user_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminUserResponse:
    """Get user by ID"""
    user = await session.scalar(select(User).where(User.unique_id == user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.USER_NOT_FOUND,
        )

    return AdminUserResponse(
        unique_id=user.unique_id,
        email=user.email,
        username=user.username,
        role=user.role,
        create_time=user.create_time,
        update_time=user.update_time,
    )


@router.put(
    "/{user_id}/role",
    response_model=AdminUserResponse,
    responses=USER_RESPONSES,
    summary="Изменить роль пользователя",
)
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminUserResponse:
    """Update a user's role"""
    user = await session.scalar(select(User).where(User.unique_id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.USER_NOT_FOUND,
        )

    # Prevent admin from changing their own role
    if user_id == current_admin.unique_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    await session.execute(
        update(User).where(User.unique_id == user_id).values(role=role_data.role)
    )
    await session.commit()

    await session.refresh(user)
    return AdminUserResponse(
        unique_id=user.unique_id,
        email=user.email,
        username=user.username,
        role=user.role,
        create_time=user.create_time,
        update_time=user.update_time,
    )


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Получить статистику платформы",
)
async def get_stats(
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminStatsResponse:
    """Get platform statistics"""
    from sqlalchemy import func

    admin_users_result = await session.scalar(
        select(func.count(User.unique_id)).where(User.role == UserRole.ADMIN)
    )
    regular_users_result = await session.scalar(
        select(func.count(User.unique_id)).where(User.role == UserRole.USER)
    )

    total_courses_result = await session.scalar(select(func.count(Course.unique_id)))
    active_courses_result = await session.scalar(
        select(func.count(Course.unique_id)).where(Course.is_active)
    )
    total_modules_result = await session.scalar(select(func.count(Module.unique_id)))
    total_tests_result = await session.scalar(select(func.count(Test.unique_id)))
    total_questions_result = await session.scalar(
        select(func.count(Question.unique_id))
    )

    return AdminStatsResponse(
        total_users=(admin_users_result or 0) + (regular_users_result or 0),
        total_courses=total_courses_result or 0,
        total_modules=total_modules_result or 0,
        total_tests=total_tests_result or 0,
        total_questions=total_questions_result or 0,
        active_courses=active_courses_result or 0,
        admin_users=admin_users_result or 0,
        regular_users=regular_users_result or 0,
    )


@router.get(
    "/{user_id}/courses",
    response_model=list[dict],
    responses=USER_RESPONSES,
    summary="Получить купленные курсы пользователя",
)
async def get_user_courses(
    user_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> list[dict]:
    """Get courses purchased by a user"""
    user = await session.scalar(select(User).where(User.unique_id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.USER_NOT_FOUND,
        )

    user_with_courses = await session.scalar(
        select(User)
        .options(
            selectinload(User.purchased_courses).selectinload(PurchasedCourse.course)
        )
        .where(User.unique_id == user_id)
    )

    courses = []
    if user_with_courses and user_with_courses.purchased_courses:
        for purchase in user_with_courses.purchased_courses:
            courses.append(
                {
                    "unique_id": purchase.course.unique_id,
                    "title": purchase.course.title,
                    "description": purchase.course.description,
                    "price": purchase.course.price,
                    "purchase_date": purchase.create_time,
                }
            )

    return courses


@router.get(
    "/{user_id}/progress",
    response_model=dict,
    responses=USER_RESPONSES,
    summary="Получить прогресс пользователя",
)
async def get_user_progress(
    user_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> dict:
    """Get user's course progress"""
    user = await session.scalar(select(User).where(User.unique_id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.USER_NOT_FOUND,
        )

    user_with_progress = await session.scalar(
        select(User)
        .options(
            selectinload(User.completed_courses).selectinload(CompletedCourse.course),
            selectinload(User.completed_modules)
            .selectinload(CompletedModule.module)
            .selectinload(Module.course),
        )
        .where(User.unique_id == user_id)
    )

    completed_courses = []
    completed_modules = []

    if user_with_progress:
        if user_with_progress.completed_courses:
            for completed in user_with_progress.completed_courses:
                completed_courses.append(
                    {
                        "course_id": completed.course.unique_id,
                        "course_title": completed.course.title,
                        "completion_date": completed.create_time,
                    }
                )

        if user_with_progress.completed_modules:
            for completed in user_with_progress.completed_modules:
                completed_modules.append(
                    {
                        "module_id": completed.module.unique_id,
                        "module_title": completed.module.title,
                        "course_id": completed.module.course.unique_id,
                        "course_title": completed.module.course.title,
                        "completion_date": completed.create_time,
                    }
                )

    return {
        "user_id": user_id,
        "completed_courses": completed_courses,
        "completed_modules": completed_modules,
        "total_completed_courses": len(completed_courses),
        "total_completed_modules": len(completed_modules),
    }
