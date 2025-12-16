from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import (
    CompletedModule,
    Course,
    CourseTag,
    Module,
    PurchasedCourse,
    User,
)
from app.schemas.responses import (
    CourseDetailResponseV2,
    CourseListResponseV2,
    ModuleResponse,
    TagResponse,
)

router = APIRouter()

COURSE_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Course not found",
        "content": {
            "application/json": {"example": {"detail": api_messages.COURSE_NOT_FOUND}}
        },
    },
}


@router.get(
    "",
    response_model=list[CourseListResponseV2],
    description="Get all active courses with user-specific pricing",
)
async def get_courses(
    skip: int = Query(0, ge=0, description="Number of courses to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of courses to return"
    ),
    current_user: User = Depends(deps.get_current_user_optional),
    session: AsyncSession = Depends(deps.get_session),
) -> list[CourseListResponseV2]:
    """Get all active courses with user-specific pricing (authenticated endpoint)"""
    result = await session.execute(
        select(Course)
        .options(
            selectinload(Course.modules),
            selectinload(Course.tags).selectinload(CourseTag.tag),
            selectinload(Course.discounts),
        )
        .where(Course.is_active)
        .offset(skip)
        .limit(limit)
        .order_by(Course.create_time.desc())
    )
    courses = result.scalars().all()

    purchased_course_ids = set()
    if current_user:
        purchased_courses_result = await session.execute(
            select(PurchasedCourse).where(
                PurchasedCourse.user_id == current_user.unique_id
            )
        )
        purchased_course_ids = {
            pc.course_id for pc in purchased_courses_result.scalars().all()
        }

    course_responses = []
    for course in courses:
        user_discount = None

        if current_user:
            for discount in course.discounts:
                if discount.user_id == current_user.unique_id:
                    user_discount = discount.percents
                    break

        if user_discount:
            final_price = course.price * (Decimal(100 - user_discount) / Decimal(100))
        else:
            final_price = course.price

        course_responses.append(
            CourseListResponseV2(
                unique_id=course.unique_id,
                title=course.title,
                description=course.description,
                price=course.price,
                img_id=course.img_id,
                modules_count=len(course.modules),
                tags=[
                    TagResponse(unique_id=ct.tag.unique_id, content=ct.tag.content)
                    for ct in course.tags
                ],
                is_active=course.is_active,
                user_discount=user_discount,
                final_price=final_price,
                is_purchased=course.unique_id in purchased_course_ids,
            )
        )

    return course_responses


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponseV2,
    responses=COURSE_RESPONSES,
    description="Get course by ID with user-specific info",
)
async def get_course(
    course_id: str,
    current_user: User = Depends(deps.get_current_user_optional),
    session: AsyncSession = Depends(deps.get_session),
) -> CourseDetailResponseV2:
    """Get course with user-specific information"""
    course = await session.scalar(
        select(Course)
        .options(
            selectinload(Course.modules),
            selectinload(Course.tags).selectinload(CourseTag.tag),
            selectinload(Course.discounts),
        )
        .where(Course.unique_id == course_id, Course.is_active)
    )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    is_purchased = False
    completion_percentage = None
    user_discount = None

    if current_user:
        purchase = await session.scalar(
            select(PurchasedCourse).where(
                PurchasedCourse.user_id == current_user.unique_id,
                PurchasedCourse.course_id == course_id,
            )
        )
        is_purchased = purchase is not None

        for discount in course.discounts:
            if discount.user_id == current_user.unique_id:
                user_discount = discount.percents
                break

        if is_purchased:
            completed_modules_result = await session.execute(
                select(CompletedModule)
                .join(Module)
                .where(
                    Module.course_id == course_id,
                    CompletedModule.user_id == current_user.unique_id,
                )
            )
            completed_modules_count = len(completed_modules_result.scalars().all())
            total_modules = len(course.modules)
            if total_modules > 0:
                completion_percentage = (completed_modules_count / total_modules) * 100

    if user_discount:
        final_price = course.price * (Decimal(100 - user_discount) / Decimal(100))
    else:
        final_price = course.price

    modules = [
        ModuleResponse(
            unique_id=module.unique_id,
            course_id=module.course_id,
            title=module.title,
            description=module.description,
            position=module.position,
        )
        for module in sorted(course.modules, key=lambda m: m.position)
    ]

    return CourseDetailResponseV2(
        unique_id=course.unique_id,
        title=course.title,
        description=course.description,
        price=course.price,
        img_id=course.img_id,
        modules=modules,
        tags=[
            TagResponse(
                unique_id=ct.tag.unique_id,
                content=ct.tag.content,
            )
            for ct in course.tags
        ],
        is_active=course.is_active,
        user_discount=user_discount,
        final_price=final_price,
        is_purchased=is_purchased,
        completion_percentage=completion_percentage,
    )
