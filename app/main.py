from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.api_router import v1_api_router, v2_api_router
from app.core.config import get_settings
from app.core.idempotency import IdempotencyMiddleware
from app.core.limiter import limiter
from app.core.ratelimit_headers import RateLimitHeadersMiddleware

app = FastAPI(
    title="DigitalSkeptik Backend",
    version="0.0.1",
    description="https://github.com/DigitalSkeptik/DS_Backend",
    openapi_url=None,
    docs_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore


v1_app = FastAPI(
    title="DigitalSkeptik Backend API v1",
    version="1.0.0",
    description="""
# DigitalSkeptik Backend API

Базовая версия API системы онлайн-обучения.

## Основные возможности v1

- CRUD операции для курсов, модулей, тестов
- JWT аутентификация с refresh tokens
- Базовые эндпоинты без пользовательских данных
- Rate limiting (60 запросов/минуту)
- Идемпотентность POST-запросов

## Переход на v2

Новая версия API доступна по адресу: [/api/v2/docs](../v2/docs)

### Что нового в v2:
- Пагинация результатов
- Персонализированные цены с учетом скидок
- Статистика прогресса пользователя
- Выборочные поля (field selection)
- Внутренние API для служебных операций
- API-ключи для внутренних сервисов

## Документация
- Swagger UI: [/api/v1/docs](../v1/docs)
- ReDoc: [/api/v1/redoc](../v1/redoc)
- OpenAPI Schema: [/api/v1/openapi.json](../v1/openapi.json)

## Аутентификация

Используйте JWT токены в заголовке `Authorization: Bearer <token>`.
Получить токен можно через эндпоинт `/api/v1/auth/login`.

## Rate Limiting

Все эндпоинты ограничены 60 запросами в минуту. Получение Access Token ограничено до 10 запросов в час, Refresh Token - до 1 запроса в час.

Заголовки ответа:
- `X-RateLimit-Limit` - максимум запросов
- `X-Limit-Remaining` - осталось запросов
- `X-RateLimit-Reset` - время сброса лимита
- `Retry-After` - секунд до повторной попытки (при 429)

## Идемпотентность
Все POST-запросы поддерживают идемпотентность через заголовок `Idempotency-Key`.
Повторные запросы с тем же ключом вернут кешированный ответ без повторного выполнения операции.
    """,
    openapi_url="/openapi.json",
    docs_url="/docs",
)

v2_app = FastAPI(
    title="DigitalSkeptik Backend API v2",
    version="2.0.0",
    description="""
Расширенная версия API с дополнительными возможностями и улучшениями.

## Новые возможности v2

### Пагинация
Все списковые эндпоинты поддерживают пагинацию:
- `page` - номер страницы (начиная с 1)
- `page_size` - количество элементов на странице (1-1000)

Ответ включает метаданные: `total`, `page`, `page_size`, `total_pages`, `has_next`, `has_prev`

### Персонализированные цены
Курсы возвращают:
- `price` - базовая цена
- `user_discount` - персональная скидка пользователя (если есть)
- `final_price` - итоговая цена с учетом скидки
- `is_purchased` - статус покупки курса

### Статистика прогресса
Для купленных курсов доступна информация:
- `completion_percentage` - процент завершения курса
- `is_completed` - статус завершения модулей
- `test_completed` - статус прохождения тестов

### Выборочные поля (Field Selection)
Параметр `fields` позволяет запросить только нужные поля:
- `?fields=unique_id,title,description` - конкретные поля
- `?fields=minimal` - минимальный набор полей

### Внутренние API
Эндпоинты `/api/v2/internal/*` для служебных операций:
- Требуют заголовок `X-API-Key`
- Массовые операции
- Детальная статистика
- Служебные функции

## Обратная совместимость

**Предыдущая версия API доступна по адресу:**  [/api/v1/docs](../v1/docs)

v1 продолжает работать без изменений. Все изменения в v2 являются аддитивными.

## Документация

- Swagger UI: [/api/v2/docs](../v2/docs)
- ReDoc: [/api/v2/redoc](../v2/redoc)
- OpenAPI Schema: [/api/v2/openapi.json](../v2/openapi.json)

## Аутентификация

### Для публичных эндпоинтов
JWT токены в заголовке `Authorization: Bearer <token>`.
Получить токен: `/api/v2/auth/login`

### Для внутренних эндпоинтов
API-ключ в заголовке `X-API-Key: <your-api-key>`.
Настраивается через переменную окружения `SECURITY__INTERNAL_API_KEY`.

## Rate Limiting

Все эндпоинты ограничены 60 запросами в минуту. Получение Access Token ограничено до 10 запросов в час, Refresh Token - до 1 запроса в час.

Заголовки ответа:
- `X-RateLimit-Limit` - максимум запросов
- `X-Limit-Remaining` - осталось запросов
- `X-RateLimit-Reset` - время сброса лимита
- `Retry-After` - секунд до повторной попытки (при 429)

## Идемпотентность
Все POST-запросы поддерживают идемпотентность через заголовок `Idempotency-Key`.
Повторные запросы с тем же ключом вернут кешированный ответ без повторного выполнения операции.

    """,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

v1_app.include_router(v1_api_router)
v2_app.include_router(v2_api_router)

v1_app.state.limiter = limiter
v1_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
v1_app.add_middleware(SlowAPIMiddleware)

v2_app.state.limiter = limiter
v2_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
v2_app.add_middleware(SlowAPIMiddleware)

v1_app.add_middleware(RateLimitHeadersMiddleware)
v2_app.add_middleware(RateLimitHeadersMiddleware)

app.mount("/api/v1", v1_app)
app.mount("/api/v2", v2_app)

app.add_middleware(IdempotencyMiddleware)

# Sets all CORS enabled origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        str(origin).rstrip("/")
        for origin in get_settings().security.backend_cors_origins
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Guards against HTTP Host Header attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_settings().security.allowed_hosts,
)
