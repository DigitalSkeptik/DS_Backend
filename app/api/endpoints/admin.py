from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import Course, CourseTag, Module, Question, Tag, Test, User
from app.schemas.admin_requests import (
    CourseCreateRequest,
    CourseUpdateRequest,
)
from app.schemas.admin_responses import (
    AdminAnswerOptionResponse,
    AdminCourseListResponse,
    AdminCourseResponse,
    AdminModuleResponse,
    AdminQuestionResponse,
    AdminTagResponse,
    AdminTestResponse,
)

router = APIRouter()

COURSE_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Course not found",
        "content": {
            "application/json": {"example": {"detail": api_messages.COURSE_NOT_FOUND}}
        },
    },
    400: {
        "description": "Bad request",
        "content": {
            "application/json": {
                "examples": {
                    "course has modules": {
                        "summary": "Cannot delete course with modules",
                        "value": {"detail": api_messages.COURSE_HAS_MODULES},
                    }
                }
            }
        },
    },
}


@router.get(
    "/courses",
    response_model=list[AdminCourseListResponse],
    description="Get all courses (admin view)",
)
async def get_all_courses(
    skip: int = Query(0, ge=0, description="Number of courses to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of courses to return"
    ),
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> list[AdminCourseListResponse]:
    """Get all courses with admin details"""
    # Load courses with modules count and tags
    result = await session.execute(
        select(Course)
        .options(
            selectinload(Course.modules),
            selectinload(Course.tags).selectinload(CourseTag.tag),
        )
        .offset(skip)
        .limit(limit)
        .order_by(Course.create_time.desc())
    )
    courses = result.scalars().all()

    return [
        AdminCourseListResponse(
            unique_id=course.unique_id,
            title=course.title,
            description=course.description,
            price=course.price,
            is_active=course.is_active,
            img_id=course.img_id,
            modules_count=len(course.modules),
            tags=[
                AdminTagResponse(
                    unique_id=ct.tag.unique_id,
                    content=ct.tag.content,
                    create_time=ct.tag.create_time,
                    update_time=ct.tag.update_time,
                )
                for ct in course.tags
            ],
            create_time=course.create_time,
            update_time=course.update_time,
        )
        for course in courses
    ]


@router.get(
    "/courses/{course_id}",
    response_model=AdminCourseResponse,
    responses=COURSE_RESPONSES,
    description="Get course by ID (admin view)",
)
async def get_course(
    course_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminCourseResponse:
    """Get course with all details"""
    # Load course with all related data
    course = await session.scalar(
        select(Course)
        .options(
            selectinload(Course.modules)
            .selectinload(Module.tests)
            .selectinload(Test.questions)
            .selectinload(Question.answer_options),
            selectinload(Course.tags).selectinload(CourseTag.tag),
        )
        .where(Course.unique_id == course_id)
    )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    # Build modules with tests
    modules = []
    for module in sorted(course.modules, key=lambda m: m.position):
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

        modules.append(
            AdminModuleResponse(
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
        )

    return AdminCourseResponse(
        unique_id=course.unique_id,
        title=course.title,
        description=course.description,
        price=course.price,
        is_active=course.is_active,
        img_id=course.img_id,
        modules=modules,
        tags=[
            AdminTagResponse(
                unique_id=ct.tag.unique_id,
                content=ct.tag.content,
                create_time=ct.tag.create_time,
                update_time=ct.tag.update_time,
            )
            for ct in course.tags
        ],
        create_time=course.create_time,
        update_time=course.update_time,
    )


@router.post(
    "/courses",
    response_model=AdminCourseResponse,
    status_code=status.HTTP_201_CREATED,
    description="Create a new course",
)
async def create_course(
    course_data: CourseCreateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminCourseResponse:
    """Create a new course"""
    # Create course
    course = Course(
        title=course_data.title,
        description=course_data.description,
        price=course_data.price,
        is_active=course_data.is_active,
        img_id=course_data.img_id,
    )
    session.add(course)
    await session.flush()  # Get the course ID

    # Add tags if provided
    if course_data.tag_ids:
        for tag_id in course_data.tag_ids:
            # Verify tag exists
            tag = await session.scalar(select(Tag).where(Tag.unique_id == tag_id))
            if tag:
                course_tag = CourseTag(course_id=course.unique_id, tag_id=tag_id)
                session.add(course_tag)

    await session.commit()

    # Reload with all data
    await session.refresh(course)
    return await get_course(course.unique_id, current_admin, session)


@router.put(
    "/courses/{course_id}",
    response_model=AdminCourseResponse,
    responses=COURSE_RESPONSES,
    description="Update a course",
)
async def update_course(
    course_id: str,
    course_data: CourseUpdateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminCourseResponse:
    """Update an existing course"""
    # Check if course exists
    course = await session.scalar(select(Course).where(Course.unique_id == course_id))
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    # Update fields if provided
    update_data = course_data.model_dump(exclude_unset=True)
    if "tag_ids" in update_data:
        tag_ids = update_data.pop("tag_ids")
        # Handle tag updates separately
        await _update_course_tags(course_id, tag_ids, session)

    if update_data:
        await session.execute(
            update(Course).where(Course.unique_id == course_id).values(**update_data)
        )

    await session.commit()
    return await get_course(course_id, current_admin, session)


@router.delete(
    "/courses/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COURSE_RESPONSES,
    description="Delete a course",
)
async def delete_course(
    course_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> None:
    """Delete a course"""
    # Check if course exists
    course = await session.scalar(
        select(Course)
        .options(selectinload(Course.modules))
        .where(Course.unique_id == course_id)
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    # Check if course has modules
    if course.modules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.COURSE_HAS_MODULES,
        )

    # Delete course
    await session.execute(delete(Course).where(Course.unique_id == course_id))
    await session.commit()


async def _update_course_tags(
    course_id: str, tag_ids: list[str], session: AsyncSession
) -> None:
    """Helper function to update course tags"""
    # Delete existing tags
    await session.execute(delete(CourseTag).where(CourseTag.course_id == course_id))

    # Add new tags
    for tag_id in tag_ids:
        # Verify tag exists
        tag = await session.scalar(select(Tag).where(Tag.unique_id == tag_id))
        if tag:
            course_tag = CourseTag(course_id=course_id, tag_id=tag_id)
            session.add(course_tag)
