from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import Course, CourseTag
from app.schemas.responses import (
    CourseDetailResponse,
    CourseListResponse,
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
    response_model=list[CourseListResponse],
    description="Get all active courses",
)
async def get_courses(
    skip: int = Query(0, ge=0, description="Number of courses to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of courses to return"
    ),
    session: AsyncSession = Depends(deps.get_session),
) -> list[CourseListResponse]:
    """Get all active courses with basic details"""
    result = await session.execute(
        select(Course)
        .options(
            selectinload(Course.modules),
            selectinload(Course.tags).selectinload(CourseTag.tag),
        )
        .where(Course.is_active)
        .offset(skip)
        .limit(limit)
        .order_by(Course.create_time.desc())
    )
    courses = result.scalars().all()

    return [
        CourseListResponse(
            unique_id=course.unique_id,
            title=course.title,
            description=course.description,
            price=course.price,
            img_id=course.img_id,
            modules_count=len(course.modules),
            tags=[
                TagResponse(
                    unique_id=ct.tag.unique_id,
                    content=ct.tag.content,
                )
                for ct in course.tags
            ],
            is_active=course.is_active,
        )
        for course in courses
    ]


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponse,
    responses=COURSE_RESPONSES,
    description="Get course by ID",
)
async def get_course(
    course_id: str,
    session: AsyncSession = Depends(deps.get_session),
) -> CourseDetailResponse:
    """Get course with all details"""
    course = await session.scalar(
        select(Course)
        .options(
            selectinload(Course.modules),
            selectinload(Course.tags).selectinload(CourseTag.tag),
        )
        .where(Course.unique_id == course_id, Course.is_active)
    )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

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

    return CourseDetailResponse(
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
    )
