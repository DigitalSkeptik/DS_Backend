import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages, deps
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.security.jwt import create_jwt_token
from app.core.security.password import (
    DUMMY_PASSWORD,
    get_password_hash,
    is_password_too_simple,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.requests import (
    RefreshTokenRequest,
    UserCreateRequest,
    UserLoginRequest,
)
from app.schemas.responses import AccessTokenResponse, UserResponse

router = APIRouter()

ACCESS_TOKEN_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Invalid email or password",
        "content": {
            "application/json": {"example": {"detail": api_messages.PASSWORD_INVALID}}
        },
    },
}

REFRESH_TOKEN_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Refresh token expired or is already used",
        "content": {
            "application/json": {
                "examples": {
                    "refresh token expired": {
                        "summary": api_messages.REFRESH_TOKEN_EXPIRED,
                        "value": {"detail": api_messages.REFRESH_TOKEN_EXPIRED},
                    },
                    "refresh token already used": {
                        "summary": api_messages.REFRESH_TOKEN_ALREADY_USED,
                        "value": {"detail": api_messages.REFRESH_TOKEN_ALREADY_USED},
                    },
                }
            }
        },
    },
    404: {
        "description": "Refresh token does not exist",
        "content": {
            "application/json": {
                "example": {"detail": api_messages.REFRESH_TOKEN_NOT_FOUND}
            }
        },
    },
}


@router.post(
    "/access-token",
    response_model=AccessTokenResponse,
    responses=ACCESS_TOKEN_RESPONSES,
    summary="Получить access token",
    response_description="JWT access token и refresh token",
)
@limiter.limit("10/hour")
async def login_access_token(
    request: Request,
    response: Response,
    form_data: UserLoginRequest,
    session: AsyncSession = Depends(deps.get_session),
) -> AccessTokenResponse:
    """
    Аутентификация пользователя и получение токенов доступа.

    ## Описание

    OAuth2-совместимый эндпоинт для получения JWT access token и refresh token.
    Токены используются для авторизации последующих запросов к API.

    ## Rate Limiting

    **Ограничение: 10 запросов в час** для защиты от брутфорса.

    ## Процесс аутентификации

    1. Пользователь отправляет email и пароль
    2. Сервер проверяет учетные данные
    3. При успехе создаются:
       - JWT access token (срок действия: 24 часа)
       - Refresh token (срок действия: 28 дней)
    4. Access token также устанавливается в HTTP-only cookie

    ## Возвращаемые данные

    - `token_type` - тип токена (всегда "Bearer")
    - `access_token` - JWT токен для авторизации запросов
    - `expires_at` - Unix timestamp истечения access token
    - `refresh_token` - токен для обновления access token
    - `refresh_token_expires_at` - Unix timestamp истечения refresh token

    ## Использование токена

    ### Вариант 1: HTTP-only Cookie (рекомендуется)
    Access token автоматически устанавливается в cookie и будет отправляться браузером.

    ### Вариант 2: Authorization Header (можно использовать для надежности на случай, если cookie не установятся)
    ```bash
    Authorization: Bearer <access_token>
    ```

    ## Примеры использования

    ```bash
    # Вход в систему
    POST /api/v2/auth/access-token
    Content-Type: application/json

    {
      "email": "user@example.com",
      "password": "SecurePassword123!"
    }
    ```

    ## Безопасность

    - Пароли хешируются с использованием bcrypt
    - Access token хранится в HTTP-only cookie (защита от XSS)
    - Rate limiting защищает от брутфорса

    ## Ошибки

    - **400 Bad Request**: Неверный email или пароль
    - **429 Too Many Requests**: Превышен лимит запросов (10/час)
    """
    user = await session.scalar(select(User).where(User.email == form_data.email))

    if user is None:
        verify_password(form_data.password, DUMMY_PASSWORD)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_INVALID,
        )

    if not verify_password(form_data.password, user.pass_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_INVALID,
        )

    jwt_token = create_jwt_token(user_id=user.unique_id)

    refresh_token = RefreshToken(
        user_id=user.unique_id,
        refresh_token=secrets.token_urlsafe(32),
        exp=int(time.time() + get_settings().security.refresh_token_expire_secs),
    )
    session.add(refresh_token)
    await session.commit()

    response.set_cookie(
        key="access_token",
        value=jwt_token.access_token,
        httponly=True,
        secure=True,  # consider False for local HTTP dev if needed
        samesite="lax",  # set to "none" if cross-site cookies are required (requires HTTPS)
        max_age=get_settings().security.jwt_access_token_expire_secs,
        expires=jwt_token.payload.exp,
        path="/",
    )

    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=refresh_token.refresh_token,
        refresh_token_expires_at=refresh_token.exp,
    )


@router.post(
    "/refresh-token",
    response_model=AccessTokenResponse,
    responses=REFRESH_TOKEN_RESPONSES,
    summary="Обновить access token",
    response_description="Новый JWT access token и refresh token",
)
@limiter.limit("1/hour")
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    response: Response,
    session: AsyncSession = Depends(deps.get_session),
) -> AccessTokenResponse:
    """
    Обновление access token с использованием refresh token.

    ## Описание

    Когда access token истекает (через 24 часа), используйте refresh token
    для получения новой пары токенов без повторного ввода пароля.

    ## Rate Limiting

    **Ограничение: 1 запрос в час** для предотвращения злоупотреблений.

    ## Процесс обновления

    1. Клиент отправляет refresh token
    2. Сервер проверяет валидность и срок действия
    3. Старый refresh token помечается как использованный
    4. Создаются новые access и refresh токены
    5. Новый access token устанавливается в cookie

    ## Важные особенности

    - **Одноразовое использование**: Каждый refresh token можно использовать только один раз
    - **Rotation**: При обновлении выдается новый refresh token
    - **Проверка пользователя**: Проверяется существование пользователя

    ## Возвращаемые данные

    - `token_type` - тип токена (всегда "Bearer")
    - `access_token` - новый JWT токен
    - `expires_at` - Unix timestamp истечения нового access token
    - `refresh_token` - новый refresh token
    - `refresh_token_expires_at` - Unix timestamp истечения нового refresh token

    ## Примеры использования

    ```bash
    # Обновить токены
    POST /api/v2/auth/refresh-token
    Content-Type: application/json

    {
      "refresh_token": "your-refresh-token-here"
    }
    ```

    ## Ошибки

    - **400 Bad Request**: Refresh token истек или уже использован
    - **401 Unauthorized**: Пользователь удален
    - **404 Not Found**: Refresh token не найден
    - **429 Too Many Requests**: Превышен лимит запросов (1/час)
    """
    token = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.refresh_token == data.refresh_token)
        .with_for_update(skip_locked=True)
    )

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.REFRESH_TOKEN_NOT_FOUND,
        )
    elif time.time() > token.exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_EXPIRED,
        )
    elif token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_ALREADY_USED,
        )

    # Check if user still exists
    user = await session.scalar(select(User).where(User.unique_id == token.user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.JWT_ERROR_USER_REMOVED,
        )

    token.used = True
    session.add(token)

    jwt_token = create_jwt_token(user_id=token.user_id)

    refresh_token = RefreshToken(
        user_id=token.user_id,
        refresh_token=secrets.token_urlsafe(32),
        exp=int(time.time() + get_settings().security.refresh_token_expire_secs),
    )
    session.add(refresh_token)
    await session.commit()

    response.set_cookie(
        key="access_token",
        value=jwt_token.access_token,
        httponly=True,
        secure=True,
        samesite="lax",  # set to "none" if cross-site cookies are required (requires HTTPS)
        max_age=get_settings().security.jwt_access_token_expire_secs,
        expires=jwt_token.payload.exp,
        path="/",
    )

    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=refresh_token.refresh_token,
        refresh_token_expires_at=refresh_token.exp,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    summary="Регистрация нового пользователя",
    response_description="Данные созданного пользователя",
    status_code=status.HTTP_201_CREATED,
)
async def register_new_user(
    new_user: UserCreateRequest,
    session: AsyncSession = Depends(deps.get_session),
) -> User:
    """
    Регистрация нового пользователя в системе.

    ## Описание

    Создает новую учетную запись пользователя с проверкой email и пароля.
    После регистрации используйте эндпоинт `/auth/access-token` для входа.

    ## Требования к данным

    ### Email
    - Должен быть валидным email адресом
    - Только ASCII символы
    - Автоматически приводится к нижнему регистру
    - Должен быть уникальным (не использоваться другими пользователями)

    ### Пароль
    Должен соответствовать требованиям безопасности:
    - Минимум 8 символов
    - Содержать заглавные и строчные буквы
    - Содержать цифры
    - Содержать специальные символы
    - Не должен быть слишком простым (например, "password123")

    ### Username
    - Произвольная строка
    - Используется для отображения имени пользователя
    - Не обязательно уникальное

    ## Возвращаемые данные

    - `unique_id` - уникальный идентификатор пользователя (UUID)
    - `email` - email пользователя (нормализованный)
    - `username` - имя пользователя

    **Примечание**: Пароль не возвращается в ответе из соображений безопасности.

    ## Процесс регистрации

    1. Валидация email (формат, ASCII, уникальность)
    2. Проверка сложности пароля
    3. Хеширование пароля (bcrypt, 12 раундов)
    4. Создание записи пользователя в БД
    5. Возврат данных пользователя

    ## Примеры использования

    ```bash
    # Регистрация нового пользователя
    POST /api/v2/auth/register
    Content-Type: application/json

    {
      "email": "newuser@example.com",
      "username": "John Doe",
      "password": "SecurePass123!@#"
    }
    ```

    ## После регистрации

    Для получения токенов доступа используйте:
    ```bash
    POST /api/v2/auth/access-token
    ```

    ## Ошибки

    - **400 Bad Request**:
      - Email уже используется
      - Неверный формат email (не-ASCII символы)
    - **422 Unprocessable Entity**:
      - Пароль не соответствует требованиям безопасности
      - Детальное сообщение указывает конкретную проблему
    """
    # Normalize email to lowercase
    normalized_email = new_user.email.lower()

    # Check for non-ASCII characters in email (should return 400)
    try:
        normalized_email.encode("ascii")
    except UnicodeEncodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format",
        )

    # Check if email is already used (use normalized email)
    user = await session.scalar(select(User).where(User.email == normalized_email))

    pass_check_result = is_password_too_simple(new_user.password)
    if pass_check_result:
        detail = (
            pass_check_result[1]
            if isinstance(pass_check_result, tuple)
            else api_messages.PASSWORD_INVALID
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        )

    user = User(
        email=normalized_email,
        username=new_user.username,
        pass_hash=get_password_hash(new_user.password),
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:  # pragma: no cover
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        )

    return user
