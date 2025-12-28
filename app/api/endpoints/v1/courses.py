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
    summary="Получить список курсов",
    response_description="Список активных курсов",
)
async def get_courses(
    skip: int = Query(0, ge=0, description="Количество курсов для пропуска (offset)"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество курсов (1-1000)"
    ),
    session: AsyncSession = Depends(deps.get_session),
) -> list[CourseListResponse]:
    """
    Получить список всех активных курсов (v1 - без пагинации).

    ## Особенности v1

    - **Offset/Limit пагинация**: Использует skip/limit вместо page/page_size
    - **Без персонализации**: Не показывает персональные скидки
    - **Базовая информация**: Только основные данные курсов
    - **Публичный доступ**: Не требует авторизации

    ## Параметры

    - `skip` - количество курсов для пропуска (по умолчанию 0)
    - `limit` - максимальное количество курсов (по умолчанию 100, макс 1000)

    ## Возвращаемые данные

    Массив курсов, каждый содержит:
    - `unique_id` - уникальный идентификатор
    - `title` - название курса
    - `description` - описание
    - `price` - цена курса
    - `img_id` - ID изображения
    - `modules_count` - количество модулей
    - `tags` - теги курса
    - `is_active` - активен ли курс

    ## Примеры использования

    ```bash
    # Первые 20 курсов
    GET /api/v1/courses?skip=0&limit=20

    # Следующие 20 курсов
    GET /api/v1/courses?skip=20&limit=20
    ```

    ## Отличия от v2

    **v1**:
    - Offset/limit пагинация
    - Нет метаданных пагинации
    - Нет персональных цен

    **v2** (`/api/v2/courses`):
    - Page-based пагинация
    - Метаданные (total, has_next, etc.)
    - Персональные скидки и цены
    - Статус покупки
    """
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
    summary="Получить курс по ID",
    response_description="Детальная информация о курсе",
)
async def get_course(
    course_id: str,
    session: AsyncSession = Depends(deps.get_session),
) -> CourseDetailResponse:
    """
    Получить детальную информацию о курсе (v1 - без персонализации).

    ## Особенности v1

    - **Без персонализации**: Не показывает персональные данные
    - **Публичный доступ**: Не требует авторизации
    - **Базовая информация**: Только общедоступные данные

    ## Возвращаемые данные

    - `unique_id` - уникальный идентификатор курса
    - `title` - название курса
    - `description` - подробное описание
    - `price` - базовая цена курса
    - `img_id` - идентификатор изображения
    - `modules` - список модулей с базовой информацией
    - `tags` - теги курса
    - `is_active` - активен ли курс

    ## Примеры использования

    ```bash
    # Получить курс
    GET /api/v1/courses/{course_id}
    ```

    ## Отличия от v2

    **v1**:
    - Только базовая цена
    - Нет персональных скидок
    - Нет статуса покупки
    - Нет процента завершения

    **v2** (`/api/v2/courses/{course_id}`):
    - Персональные скидки
    - Итоговая цена с учетом скидки
    - Статус покупки
    - Процент завершения (для купленных)

    ## Ошибки

    - **404 Not Found**: Курс не найден или неактивен
    """
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
