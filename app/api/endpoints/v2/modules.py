from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.core.fields_selector import (
    filter_model_fields,
    parse_fields_param,
    validate_fields,
)
from app.core.pagination import create_paginated_response, get_pagination_params
from app.models import CompletedModule, Course, Module, Test, User
from app.schemas.responses import (
    ModuleDetailResponse,
    ModuleResponse,
    PaginatedModuleResponse,
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
    "/courses/{course_id}",
    response_model=PaginatedModuleResponse,
    responses={404: {"description": "Course not found"}},
    summary="Получить модули курса",
    response_description="Список модулей курса с пагинацией",
)
async def get_course_modules(
    course_id: str,
    page: int = Query(1, ge=1, description="Номер страницы (начиная с 1)"),
    page_size: int = Query(
        20, ge=1, le=1000, description="Количество модулей на странице (1-1000)"
    ),
    session: AsyncSession = Depends(deps.get_session),
) -> PaginatedModuleResponse:
    """
    Получить список всех модулей курса с пагинацией.

    ## Особенности

    - **Базовая информация**: Возвращает только основные данные модулей (без контента)
    - **Пагинация**: Результаты разбиты на страницы
    - **Сортировка**: Модули отсортированы по позиции (position)
    - **Публичный доступ**: Не требует авторизации

    ## Возвращаемые данные

    Для каждого модуля:
    - `unique_id` - уникальный идентификатор модуля
    - `course_id` - ID курса, к которому относится модуль
    - `title` - название модуля
    - `description` - краткое описание модуля
    - `position` - порядковый номер модуля в курсе

    **Примечание**: Полный контент модуля (`content_json`) доступен только через эндпоинт
    `GET /api/v2/modules/{module_id}` для пользователей, купивших курс.

    ## Пагинация

    Метаданные включают:
    - `total` - общее количество модулей
    - `page` - текущая страница
    - `page_size` - размер страницы
    - `total_pages` - всего страниц
    - `has_next` - есть ли следующая страница
    - `has_prev` - есть ли предыдущая страница

    ## Примеры использования

    ```bash
    # Получить первую страницу модулей курса
    GET /api/v2/modules/courses/{course_id}?page=1&page_size=10

    # Получить все модули (большой page_size)
    GET /api/v2/modules/courses/{course_id}?page=1&page_size=1000
    ```

    ## Ошибки

    - **404 Not Found**: Курс не найден или неактивен
    """
    # Verify course exists
    course = await session.scalar(
        select(Course).where(Course.unique_id == course_id, Course.is_active)
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.COURSE_NOT_FOUND,
        )

    # Get pagination parameters
    offset, limit = get_pagination_params(page, page_size)

    # Get total count
    total_result = await session.execute(
        select(func.count(Module.unique_id)).where(Module.course_id == course_id)
    )
    total = total_result.scalar() or 0

    # Get modules
    result = await session.execute(
        select(Module)
        .where(Module.course_id == course_id)
        .order_by(Module.position)
        .offset(offset)
        .limit(limit)
    )
    modules = result.scalars().all()

    module_responses = [
        ModuleResponse(
            unique_id=module.unique_id,
            course_id=module.course_id,
            title=module.title,
            description=module.description,
            position=module.position,
        )
        for module in modules
    ]

    return create_paginated_response(module_responses, total, page, page_size)


@router.get(
    "/{module_id}",
    response_model=ModuleDetailResponse,
    responses=MODULE_RESPONSES,
    summary="Получить модуль по ID",
    response_description="Детальная информация о модуле с полным контентом",
)
async def get_module(
    module_id: str,
    fields: str = Query(
        None,
        description="Список полей через запятую. Используйте 'minimal' для базовых полей. Пример: 'unique_id,title,description' или 'minimal'",
    ),
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> ModuleDetailResponse:
    """
    Получить детальную информацию о модуле с полным контентом.

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен
    - **Покупка курса**: Пользователь должен купить курс, к которому относится модуль
    - **Активный курс**: Курс должен быть активным

    ## Особенности

    - **Полный контент**: Включает `content_json` с учебными материалами
    - **Статус прогресса**: Показывает, завершен ли модуль пользователем
    - **Информация о тесте**: Указывает наличие и статус прохождения теста
    - **Выборочные поля**: Поддержка параметра `fields` для оптимизации ответа

    ## Возвращаемые данные

    ### Основная информация
    - `unique_id` - уникальный идентификатор модуля
    - `course_id` - ID курса
    - `title` - название модуля
    - `description` - подробное описание
    - `position` - порядковый номер в курсе

    ### Контент и прогресс
    - `content_json` - полный учебный контент модуля (JSON)
    - `is_completed` - завершен ли модуль пользователем
    - `has_test` - есть ли тест для этого модуля
    - `test_completed` - пройден ли тест (если есть)

    ## Выборочные поля (Field Selection)

    Параметр `fields` позволяет запросить только нужные поля для оптимизации:

    ### Примеры
    ```bash
    # Только ID и название
    GET /api/v2/modules/{module_id}?fields=unique_id,title

    # Минимальный набор полей
    GET /api/v2/modules/{module_id}?fields=minimal

    # Несколько конкретных полей
    GET /api/v2/modules/{module_id}?fields=unique_id,title,description,is_completed
    ```

    ### Режим 'minimal'
    Возвращает только обязательные поля:
    - `unique_id`
    - `course_id`
    - `title`
    - `position`

    **Примечание**: Обязательные поля всегда включаются в ответ, даже если не указаны в `fields`.

    ## Примеры использования

    ```bash
    # Получить модуль с полным контентом
    GET /api/v2/modules/{module_id}
    Authorization: Bearer <token>

    # Получить только базовую информацию
    GET /api/v2/modules/{module_id}?fields=minimal
    Authorization: Bearer <token>

    # Получить модуль с выборочными полями
    GET /api/v2/modules/{module_id}?fields=unique_id,title,content_json,is_completed
    Authorization: Bearer <token>
    ```

    ## Ошибки

    - **401 Unauthorized**: Не авторизован или токен недействителен
    - **403 Forbidden**: Курс не куплен пользователем
    - **404 Not Found**: Модуль не найден или курс неактивен
    - **400 Bad Request**: Неверные поля в параметре `fields`
    """
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

    module_response = ModuleDetailResponse(
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

    if fields:
        try:
            requested_fields = parse_fields_param(fields)
            if requested_fields:
                validated_fields = validate_fields(
                    requested_fields, ModuleDetailResponse
                )
                filtered_data = filter_model_fields(
                    module_response, validated_fields, ModuleDetailResponse
                )

                return ModuleDetailResponse(**filtered_data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    return module_response
