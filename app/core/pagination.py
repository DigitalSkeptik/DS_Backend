from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

# Constants for pagination
MAX_PAGE_SIZE = 1000


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number (1-based)")
    page_size: int = Field(..., ge=1, le=1000, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""

    items: list[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


def calculate_pagination(
    total: int,
    page: int,
    page_size: int,
) -> PaginationMeta:
    """Calculate pagination metadata"""
    total_pages = ceil(total / page_size) if page_size > 0 else 0

    return PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, int]:
    """Get and validate pagination parameters"""
    # Validate page
    page = max(page, 1)

    # Validate page_size
    if page_size < 1:
        page_size = 20
    elif page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE

    # Calculate offset
    offset = (page - 1) * page_size

    return offset, page_size


def create_paginated_response(
    items: list[T],
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse[T]:
    """Create a paginated response"""
    pagination_meta = calculate_pagination(total, page, page_size)

    return PaginatedResponse(
        items=items,
        pagination=pagination_meta,
    )
