from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import Tag, User
from app.schemas.admin_requests import TagCreateRequest, TagUpdateRequest
from app.schemas.admin_responses import AdminBulkOperationResponse, AdminTagResponse

router = APIRouter()

TAG_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Tag not found",
        "content": {
            "application/json": {"example": {"detail": api_messages.TAG_NOT_FOUND}}
        },
    },
    400: {
        "description": "Bad request",
        "content": {
            "application/json": {
                "examples": {
                    "tag already exists": {
                        "summary": "Tag already exists",
                        "value": {"detail": api_messages.TAG_ALREADY_EXISTS},
                    },
                    "tag has courses": {
                        "summary": "Cannot delete tag with associated courses",
                        "value": {
                            "detail": "Cannot delete tag with associated courses"
                        },
                    },
                }
            }
        },
    },
}


@router.get(
    "/tags",
    response_model=list[AdminTagResponse],
    description="Get all tags (admin view)",
)
async def get_all_tags(
    skip: int = Query(0, ge=0, description="Number of tags to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of tags to return"
    ),
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> list[AdminTagResponse]:
    """Get all tags"""
    result = await session.execute(
        select(Tag)
        .options(selectinload(Tag.courses))
        .offset(skip)
        .limit(limit)
        .order_by(Tag.content)
    )
    tags = result.scalars().all()

    return [
        AdminTagResponse(
            unique_id=tag.unique_id,
            content=tag.content,
            create_time=tag.create_time,
            update_time=tag.update_time,
        )
        for tag in tags
    ]


@router.get(
    "/tags/{tag_id}",
    response_model=AdminTagResponse,
    responses=TAG_RESPONSES,
    description="Get tag by ID (admin view)",
)
async def get_tag(
    tag_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminTagResponse:
    """Get tag by ID"""
    tag = await session.scalar(
        select(Tag).options(selectinload(Tag.courses)).where(Tag.unique_id == tag_id)
    )

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TAG_NOT_FOUND,
        )

    return AdminTagResponse(
        unique_id=tag.unique_id,
        content=tag.content,
        create_time=tag.create_time,
        update_time=tag.update_time,
    )


@router.post(
    "/tags",
    response_model=AdminTagResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "Tag already exists",
            "content": {
                "application/json": {
                    "example": {"detail": api_messages.TAG_ALREADY_EXISTS}
                }
            },
        }
    },
    description="Create a new tag",
)
async def create_tag(
    tag_data: TagCreateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminTagResponse:
    """Create a new tag"""
    existing_tag = await session.scalar(
        select(Tag).where(Tag.content == tag_data.content)
    )
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.TAG_ALREADY_EXISTS,
        )

    tag = Tag(content=tag_data.content)
    session.add(tag)
    await session.commit()

    await session.refresh(tag)
    return await get_tag(tag.unique_id, current_admin, session)


@router.put(
    "/tags/{tag_id}",
    response_model=AdminTagResponse,
    responses=TAG_RESPONSES,
    description="Update a tag",
)
async def update_tag(
    tag_id: str,
    tag_data: TagUpdateRequest,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminTagResponse:
    """Update an existing tag"""
    tag = await session.scalar(select(Tag).where(Tag.unique_id == tag_id))
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TAG_NOT_FOUND,
        )

    if tag_data.content and tag_data.content != tag.content:
        existing_tag = await session.scalar(
            select(Tag).where(Tag.content == tag_data.content)
        )
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_messages.TAG_ALREADY_EXISTS,
            )

    update_data = tag_data.model_dump(exclude_unset=True)
    if update_data:
        await session.execute(
            update(Tag).where(Tag.unique_id == tag_id).values(**update_data)
        )

    await session.commit()
    return await get_tag(tag_id, current_admin, session)


@router.delete(
    "/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=TAG_RESPONSES,
    description="Delete a tag",
)
async def delete_tag(
    tag_id: str,
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> None:
    """Delete a tag"""
    tag = await session.scalar(
        select(Tag).options(selectinload(Tag.courses)).where(Tag.unique_id == tag_id)
    )
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TAG_NOT_FOUND,
        )

    if tag.courses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete tag with associated courses",
        )

    await session.execute(delete(Tag).where(Tag.unique_id == tag_id))
    await session.commit()


@router.post(
    "/tags/bulk-delete",
    response_model=AdminBulkOperationResponse,
    description="Delete multiple tags",
)
async def bulk_delete_tags(
    tag_ids: list[str],
    current_admin: User = Depends(deps.get_current_admin_user),
    session: AsyncSession = Depends(deps.get_session),
) -> AdminBulkOperationResponse:
    """Delete multiple tags"""
    success_count = 0
    error_count = 0
    errors = []

    for tag_id in tag_ids:
        tag = await session.scalar(
            select(Tag)
            .options(selectinload(Tag.courses))
            .where(Tag.unique_id == tag_id)
        )
        if not tag:
            error_count += 1
            errors.append(f"Tag {tag_id} not found")
            continue

        if tag.courses:
            error_count += 1
            errors.append(f"Tag {tag.content} has associated courses")
            continue

        await session.execute(delete(Tag).where(Tag.unique_id == tag_id))
        success_count += 1

    await session.commit()

    return AdminBulkOperationResponse(
        success_count=success_count,
        error_count=error_count,
        errors=errors,
    )
