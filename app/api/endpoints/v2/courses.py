from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.core.pagination import create_paginated_response, get_pagination_params
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
    PaginatedCourseListResponseV2,
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
    response_model=PaginatedCourseListResponseV2,
    summary="Получить список курсов",
    response_description="Список курсов с пагинацией и персонализированными ценами",
)
async def get_courses(
    page: int = Query(1, ge=1, description="Номер страницы (начиная с 1)"),
    page_size: int = Query(
        20, ge=1, le=1000, description="Количество курсов на странице (1-1000)"
    ),
    current_user: User = Depends(deps.get_current_user_optional),
    session: AsyncSession = Depends(deps.get_session),
) -> PaginatedCourseListResponseV2:
    """
    Получить список всех активных курсов с пагинацией.

    ## Особенности

    - **Пагинация**: Результаты разбиты на страницы для удобства
    - **Персонализация**: Если пользователь авторизован, показываются персональные скидки
    - **Статус покупки**: Отображается, куплен ли курс пользователем
    - **Сортировка**: Курсы отсортированы по дате создания (новые первыми)

    ## Возвращаемые данные

    Для каждого курса:
    - `unique_id` - уникальный идентификатор
    - `title` - название курса
    - `description` - описание курса
    - `price` - базовая цена
    - `final_price` - итоговая цена с учетом скидки
    - `user_discount` - персональная скидка (если есть)
    - `is_purchased` - куплен ли курс (требует авторизации)
    - `modules_count` - количество модулей
    - `tags` - теги курса

    ## Пагинация

    Метаданные пагинации включают:
    - `total` - общее количество курсов
    - `page` - текущая страница
    - `page_size` - размер страницы
    - `total_pages` - всего страниц
    - `has_next` - есть ли следующая страница
    - `has_prev` - есть ли предыдущая страница

    ## Примеры использования

    ```bash
    # Первая страница (20 курсов)
    GET /api/v2/courses?page=1&page_size=20

    # Вторая страница (50 курсов)
    GET /api/v2/courses?page=2&page_size=50
    ```
    """
    # Get pagination parameters
    offset, limit = get_pagination_params(page, page_size)

    # Get total count
    total_result = await session.execute(
        select(func.count(Course.unique_id)).where(Course.is_active)
    )
    total = total_result.scalar() or 0

    # Get courses with relationships
    result = await session.execute(
        select(Course)
        .options(
            selectinload(Course.modules),
            selectinload(Course.tags).selectinload(CourseTag.tag),
            selectinload(Course.discounts),
        )
        .where(Course.is_active)
        .offset(offset)
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

    return create_paginated_response(course_responses, total, page, page_size)


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponseV2,
    responses=COURSE_RESPONSES,
    summary="Получить курс по ID",
    response_description="Детальная информация о курсе с модулями и персональными данными",
)
async def get_course(
    course_id: str,
    current_user: User = Depends(deps.get_current_user_optional),
    session: AsyncSession = Depends(deps.get_session),
) -> CourseDetailResponseV2:
    """
    Получить детальную информацию о курсе по его ID.

    ## Особенности

    - **Полная информация**: Включает все модули курса
    - **Персонализация**: Показывает персональные скидки и цены
    - **Статус покупки**: Отображает, куплен ли курс
    - **Прогресс**: Для купленных курсов показывает процент завершения

    ## Возвращаемые данные

    ### Основная информация
    - `unique_id` - уникальный идентификатор курса
    - `title` - название курса
    - `description` - подробное описание
    - `price` - базовая цена курса
    - `img_id` - идентификатор изображения
    - `is_active` - активен ли курс
    - `tags` - список тегов курса

    ### Персонализированные данные (если авторизован)
    - `user_discount` - персональная скидка в процентах (null если нет)
    - `final_price` - итоговая цена с учетом скидки
    - `is_purchased` - куплен ли курс пользователем
    - `completion_percentage` - процент завершения (только для купленных курсов)

    ### Модули курса
    - `modules` - список всех модулей курса с базовой информацией
      - `unique_id` - ID модуля
      - `title` - название модуля
      - `description` - описание модуля
      - `position` - порядковый номер

    ## Примеры использования

    ```bash
    # Получить курс (без авторизации)
    GET /api/v2/courses/{course_id}

    # Получить курс с персональными данными (с авторизацией)
    GET /api/v2/courses/{course_id}
    Authorization: Bearer <token>
    ```

    ## Ошибки

    - **404 Not Found**: Курс не найден или неактивен
    """
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
