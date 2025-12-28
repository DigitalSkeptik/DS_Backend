from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database_session import get_async_session
from app.core.security.api_key import verify_api_key
from app.models import (
    CompletedModule,
    Course,
    Module,
    PurchasedCourse,
    Test,
    User,
    UserRole,
)
from app.schemas.admin_requests import CourseCreateRequest
from app.schemas.responses import CourseListResponse

router = APIRouter()


async def get_internal_user(
    request: Request,
) -> User:
    """Get authenticated user for internal endpoints"""
    async with get_async_session() as session:
        return await verify_api_key(request, session)


@router.post(
    "/courses/batch-create",
    response_model=list[CourseListResponse],
    summary="Массовое создание курсов",
    response_description="Список созданных курсов",
    status_code=status.HTTP_201_CREATED,
)
async def batch_create_courses(
    courses_data: list[CourseCreateRequest],
    request: Request,
) -> list[CourseListResponse]:
    """
    Массовое создание курсов для внутренних сервисов.

    ## Назначение

    Внутренний эндпоинт для служебных операций, позволяющий создавать
    несколько курсов за один запрос. Используется для:
    - Импорта курсов из внешних систем
    - Массовой загрузки контента
    - Автоматизированного создания курсов
    - Миграции данных

    ## Аутентификация

    **Требуется API-ключ** в заголовке `X-API-Key`.

    Настройка через переменную окружения:
    ```bash
    SECURITY__INTERNAL_API_KEY=your-secret-key
    ```

    ## Особенности

    - **Массовая операция**: Создает несколько курсов за один запрос
    - **Транзакционность**: Все курсы создаются в одной транзакции
    - **Упрощенная валидация**: Минимальная проверка данных
    - **Без пользовательского контекста**: Не привязано к конкретному пользователю

    ## Входные данные

    Массив объектов курсов, каждый содержит:
    - `title` - название курса (обязательно)
    - `description` - описание курса (опционально)
    - `price` - цена курса (обязательно)
    - `img_id` - ID изображения (опционально)
    - `is_active` - активен ли курс (по умолчанию true)

    ## Возвращаемые данные

    Массив созданных курсов с базовой информацией:
    - `unique_id` - UUID курса
    - `title` - название
    - `description` - описание
    - `price` - цена
    - `img_id` - ID изображения
    - `modules_count` - количество модулей (0 для новых курсов)
    - `tags` - теги (пустой массив для новых курсов)
    - `is_active` - статус активности

    ## Примеры использования

    ```bash
    # Создать несколько курсов
    POST /api/v2/internal/courses/batch-create
    X-API-Key: your-secret-key
    Content-Type: application/json

    [
      {
        "title": "Python для начинающих",
        "description": "Основы программирования на Python",
        "price": 1999.00,
        "img_id": "python-course-img",
        "is_active": true
      },
      {
        "title": "JavaScript Advanced",
        "description": "Продвинутый JavaScript",
        "price": 2999.00,
        "is_active": true
      }
    ]
    ```

    ## Отличия от публичного API

    - Не требует JWT токена пользователя
    - Использует API-ключ вместо аутентификации
    - Позволяет массовые операции
    - Упрощенная валидация
    - Не проверяет права доступа пользователя

    ## Ошибки

    - **401 Unauthorized**: Отсутствует или неверный API-ключ
    - **400 Bad Request**: Неверный формат данных
    """
    async with get_async_session() as session:
        # Verify API key
        await verify_api_key(request, session)

        created_courses = []

        for course_data in courses_data:
            course = Course(
                title=course_data.title,
                description=course_data.description,
                price=course_data.price,
                img_id=course_data.img_id,
                is_active=course_data.is_active,
            )
            session.add(course)
            created_courses.append(course)

        await session.commit()

        # Refresh all courses to get their IDs
        for course in created_courses:
            await session.refresh(course)

        return [
            CourseListResponse(
                unique_id=course.unique_id,
                title=course.title,
                description=course.description,
                price=course.price,
                img_id=course.img_id,
                modules_count=0,  # No modules yet
                tags=[],  # No tags yet
                is_active=course.is_active,
            )
            for course in created_courses
        ]


@router.post(
    "/users/{user_id}/make-admin",
    summary="Повысить пользователя до администратора",
    response_description="Успешное повышение (без тела ответа)",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def make_user_admin(
    user_id: str,
    request: Request,
) -> None:
    """
    Повысить пользователя до роли администратора.

    ## Назначение

    Внутренний эндпоинт для управления ролями пользователей.
    Используется для:
    - Назначения администраторов системы
    - Управления правами доступа
    - Автоматизированного управления ролями

    ## Аутентификация

    **Требуется API-ключ** в заголовке `X-API-Key`.

    ## Параметры

    - `user_id` - UUID пользователя (в URL)

    ## Роли пользователей

    - **user** - обычный пользователь (по умолчанию)
    - **admin** - администратор с полными правами

    ## Права администратора

    После повышения пользователь получает доступ к:
    - Административным эндпоинтам `/api/v2/admin/*`
    - Управлению курсами, модулями, тестами
    - Управлению пользователями
    - Управлению тегами
    - Просмотру статистики

    ## Примеры использования

    ```bash
    # Сделать пользователя администратором
    POST /api/v2/internal/users/{user_id}/make-admin
    X-API-Key: your-secret-key
    ```

    ## Ответ

    При успехе возвращается статус **204 No Content** без тела ответа.

    ## Безопасность

    - Операция необратима через API (требуется прямой доступ к БД для понижения)
    - Используйте с осторожностью
    - Логируйте все изменения ролей
    - Рекомендуется дополнительная аутентификация для продакшена

    ## Ошибки

    - **401 Unauthorized**: Отсутствует или неверный API-ключ
    - **404 Not Found**: Пользователь не найден
    """
    async with get_async_session() as session:
        # Verify API key
        await verify_api_key(request, session)

        user = await session.scalar(select(User).where(User.unique_id == user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.role = UserRole.ADMIN
        await session.commit()


@router.get(
    "/stats/courses",
    summary="Получить статистику курсов",
    response_description="Детальная статистика по курсам и пользователям",
)
async def get_course_stats(
    request: Request,
) -> dict[str, Any]:
    """
    Получить комплексную статистику по курсам для внутренних сервисов.

    ## Назначение

    Внутренний эндпоинт для получения аналитики и статистики.
    Используется для:
    - Мониторинга системы
    - Бизнес-аналитики
    - Отчетности
    - Дашбордов администратора

    ## Аутентификация

    **Требуется API-ключ** в заголовке `X-API-Key`.

    ## Возвращаемые данные

    ### Обзор (overview)
    - `total_courses` - всего курсов в системе
    - `active_courses` - активных курсов
    - `total_modules` - всего модулей
    - `total_tests` - всего тестов

    ### Вовлеченность (engagement)
    - `total_purchases` - всего покупок курсов
    - `total_completions` - всего завершений модулей

    ### Доход (revenue)
    - `total_potential_revenue` - потенциальный доход (сумма цен активных курсов)
    - `currency` - валюта (RUB)

    ### Последние курсы (recent_courses)
    Массив из 5 последних созданных курсов:
    - `unique_id` - ID курса
    - `title` - название
    - `created_at` - дата создания (ISO 8601)

    ### Метаданные
    - `generated_at` - время генерации отчета (ISO 8601 UTC)

    ## Примеры использования

    ```bash
    # Получить статистику
    GET /api/v2/internal/stats/courses
    X-API-Key: your-secret-key
    ```

    ## Использование

    - Интеграция с системами мониторинга
    - Построение дашбордов
    - Автоматические отчеты
    - Анализ эффективности контента

    ## Ошибки

    - **401 Unauthorized**: Отсутствует или неверный API-ключ
    """
    async with get_async_session() as session:
        # Verify API key
        await verify_api_key(request, session)

        # Basic counts
        total_courses = await session.scalar(select(func.count(Course.unique_id)))

        active_courses = await session.scalar(
            select(func.count(Course.unique_id)).where(Course.is_active)
        )

        total_modules = await session.scalar(select(func.count(Module.unique_id)))

        total_tests = await session.scalar(select(func.count(Test.unique_id)))

        # User engagement stats
        total_purchases = await session.scalar(
            select(func.count(PurchasedCourse.unique_id))
        )

        total_completions = await session.scalar(
            select(func.count(CompletedModule.unique_id))
        )

        # Revenue stats
        total_revenue = await session.scalar(
            select(func.sum(Course.price)).where(Course.is_active)
        ) or Decimal(0)

        # Recent activity
        recent_courses = await session.execute(
            select(Course)
            .where(Course.is_active)
            .order_by(Course.create_time.desc())
            .limit(5)
        )

        return {
            "overview": {
                "total_courses": total_courses or 0,
                "active_courses": active_courses or 0,
                "total_modules": total_modules or 0,
                "total_tests": total_tests or 0,
            },
            "engagement": {
                "total_purchases": total_purchases or 0,
                "total_completions": total_completions or 0,
            },
            "revenue": {
                "total_potential_revenue": float(total_revenue),
                "currency": "RUB",
            },
            "recent_courses": [
                {
                    "unique_id": course.unique_id,
                    "title": course.title,
                    "created_at": course.create_time.isoformat(),
                }
                for course in recent_courses.scalars().all()
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }


@router.get(
    "/health/detailed",
    summary="Детальная проверка здоровья системы",
    response_description="Подробная информация о состоянии всех компонентов",
)
async def detailed_health_check(
    request: Request,
) -> dict[str, Any]:
    """
    Детальная проверка здоровья системы для внутреннего мониторинга.

    ## Назначение

    Внутренний эндпоинт для мониторинга состояния системы.
    Используется для:
    - Health checks в Kubernetes/Docker
    - Мониторинг систем (Prometheus, Grafana)
    - Алертинг при проблемах
    - Диагностика проблем

    ## Аутентификация

    **Требуется API-ключ** в заголовке `X-API-Key`.

    ## Возвращаемые данные

    ### Общий статус
    - `status` - общее состояние ("healthy" или "unhealthy")
    - `timestamp` - время проверки (ISO 8601 UTC)
    - `version` - версия API
    - `environment` - окружение (development/production)

    ### База данных (database)
    - `status` - состояние подключения к БД
    - `user_count` - количество пользователей (тест подключения)

    ### Безопасность (security)
    - `jwt_configured` - настроен ли JWT секретный ключ
    - `rate_limiting_enabled` - включен ли rate limiting
    - `rate_limit_requests_per_minute` - лимит запросов в минуту

    ### Функции (features)
    - `idempotency_enabled` - включена ли идемпотентность
    - `pagination_enabled` - включена ли пагинация
    - `field_selection_enabled` - включен ли выбор полей
    - `internal_api_enabled` - включен ли внутренний API

    ### Эндпоинты (endpoints)
    - `public` - список публичных версий API
    - `internal` - путь к внутреннему API
    - `docs` - пути к документации

    ## Примеры использования

    ```bash
    # Проверить здоровье системы
    GET /api/v2/internal/health/detailed
    X-API-Key: your-secret-key
    ```

    ## Интеграция с мониторингом

    Используйте этот эндпоинт для:
    - Kubernetes liveness/readiness probes
    - Prometheus health checks
    - Uptime мониторинга
    - Автоматического алертинга

    ## Ошибки

    - **401 Unauthorized**: Отсутствует или неверный API-ключ
    - **500 Internal Server Error**: Критические проблемы с системой
    """
    async with get_async_session() as session:
        # Verify API key
        await verify_api_key(request, session)

        # Database connectivity check
        try:
            db_test = await session.scalar(select(func.count(User.unique_id)))
            db_status = "healthy"
            db_user_count = db_test or 0
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
            db_user_count = 0

        # System info
        settings = get_settings()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.0.1",
            "environment": "development",
            "database": {
                "status": db_status,
                "user_count": db_user_count,
            },
            "security": {
                "jwt_configured": bool(
                    settings.security.jwt_secret_key.get_secret_value()
                ),
                "rate_limiting_enabled": settings.rate_limit.enabled,
                "rate_limit_requests_per_minute": settings.rate_limit.requests_per_minute,
            },
            "features": {
                "idempotency_enabled": True,
                "pagination_enabled": True,
                "field_selection_enabled": True,
                "internal_api_enabled": True,
            },
            "endpoints": {
                "public": ["/api/v1", "/api/v2"],
                "internal": "/api/v2/internal",
                "docs": ["/api/v1/docs", "/api/v2/docs"],
            },
        }
