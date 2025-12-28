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
    "/courses/{course_id}",
    response_model=list[ModuleResponse],
    responses={404: {"description": "Course not found"}},
    summary="Получить модули курса",
    response_description="Список модулей курса",
)
async def get_course_modules(
    course_id: str,
    session: AsyncSession = Depends(deps.get_session),
) -> list[ModuleResponse]:
    """
    Получить список всех модулей курса (v1 - без пагинации).

    ## Особенности v1

    - **Без пагинации**: Возвращает все модули сразу
    - **Базовая информация**: Только основные данные (без контента)
    - **Публичный доступ**: Не требует авторизации
    - **Сортировка**: По позиции (position)

    ## Возвращаемые данные

    Массив модулей, каждый содержит:
    - `unique_id` - уникальный идентификатор модуля
    - `course_id` - ID курса
    - `title` - название модуля
    - `description` - краткое описание
    - `position` - порядковый номер

    **Примечание**: Полный контент модуля доступен только через
    `GET /modules/{module_id}` для авторизованных пользователей, купивших курс.

    ## Примеры использования

    ```bash
    # Получить все модули курса
    GET /api/v1/modules/courses/{course_id}
    ```

    ## Отличия от v2

    **v1**:
    - Без пагинации (все модули сразу)
    - Простой массив

    **v2** (`/api/v2/modules/courses/{course_id}`):
    - С пагинацией (page/page_size)
    - Метаданные пагинации
    - Более гибкий для больших курсов

    ## Ошибки

    - **404 Not Found**: Курс не найден или неактивен
    """
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
    "/{module_id}",
    response_model=ModuleDetailResponse,
    responses=MODULE_RESPONSES,
    summary="Получить модуль по ID",
    response_description="Детальная информация о модуле с контентом",
)
async def get_module(
    module_id: str,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> ModuleDetailResponse:
    """
    Получить детальную информацию о модуле с полным контентом (v1).

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен
    - **Покупка курса**: Пользователь должен купить курс
    - **Активный курс**: Курс должен быть активным

    ## Особенности v1

    - **Без выборочных полей**: Всегда возвращает все поля
    - **Полный контент**: Включает content_json
    - **Статус прогресса**: Показывает завершение

    ## Возвращаемые данные

    - `unique_id` - уникальный идентификатор модуля
    - `course_id` - ID курса
    - `title` - название модуля
    - `description` - подробное описание
    - `content_json` - полный учебный контент (JSON)
    - `position` - порядковый номер в курсе
    - `is_completed` - завершен ли модуль пользователем
    - `has_test` - есть ли тест для этого модуля
    - `test_completed` - пройден ли тест

    ## Примеры использования

    ```bash
    # Получить модуль с полным контентом
    GET /api/v1/modules/{module_id}
    Authorization: Bearer <token>
    ```

    ## Отличия от v2

    **v1**:
    - Всегда возвращает все поля
    - Нет параметра fields

    **v2** (`/api/v2/modules/{module_id}`):
    - Поддержка параметра `fields`
    - Можно запросить только нужные поля
    - Режим `minimal` для оптимизации

    ## Ошибки

    - **401 Unauthorized**: Не авторизован
    - **403 Forbidden**: Курс не куплен
    - **404 Not Found**:
      - Модуль не найден
      - Курс неактивен
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
